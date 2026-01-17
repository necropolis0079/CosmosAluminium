"""
CV Processor Lambda Handler.

Processes uploaded CVs using smart extraction:
- DOCX/Text PDF: Direct extraction (fast, free)
- Scanned PDF/Images: Triple OCR (Claude Vision + Tesseract + Textract)

Triggered by S3 upload events. Updates DynamoDB state machine.

Environment Variables:
    - CV_UPLOADS_BUCKET: Source bucket for uploads
    - PROCESSED_BUCKET: Destination bucket for processed data
    - STATE_TABLE: DynamoDB table for processing state
    - DB_SECRET_ARN: RDS credentials secret ARN
"""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote_plus

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Environment variables
CV_UPLOADS_BUCKET = os.environ.get("CV_UPLOADS_BUCKET", "lcmgo-cagenai-prod-cv-uploads-eun1")
PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "lcmgo-cagenai-prod-processed-eun1")
STATE_TABLE = os.environ.get("STATE_TABLE", "lcmgo-cagenai-prod-cv-processing-state")


class ProcessingStatus:
    """CV processing status values."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    PARSING = "parsing"
    MAPPING = "mapping"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


def handler(event: dict, context: Any) -> dict:
    """
    Lambda handler for CV processing.

    Triggered by S3 upload events.

    Args:
        event: S3 event with Records
        context: Lambda context

    Returns:
        Processing result summary
    """
    logger.info(f"CV Processor invoked with {len(event.get('Records', []))} records")

    results = []

    for record in event.get("Records", []):
        # Handle S3 event
        if record.get("eventSource") == "aws:s3":
            result = process_s3_record(record)
            results.append(result)

        # Handle direct invocation for testing
        elif "file_path" in record:
            result = asyncio.get_event_loop().run_until_complete(
                process_local_file(record["file_path"], record.get("correlation_id"))
            )
            results.append(result)

    return {
        "statusCode": 200,
        "processed": len(results),
        "results": results,
    }


def process_s3_record(record: dict) -> dict:
    """
    Process a single S3 upload record.

    Args:
        record: S3 event record

    Returns:
        Processing result
    """
    bucket = record["s3"]["bucket"]["name"]
    key = unquote_plus(record["s3"]["object"]["key"])
    correlation_id = str(uuid.uuid4())

    logger.info(f"Processing s3://{bucket}/{key}, correlation_id: {correlation_id}")

    # Initialize state in DynamoDB
    update_state(correlation_id, ProcessingStatus.PENDING, {"s3_key": key})

    try:
        # Download file to temp location
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(key).suffix
        ) as tmp_file:
            s3.download_file(bucket, key, tmp_file.name)
            local_path = tmp_file.name

        # Update state
        update_state(correlation_id, ProcessingStatus.EXTRACTING)

        # Run extraction
        result = asyncio.get_event_loop().run_until_complete(
            extract_cv(local_path, correlation_id)
        )

        # Clean up temp file
        os.unlink(local_path)

        if result.get("error"):
            update_state(
                correlation_id,
                ProcessingStatus.FAILED,
                {"error": result["error"]},
            )
            return {
                "correlation_id": correlation_id,
                "status": ProcessingStatus.FAILED,
                "error": result["error"],
            }

        # Store extracted text
        text_key = f"extracted/{correlation_id}.txt"
        s3.put_object(
            Bucket=PROCESSED_BUCKET,
            Key=text_key,
            Body=result["text"].encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
            Metadata={
                "correlation_id": correlation_id,
                "source_key": key,
                "extraction_method": result["method"],
                "confidence": str(result["confidence"]),
            },
        )

        # Store metadata
        metadata_key = f"metadata/{correlation_id}.json"
        metadata = {
            "correlation_id": correlation_id,
            "source_bucket": bucket,
            "source_key": key,
            "extraction_method": result["method"],
            "document_type": result["document_type"],
            "confidence": result["confidence"],
            "page_count": result.get("page_count", 1),
            "has_images": result.get("has_images", False),
            "text_length": len(result["text"]),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "ocr_details": result.get("ocr_details", {}),
        }
        s3.put_object(
            Bucket=PROCESSED_BUCKET,
            Key=metadata_key,
            Body=json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

        # Update state to completed (for now, parsing/mapping/indexing will be separate)
        update_state(
            correlation_id,
            ProcessingStatus.COMPLETED,
            {
                "text_key": text_key,
                "metadata_key": metadata_key,
                "confidence": result["confidence"],
            },
        )

        logger.info(
            f"Successfully processed {key}: method={result['method']}, "
            f"confidence={result['confidence']:.2f}, "
            f"chars={len(result['text'])}"
        )

        return {
            "correlation_id": correlation_id,
            "status": ProcessingStatus.COMPLETED,
            "method": result["method"],
            "confidence": result["confidence"],
            "text_length": len(result["text"]),
        }

    except Exception as e:
        logger.exception(f"Failed to process {key}")
        update_state(
            correlation_id,
            ProcessingStatus.FAILED,
            {"error": str(e)},
        )
        return {
            "correlation_id": correlation_id,
            "status": ProcessingStatus.FAILED,
            "error": str(e),
        }


async def extract_cv(file_path: str, correlation_id: str) -> dict:
    """
    Extract text from CV using smart routing.

    Args:
        file_path: Path to CV file
        correlation_id: Tracing ID

    Returns:
        Extraction result dict
    """
    # Import here to allow Lambda layer resolution
    import sys
    sys.path.insert(0, "/opt/python")

    try:
        from lcmgo_cagenai.ocr import DocumentExtractor

        extractor = DocumentExtractor()
        result = await extractor.extract(file_path, correlation_id)

        return {
            "text": result.text,
            "method": result.method.value,
            "document_type": result.document_type.value,
            "confidence": result.confidence,
            "page_count": result.page_count,
            "has_images": result.has_images,
            "ocr_details": result.ocr_details,
            "error": result.error,
        }

    except ImportError:
        # Fallback for when package isn't installed (local testing)
        logger.warning("lcmgo_cagenai not found, using basic extraction")
        return await _fallback_extract(file_path)


async def _fallback_extract(file_path: str) -> dict:
    """
    Fallback extraction when main package isn't available.

    Uses basic pdfplumber/python-docx extraction.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    try:
        if ext == ".docx":
            from docx import Document

            doc = Document(path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return {
                "text": text,
                "method": "direct_docx",
                "document_type": "docx",
                "confidence": 1.0,
                "error": None,
            }

        elif ext == ".pdf":
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                pages = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)

                if pages:
                    return {
                        "text": "\n\n".join(pages),
                        "method": "direct_pdf",
                        "document_type": "pdf_text",
                        "confidence": 1.0,
                        "page_count": len(pdf.pages),
                        "error": None,
                    }
                else:
                    return {
                        "text": "",
                        "method": "failed",
                        "document_type": "pdf_scanned",
                        "confidence": 0.0,
                        "error": "PDF appears to be scanned, OCR not available in fallback",
                    }

        else:
            return {
                "text": "",
                "method": "failed",
                "document_type": "unsupported",
                "confidence": 0.0,
                "error": f"Unsupported file type: {ext}",
            }

    except Exception as e:
        return {
            "text": "",
            "method": "failed",
            "document_type": "unknown",
            "confidence": 0.0,
            "error": str(e),
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
    table = dynamodb.Table(STATE_TABLE)

    item = {
        "correlation_id": correlation_id,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if extra_data:
        item.update(extra_data)

    # Use update_item for atomic updates
    update_expr = "SET #status = :status, updated_at = :updated_at"
    expr_names = {"#status": "status"}
    expr_values = {
        ":status": status,
        ":updated_at": item["updated_at"],
    }

    if extra_data:
        for key, value in extra_data.items():
            if key not in ("correlation_id", "status", "updated_at"):
                update_expr += f", {key} = :{key}"
                expr_values[f":{key}"] = value

    try:
        table.update_item(
            Key={"correlation_id": correlation_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )
    except Exception as e:
        logger.warning(f"Failed to update state: {e}")


async def process_local_file(file_path: str, correlation_id: str | None = None) -> dict:
    """
    Process a local file (for testing).

    Args:
        file_path: Path to local file
        correlation_id: Optional tracing ID

    Returns:
        Extraction result
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    result = await extract_cv(file_path, correlation_id)

    return {
        "correlation_id": correlation_id,
        "status": ProcessingStatus.COMPLETED if not result.get("error") else ProcessingStatus.FAILED,
        **result,
    }


# For local testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python handler.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    result = asyncio.run(process_local_file(file_path))
    print(json.dumps(result, indent=2, ensure_ascii=False))
