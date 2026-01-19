"""
Upload Lambda Handler.

Generates presigned URLs for S3 CV uploads and initializes DynamoDB state.
Used by the testing frontend for direct browser uploads.

Environment Variables:
    - CV_UPLOADS_BUCKET: S3 bucket for CV uploads
    - STATE_TABLE: DynamoDB table for processing state
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

import boto3
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients - use regional endpoint for eu-north-1
AWS_REGION = os.environ.get("AWS_REGION_NAME", "eu-north-1")
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com",
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)
dynamodb = boto3.resource("dynamodb")

# Environment variables
CV_UPLOADS_BUCKET = os.environ.get("CV_UPLOADS_BUCKET", "lcmgo-cagenai-prod-cv-uploads-eun1")
STATE_TABLE = os.environ.get("STATE_TABLE", "lcmgo-cagenai-prod-cv-processing-state")

# Allowed file types
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def handler(event: dict, context) -> dict:
    """
    Lambda handler for generating presigned upload URLs.

    Args:
        event: API Gateway HTTP API v2 event
        context: Lambda context

    Returns:
        API Gateway response with presigned URL
    """
    logger.info(f"Upload request: {json.dumps(event, default=str)}")

    # Parse request body
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON body"})

    filename = body.get("filename", "")
    content_type = body.get("content_type", "application/pdf")

    if not filename:
        return response(400, {"error": "filename is required"})

    # Validate content type
    if content_type not in ALLOWED_TYPES:
        return response(400, {
            "error": f"Invalid content_type. Allowed: {list(ALLOWED_TYPES.keys())}"
        })

    # Generate correlation ID
    correlation_id = str(uuid.uuid4())

    # Build S3 key with safe filename
    safe_filename = quote(filename, safe=".-_")
    s3_key = f"uploads/{safe_filename}"

    try:
        # Generate presigned POST (more secure than PUT for browser uploads)
        presigned_post = s3.generate_presigned_post(
            Bucket=CV_UPLOADS_BUCKET,
            Key=s3_key,
            Fields={
                "Content-Type": content_type,
                "x-amz-meta-correlation-id": correlation_id,
            },
            Conditions=[
                {"Content-Type": content_type},
                {"x-amz-meta-correlation-id": correlation_id},
                ["content-length-range", 1, 10 * 1024 * 1024],  # 1 byte to 10MB
            ],
            ExpiresIn=300,  # 5 minutes
        )

        # Initialize DynamoDB state
        init_state(correlation_id, s3_key, filename)

        logger.info(f"Generated presigned URL for {filename}, correlation_id={correlation_id}")

        return response(200, {
            "correlation_id": correlation_id,
            "upload_url": presigned_post["url"],
            "fields": presigned_post["fields"],
            "s3_key": s3_key,
            "expires_in": 300,
        })

    except Exception as e:
        logger.exception(f"Failed to generate presigned URL: {e}")
        return response(500, {"error": str(e)})


def init_state(correlation_id: str, s3_key: str, filename: str) -> None:
    """
    Initialize processing state in DynamoDB.

    Args:
        correlation_id: Unique processing ID
        s3_key: S3 key where CV will be uploaded
        filename: Original filename
    """
    table = dynamodb.Table(STATE_TABLE)

    now = datetime.now(timezone.utc).isoformat()

    try:
        table.put_item(
            Item={
                "cv_id": correlation_id,
                "correlation_id": correlation_id,
                "status": "uploading",
                "s3_key": s3_key,
                "filename": filename,
                "created_at": now,
                "updated_at": now,
            }
        )
        logger.info(f"Initialized state for {correlation_id}")
    except Exception as e:
        logger.warning(f"Failed to initialize state: {e}")


def response(status_code: int, body: dict) -> dict:
    """Build API Gateway HTTP API v2 response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Request-ID",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
