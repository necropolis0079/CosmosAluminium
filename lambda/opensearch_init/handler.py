"""
OpenSearch Index Initialization Lambda.

Creates OpenSearch indices with k-NN mappings for vector search:
- cosmos-hr-candidates: CV embeddings and candidate data
- cosmos-hr-jobs: Job postings with requirements

Invoked manually or via Terraform to set up search infrastructure.

Environment Variables:
    OPENSEARCH_ENDPOINT: OpenSearch domain endpoint
    AWS_REGION_NAME: AWS region (default: eu-north-1)
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict, context: Any) -> dict:
    """
    Lambda handler to initialize OpenSearch indices.

    Event payload (all optional):
        {
            "action": "create_all" | "create_candidates" | "create_jobs" | "delete_all" | "status",
            "force": false  # If true, delete existing indices first
        }

    Returns:
        {
            "statusCode": 200 | 500,
            "body": {
                "message": "...",
                "indices": {...}
            }
        }
    """
    logger.info(f"OpenSearch init Lambda invoked: {json.dumps(event)}")

    # Get configuration from environment
    opensearch_endpoint = os.environ.get("OPENSEARCH_ENDPOINT")
    region = os.environ.get("AWS_REGION_NAME", "eu-north-1")

    if not opensearch_endpoint:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "OPENSEARCH_ENDPOINT not configured"}),
        }

    # Import search module (from Lambda layer)
    try:
        from lcmgo_cagenai.search import (
            CANDIDATES_INDEX,
            JOBS_INDEX,
            OpenSearchClient,
        )
        from lcmgo_cagenai.search.mappings import (
            CANDIDATES_INDEX_VERSIONED,
            JOBS_INDEX_VERSIONED,
        )
    except ImportError as e:
        logger.error(f"Failed to import search module: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Import error: {str(e)}"}),
        }

    # Initialize client
    try:
        client = OpenSearchClient(host=opensearch_endpoint, region=region)
        logger.info(f"Connected to OpenSearch: {opensearch_endpoint}")
    except Exception as e:
        logger.error(f"Failed to connect to OpenSearch: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Connection error: {str(e)}"}),
        }

    # Parse action
    action = event.get("action", "create_all")
    force = event.get("force", False)

    try:
        if action == "status":
            # Get cluster health and index info
            health = client.cluster_health()
            indices = client.list_indices()

            # Get stats for our indices
            index_stats = {}
            for idx in [CANDIDATES_INDEX, JOBS_INDEX]:
                try:
                    stats = client.get_index_stats(idx)
                    index_stats[idx] = {
                        "exists": True,
                        "doc_count": stats["_all"]["primaries"]["docs"]["count"],
                        "size_bytes": stats["_all"]["primaries"]["store"][
                            "size_in_bytes"
                        ],
                    }
                except Exception:
                    index_stats[idx] = {"exists": False}

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "OpenSearch status retrieved",
                        "cluster_health": health["status"],
                        "all_indices": indices,
                        "app_indices": index_stats,
                    }
                ),
            }

        elif action == "create_all":
            results = {}

            # Delete if force
            if force:
                logger.info("Force flag set, deleting existing indices")
                for idx in [CANDIDATES_INDEX_VERSIONED, JOBS_INDEX_VERSIONED]:
                    try:
                        client.delete_index(idx)
                        logger.info(f"Deleted index: {idx}")
                    except Exception as e:
                        logger.warning(f"Could not delete {idx}: {e}")

            # Create indices
            results = client.create_all_indices()
            logger.info(f"Created indices: {list(results.keys())}")

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "All indices created successfully",
                        "indices": {
                            k: {"acknowledged": v.get("acknowledged", True)}
                            for k, v in results.items()
                        },
                    }
                ),
            }

        elif action == "create_candidates":
            if force:
                try:
                    client.delete_index(CANDIDATES_INDEX_VERSIONED)
                except Exception:
                    pass

            result = client.create_candidates_index()
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Candidates index created",
                        "index": CANDIDATES_INDEX,
                        "acknowledged": result.get("acknowledged", True),
                    }
                ),
            }

        elif action == "create_jobs":
            if force:
                try:
                    client.delete_index(JOBS_INDEX_VERSIONED)
                except Exception:
                    pass

            result = client.create_jobs_index()
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Jobs index created",
                        "index": JOBS_INDEX,
                        "acknowledged": result.get("acknowledged", True),
                    }
                ),
            }

        elif action == "delete_all":
            results = {}
            for idx in [CANDIDATES_INDEX_VERSIONED, JOBS_INDEX_VERSIONED]:
                try:
                    result = client.delete_index(idx)
                    results[idx] = {"deleted": True}
                except Exception as e:
                    results[idx] = {"deleted": False, "error": str(e)}

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"message": "Delete operation completed", "indices": results}
                ),
            }

        else:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": f"Unknown action: {action}",
                        "valid_actions": [
                            "create_all",
                            "create_candidates",
                            "create_jobs",
                            "delete_all",
                            "status",
                        ],
                    }
                ),
            }

    except Exception as e:
        logger.exception(f"Error during {action}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e), "action": action}),
        }
