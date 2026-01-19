"""
Status Lambda Handler.

Polls DynamoDB for CV processing status.
Returns current state and step details for the progress monitor.

Environment Variables:
    - STATE_TABLE: DynamoDB table for processing state
    - PROCESSED_BUCKET: S3 bucket for processed data
"""

import json
import logging
import os
from decimal import Decimal
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# Environment variables
STATE_TABLE = os.environ.get("STATE_TABLE", "lcmgo-cagenai-prod-cv-processing-state")
PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "lcmgo-cagenai-prod-processed-eun1")

# Processing steps with display info
PROCESSING_STEPS = [
    {"status": "uploading", "label": "Uploading", "description": "Uploading CV to storage"},
    {"status": "pending", "label": "Queued", "description": "CV queued for processing"},
    {"status": "extracting", "label": "Extracting", "description": "Extracting text from document"},
    {"status": "parsing", "label": "Parsing", "description": "AI parsing CV content"},
    {"status": "mapping", "label": "Mapping", "description": "Mapping skills to taxonomy"},
    {"status": "storing", "label": "Storing", "description": "Saving to database"},
    {"status": "indexing", "label": "Indexing", "description": "Indexing for search"},
    {"status": "completed", "label": "Completed", "description": "Processing complete"},
]

STATUS_ORDER = {step["status"]: i for i, step in enumerate(PROCESSING_STEPS)}


def handler(event: dict, context: Any) -> dict:
    """
    Lambda handler for status polling.

    Args:
        event: API Gateway HTTP API v2 event
        context: Lambda context

    Returns:
        API Gateway response with status info
    """
    # Extract correlation_id from path parameters
    path_params = event.get("pathParameters", {}) or {}
    correlation_id = path_params.get("correlation_id")

    if not correlation_id:
        return response(400, {"error": "correlation_id is required in path"})

    logger.info(f"Status request for: {correlation_id}")

    try:
        table = dynamodb.Table(STATE_TABLE)

        # Get item from DynamoDB
        result = table.get_item(Key={"cv_id": correlation_id})
        item = result.get("Item")

        if not item:
            return response(404, {
                "error": "Not found",
                "correlation_id": correlation_id,
            })

        # Convert Decimal to float for JSON serialization
        item = convert_decimals(item)

        # Build response with step info
        current_status = item.get("status", "unknown")
        current_step = STATUS_ORDER.get(current_status, -1)

        # Determine if processing is complete or failed
        is_completed = current_status == "completed"
        is_failed = current_status == "failed"

        response_body = {
            "correlation_id": correlation_id,
            "status": current_status,
            "is_completed": is_completed,
            "is_failed": is_failed,
            "current_step": current_step,
            "total_steps": len(PROCESSING_STEPS),
            "progress_percent": calculate_progress(current_status),
            "steps": get_steps_with_state(current_status),
            "updated_at": item.get("updated_at"),
            "details": extract_details(item),
        }

        # Add error info if failed
        if is_failed:
            response_body["error"] = item.get("error", "Unknown error")

        # Add completion info if completed
        if is_completed:
            response_body["candidate_id"] = item.get("candidate_id")
            response_body["summary"] = {
                "skills_count": item.get("skills_count", 0),
                "experience_count": item.get("experience_count", 0),
                "education_count": item.get("education_count", 0),
                "certifications_count": item.get("certifications_count", 0),
                "training_count": item.get("training_count", 0),
                "languages_count": item.get("languages_count", 0),
                "software_count": item.get("software_count", 0),
                "driving_licenses_count": item.get("driving_licenses_count", 0),
                "unmatched_count": item.get("unmatched_count", 0),
                "overall_confidence": item.get("overall_confidence", 0),
                "completeness_score": item.get("completeness_score", 0),
            }

            # Fetch full parsed CV data from S3
            parsed_data = get_parsed_cv_data(correlation_id)
            if parsed_data:
                response_body["parsed_cv"] = parsed_data

            # Fetch unmatched data
            unmatched = get_unmatched_data(correlation_id)
            if unmatched:
                response_body["unmatched_data"] = unmatched

        return response(200, response_body)

    except Exception as e:
        logger.exception(f"Failed to get status: {e}")
        return response(500, {"error": str(e)})


