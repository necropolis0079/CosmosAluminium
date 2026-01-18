"""
CV Parser Lambda Handler.

Parses extracted CV text into structured data using Claude Sonnet 4.5.
Writes to PostgreSQL and indexes to OpenSearch.

Triggered by async invocation from cv_processor Lambda.

Environment Variables:
    - PROCESSED_BUCKET: S3 bucket with extracted text
    - STATE_TABLE: DynamoDB table for processing state
    - DB_SECRET_ARN: RDS credentials secret ARN
    - OPENSEARCH_ENDPOINT: OpenSearch domain endpoint
    - AWS_REGION_NAME: AWS region
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")

# Environment variables
PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "lcmgo-cagenai-prod-processed-eun1")
STATE_TABLE = os.environ.get("STATE_TABLE", "lcmgo-cagenai-prod-cv-processing-state")
DB_SECRET_ARN = os.environ.get("DB_SECRET_ARN")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT")
AWS_REGION = os.environ.get("AWS_REGION_NAME", "eu-north-1")


class ProcessingStatus:
    """CV processing status values."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    PARSING = "parsing"
    MAPPING = "mapping"
    STORING = "storing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


def handler(event: dict, context: Any) -> dict:
    """
    Lambda handler for CV parsing.

    Triggered by async invocation from cv_processor.

    Event structure:
    {
        "correlation_id": "uuid",
        "text_key": "extracted/uuid.txt",
        "metadata_key": "metadata/uuid.json",
        "extraction_confidence": 0.95
    }

    Args:
        event: Event with correlation_id and S3 keys
        context: Lambda context

    Returns:
        Processing result summary
    """
    correlation_id = event.get("correlation_id")
    text_key = event.get("text_key")
    metadata_key = event.get("metadata_key")

    logger.info(f"CV Parser invoked: correlation_id={correlation_id}")

    if not correlation_id or not text_key:
        return {
            "statusCode": 400,
            "error": "Missing correlation_id or text_key",
        }

    try:
        # Run async processing
        result = asyncio.get_event_loop().run_until_complete(
            process_cv(correlation_id, text_key, metadata_key)
        )
        return result

    except Exception as e:
        logger.exception(f"Failed to process CV: {correlation_id}")
        update_state(correlation_id, ProcessingStatus.FAILED, {"error": str(e)})
        return {
            "statusCode": 500,
            "correlation_id": correlation_id,
            "status": ProcessingStatus.FAILED,
            "error": str(e),
        }


