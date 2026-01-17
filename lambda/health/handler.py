"""
Health Check Lambda Handler
============================
Simple health check endpoint for API Gateway.
No authentication required - used for load balancer health checks and monitoring.

Author: Claude Code (LCMGoCloud-CAGenAI)
"""

import json
import os
from datetime import datetime, timezone


def handler(event, context):
    """
    Handle health check requests.

    Returns a simple health status response.
    Works with both direct Lambda invocation and API Gateway proxy integration.

    Args:
        event: Lambda event (API Gateway v2 format or direct invocation)
        context: Lambda context

    Returns:
        dict: API Gateway v2 response format
    """
    # Build health response
    response_body = {
        "status": "healthy",
        "service": "lcmgo-cagenai",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "region": os.environ.get("AWS_REGION", "unknown"),
    }

    # Include request ID if available (from API Gateway)
    request_context = event.get("requestContext", {})
    if request_id := request_context.get("requestId"):
        response_body["request_id"] = request_id

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
        "body": json.dumps(response_body),
    }