def calculate_progress(status: str) -> int:
    """Calculate progress percentage based on current status."""
    if status == "failed":
        return 0
    if status == "completed":
        return 100

    step = STATUS_ORDER.get(status, 0)
    total = len(PROCESSING_STEPS) - 1  # Exclude completed
    return int((step / total) * 100)


def get_steps_with_state(current_status: str) -> list:
    """Get steps array with current state indicators."""
    current_idx = STATUS_ORDER.get(current_status, -1)
    is_failed = current_status == "failed"
    is_completed = current_status == "completed"

    steps = []
    for i, step in enumerate(PROCESSING_STEPS):
        if is_failed:
            state = "failed" if i == current_idx else ("completed" if i < current_idx else "pending")
        elif is_completed:
            # All steps are completed when status is "completed"
            state = "completed"
        elif i < current_idx:
            state = "completed"
        elif i == current_idx:
            state = "current"
        else:
            state = "pending"

        steps.append({
            "status": step["status"],
            "label": step["label"],
            "description": step["description"],
            "state": state,
        })

    return steps


def extract_details(item: dict) -> dict:
    """Extract relevant details from DynamoDB item."""
    details = {}

    # Extraction details
    if item.get("extraction_complete"):
        details["extraction"] = {
            "confidence": item.get("confidence"),
            "method": item.get("extraction_method"),
        }

    # Parsing details
    if item.get("skills_count") is not None:
        details["parsing"] = {
            "skills_count": item.get("skills_count"),
            "experience_count": item.get("experience_count"),
        }

    # Verification details (Task 1.2)
    if item.get("verification_success") is not None:
        details["verification"] = {
            "success": item.get("verification_success"),
            "coverage": item.get("verification_coverage"),
        }

    # Audit details (Task 1.3)
    if item.get("audit_completeness_score") is not None:
        details["audit"] = {
            "completeness_score": item.get("audit_completeness_score"),
            "quality_level": item.get("audit_quality_level"),
        }

    return details


def convert_decimals(obj: Any) -> Any:
    """Recursively convert Decimal to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    return obj


def get_parsed_cv_data(correlation_id: str) -> dict | None:
    """Fetch full parsed CV data from S3."""
    try:
        parsed_key = f"parsed/{correlation_id}.json"
        response = s3.get_object(Bucket=PROCESSED_BUCKET, Key=parsed_key)
        parsed_data = json.loads(response["Body"].read().decode("utf-8"))
        return parsed_data
    except s3.exceptions.NoSuchKey:
        logger.warning(f"Parsed CV not found: {parsed_key}")
        return None
    except Exception as e:
        logger.warning(f"Failed to get parsed CV: {e}")
        return None


def get_unmatched_data(correlation_id: str) -> list:
    """Fetch unmatched taxonomy items from S3 metadata or parsed data."""
    try:
        # Try to get from unmatched file if exists
        unmatched_key = f"unmatched/{correlation_id}.json"
        try:
            response = s3.get_object(Bucket=PROCESSED_BUCKET, Key=unmatched_key)
            return json.loads(response["Body"].read().decode("utf-8"))
        except Exception:
            pass

        # Fall back to parsed data
        parsed_data = get_parsed_cv_data(correlation_id)
        if parsed_data and "unmatched_data" in parsed_data:
            return parsed_data["unmatched_data"]

        return []
    except Exception as e:
        logger.warning(f"Failed to get unmatched data: {e}")
        return []


def response(status_code: int, body: dict) -> dict:
    """Build API Gateway HTTP API v2 response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Request-ID",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