async def process_cv(
    correlation_id: str,
    text_key: str,
    metadata_key: str | None,
) -> dict:
    """
    Process CV: parse, map taxonomy, write to DB, index to OpenSearch.

    Args:
        correlation_id: Tracking ID
        text_key: S3 key for extracted text
        metadata_key: S3 key for metadata

    Returns:
        Processing result
    """
    # Import here to allow Lambda layer resolution
    import sys
    sys.path.insert(0, "/opt/python")

    try:
        from lcmgo_cagenai.parser import (
            CVParser,
            DatabaseWriter,
            SearchIndexer,
            TaxonomyMapper,
        )
    except ImportError as e:
        logger.error(f"Failed to import parser modules: {e}")
        raise

    # 1. Update state: PARSING
    update_state(correlation_id, ProcessingStatus.PARSING)

    # 2. Read extracted text from S3
    logger.info(f"Reading extracted text from s3://{PROCESSED_BUCKET}/{text_key}")
    response = s3.get_object(Bucket=PROCESSED_BUCKET, Key=text_key)
    cv_text = response["Body"].read().decode("utf-8")

    # Read metadata if available
    metadata = {}
    if metadata_key:
        try:
            meta_response = s3.get_object(Bucket=PROCESSED_BUCKET, Key=metadata_key)
            metadata = json.loads(meta_response["Body"].read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Failed to read metadata: {e}")

    # 3. Parse with Claude
    logger.info(f"Parsing CV text ({len(cv_text)} chars)")
    parser = CVParser(region=AWS_REGION)

    parsed_cv = await parser.parse(cv_text, correlation_id)

    # Log parsing summary
    logger.info(
        f"Parsed CV: "
        f"name={parsed_cv.personal.first_name} {parsed_cv.personal.last_name}, "
        f"education={len(parsed_cv.education)}, "
        f"experience={len(parsed_cv.experience)}, "
        f"skills={len(parsed_cv.skills)}, "
        f"confidence={parsed_cv.overall_confidence:.2f}"
    )

    # 4. Update state: MAPPING
    update_state(correlation_id, ProcessingStatus.MAPPING, {
        "skills_count": len(parsed_cv.skills),
        "experience_count": len(parsed_cv.experience),
    })

    # 5. Map to taxonomy
    if DB_SECRET_ARN:
        try:
            logger.info("Mapping skills to taxonomy")
            mapper = TaxonomyMapper(
                db_secret_arn=DB_SECRET_ARN,
                region=AWS_REGION,
                use_semantic_matching=True,
            )
            await mapper.map_all(parsed_cv)
            mapper.close()

            mapped_skills = sum(1 for s in parsed_cv.skills if s.skill_id)
            logger.info(f"Mapped {mapped_skills}/{len(parsed_cv.skills)} skills to taxonomy")

        except Exception as e:
            logger.warning(f"Taxonomy mapping failed: {e}")
            # Continue without taxonomy mapping

    # 6. Update state: STORING
    update_state(correlation_id, ProcessingStatus.STORING)

    # 7. Write to PostgreSQL
    candidate_id = None
    if DB_SECRET_ARN:
        try:
            logger.info("Writing to PostgreSQL")
            writer = DatabaseWriter(db_secret_arn=DB_SECRET_ARN, region=AWS_REGION)
            candidate_id = await writer.write_candidate(
                parsed_cv,
                correlation_id,
                source_key=metadata.get("source_key"),
            )
            writer.close()
            logger.info(f"Created/updated candidate: {candidate_id}")

        except Exception as e:
            logger.error(f"Database write failed: {e}")
            # Continue to try indexing anyway

    # 8. Update state: INDEXING
    update_state(correlation_id, ProcessingStatus.INDEXING, {
        "candidate_id": str(candidate_id) if candidate_id else None,
    })

    # 9. Index to OpenSearch
    if OPENSEARCH_ENDPOINT and candidate_id:
        try:
            logger.info("Indexing to OpenSearch")
            indexer = SearchIndexer(
                opensearch_endpoint=OPENSEARCH_ENDPOINT,
                region=AWS_REGION,
            )
            await indexer.index_candidate(candidate_id, parsed_cv)
            logger.info(f"Indexed candidate {candidate_id} to OpenSearch")

        except Exception as e:
            logger.warning(f"OpenSearch indexing failed: {e}")
            # Non-fatal: data is in PostgreSQL

    # 10. Store parsed JSON to S3
    parsed_key = f"parsed/{correlation_id}.json"
    s3.put_object(
        Bucket=PROCESSED_BUCKET,
        Key=parsed_key,
        Body=json.dumps(parsed_cv.to_dict(), ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
        Metadata={
            "correlation_id": correlation_id,
            "candidate_id": str(candidate_id) if candidate_id else "",
        },
    )

    # 11. Update state: COMPLETED
    update_state(
        correlation_id,
        ProcessingStatus.COMPLETED,
        {
            "candidate_id": str(candidate_id) if candidate_id else None,
            "parsed_key": parsed_key,
            "overall_confidence": parsed_cv.overall_confidence,
            "completeness_score": parsed_cv.completeness_score,
            "skills_count": len(parsed_cv.skills),
            "experience_count": len(parsed_cv.experience),
            "education_count": len(parsed_cv.education),
        },
    )

    return {
        "statusCode": 200,
        "correlation_id": correlation_id,
        "status": ProcessingStatus.COMPLETED,
        "candidate_id": str(candidate_id) if candidate_id else None,
        "confidence": parsed_cv.overall_confidence,
        "completeness": parsed_cv.completeness_score,
        "summary": {
            "name": f"{parsed_cv.personal.first_name} {parsed_cv.personal.last_name}",
            "skills": len(parsed_cv.skills),
            "experience": len(parsed_cv.experience),
            "education": len(parsed_cv.education),
            "languages": len(parsed_cv.languages),
            "certifications": len(parsed_cv.certifications),
        },
    }


def update_state(
    correlation_id: str,
    status: str,
    extra_data: dict | None = None,
) -> None:
    """
    Update processing state in DynamoDB.

    Args:
        correlation_id: Unique processing ID
        status: Current processing status
        extra_data: Additional data to store
    """
    from decimal import Decimal

    table = dynamodb.Table(STATE_TABLE)

    update_expr = "SET #status = :status, #updated_at = :updated_at, #correlation_id = :correlation_id"
    expr_names = {
        "#status": "status",
        "#updated_at": "updated_at",
        "#correlation_id": "correlation_id",
    }
    expr_values = {
        ":status": status,
        ":updated_at": datetime.now(timezone.utc).isoformat(),
        ":correlation_id": correlation_id,
    }

    if extra_data:
        for key, value in extra_data.items():
            if key not in ("cv_id", "correlation_id", "status", "updated_at"):
                # Use expression attribute names to avoid reserved keyword issues
                attr_name = f"#attr_{key.replace('-', '_')}"
                expr_names[attr_name] = key
                update_expr += f", {attr_name} = :{key.replace('-', '_')}"
                # Convert floats to Decimal for DynamoDB compatibility
                if isinstance(value, float):
                    value = Decimal(str(value))
                expr_values[f":{key.replace('-', '_')}"] = value

    try:
        table.update_item(
            Key={"cv_id": correlation_id},  # Use correlation_id as cv_id (primary key)
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )
    except Exception as e:
        logger.warning(f"Failed to update state: {e}")


# For local testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python handler.py <correlation_id> [text_key]")
        sys.exit(1)

    correlation_id = sys.argv[1]
    text_key = sys.argv[2] if len(sys.argv) > 2 else f"extracted/{correlation_id}.txt"

    result = asyncio.run(process_cv(correlation_id, text_key, None))
    print(json.dumps(result, indent=2, ensure_ascii=False))
