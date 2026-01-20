"""
Query Lambda Handler.

Exposes Text-to-SQL functionality via API.
Translates natural language HR queries (Greek/English) into PostgreSQL queries.

Supports:
- Direct invocation (from other Lambdas)
- API Gateway integration (POST /query)
- Intelligent job matching fallback when strict query returns 0 results

Environment Variables:
    - DB_SECRET_ARN: RDS credentials secret ARN (for SQL execution)
    - QUERY_CACHE_TABLE: DynamoDB table for query caching
    - AWS_REGION_NAME: AWS region
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3


class JSONEncoderWithUUID(json.JSONEncoder):
    """Custom JSON encoder that handles UUID and Decimal types."""

    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource("dynamodb")
secrets_client = boto3.client("secretsmanager")

# Environment variables
DB_SECRET_ARN = os.environ.get("DB_SECRET_ARN")
QUERY_CACHE_TABLE = os.environ.get("QUERY_CACHE_TABLE", "lcmgo-cagenai-prod-query-cache")
AWS_REGION = os.environ.get("AWS_REGION_NAME", "eu-north-1")

# Cache for DB credentials
_db_credentials = None


def handler(event: dict, context: Any) -> dict:
    """
    Lambda handler for query processing.

    Supports both direct invocation and API Gateway.

    Event structure (direct invocation):
    {
        "query": "λογιστής με Softone, 5+ χρόνια, Αθήνα",
        "execute": false,           // Optional: execute SQL and return results
        "limit": 50,                // Optional: limit results (default 50)
        "context": {}               // Optional: additional context
    }

    Event structure (API Gateway):
    {
        "body": "{\"query\": \"...\"}"
        "httpMethod": "POST"
    }

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        Query result with SQL or clarification request
    """
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    logger.info(f"Query Lambda invoked: request_id={request_id}")

    try:
        # Parse request
        body = _parse_request(event)
        user_query = body.get("query", "").strip()
        execute = body.get("execute", False)
        limit = min(body.get("limit", 50), 500)  # Cap at 500
        query_context = body.get("context", {})

        if not user_query:
            return _error_response(400, "Missing 'query' parameter", request_id)

        logger.info(f"Processing query: '{user_query[:100]}...' execute={execute}")

        # Check cache first
        cached = _check_cache(user_query)
        if cached and not execute:
            logger.info(f"Cache hit for query")
            cached["cached"] = True
            cached["request_id"] = request_id
            cached["latency_ms"] = int((time.time() - start_time) * 1000)
            return _success_response(cached)

        # Route the query
        result = asyncio.get_event_loop().run_until_complete(
            process_query(user_query, execute, limit, query_context)
        )

        # Check if we need job matching fallback
        # If execute=True and (result_count=0 or execution_error), try intelligent matching
        use_job_matching = body.get("use_job_matching", True)  # Default: enabled
        needs_fallback = (
            result.get("result_count", -1) == 0 or
            "execution_error" in result
        )
        if (execute and
            use_job_matching and
            needs_fallback and
            result.get("query_type") == "structured"):

            logger.info("No results or error from strict query, falling back to job matching")
            try:
                job_match_result = run_job_matching(user_query, limit)
                if job_match_result and job_match_result.get("total_found", 0) > 0:
                    # Combine results
                    result["job_matching"] = job_match_result
                    result["fallback_used"] = True
                    logger.info(f"Job matching found {job_match_result.get('total_found')} candidates")
            except Exception as e:
                logger.warning(f"Job matching fallback failed: {e}")
                result["job_matching_error"] = str(e)

        # Add request metadata
        result["request_id"] = request_id
        result["latency_ms"] = int((time.time() - start_time) * 1000)
        result["cached"] = False

        # Cache the result (if structured and not executed)
        if not execute and result.get("query_type") == "structured":
            _cache_result(user_query, result)

        return _success_response(result)

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return _error_response(400, str(e), request_id)

    except Exception as e:
        logger.exception(f"Query processing failed: {e}")
        return _error_response(500, f"Internal error: {str(e)}", request_id)


async def process_query(
    user_query: str,
    execute: bool,
    limit: int,
    context: dict[str, Any],
) -> dict:
    """
    Process the natural language query.

    Args:
        user_query: User's natural language query
        execute: Whether to execute SQL
        limit: Result limit
        context: Query context

    Returns:
        Query result dictionary
    """
    # Import here to allow Lambda layer resolution
    import sys
    sys.path.insert(0, "/opt/python")

    try:
        from lcmgo_cagenai.query import QueryRouter, QueryType
    except ImportError as e:
        logger.error(f"Failed to import query modules: {e}")
        raise

    # Create router and route query
    router = QueryRouter(region=AWS_REGION)
    route_result = await router.route(user_query, context)

    # Build response
    response = {
        "query_type": route_result.query_type.value,
        "original_query": user_query,
        "translation": {
            "confidence": route_result.translation.confidence,
            "filters": route_result.translation.filters,
            "sort": route_result.translation.sort.to_dict() if route_result.translation.sort else None,
            "limit": route_result.translation.limit,
            "unknown_terms": route_result.translation.unknown_terms,
        },
        "route_reason": route_result.route_reason,
    }

    # Add SQL query if structured
    if route_result.sql_query:
        response["sql"] = {
            "query": route_result.sql_query.query,
            "params": route_result.sql_query.params,
            "param_types": route_result.sql_query.param_types,
            "filter_summary": route_result.sql_query.filter_summary,
            "tables_used": route_result.sql_query.tables_used,
        }

        # Execute if requested
        if execute and DB_SECRET_ARN:
            try:
                results = await execute_sql(
                    route_result.sql_query.query,
                    route_result.sql_query.params,
                    limit,
                )
                response["results"] = results
                response["result_count"] = len(results)
            except Exception as e:
                logger.error(f"SQL execution failed: {e}")
                response["execution_error"] = str(e)

    # Add embedding query if semantic
    if route_result.embedding_query:
        response["embedding_query"] = route_result.embedding_query

    # Add clarification if needed
    if route_result.query_type == QueryType.CLARIFICATION:
        response["clarification"] = {
            "needed": True,
            "question": route_result.translation.clarification_question,
            "suggestions": _generate_suggestions(route_result.translation),
        }

    return response


async def execute_sql(query: str, params: list, limit: int) -> list[dict]:
    """
    Execute SQL query against PostgreSQL.

    Args:
        query: Parameterized SQL query
        params: Query parameters
        limit: Result limit

    Returns:
        List of result dictionaries
    """
    global _db_credentials

    try:
        import pg8000
    except ImportError:
        logger.error("pg8000 not available")
        raise RuntimeError("Database driver not available")

    # Get credentials
    if _db_credentials is None:
        logger.info("Fetching database credentials")
        secret_response = secrets_client.get_secret_value(SecretId=DB_SECRET_ARN)
        _db_credentials = json.loads(secret_response["SecretString"])

    # Connect and execute
    conn = pg8000.connect(
        host=_db_credentials["host"],
        port=int(_db_credentials.get("port", 5432)),
        database=_db_credentials.get("dbname", "cagenai"),
        user=_db_credentials["username"],
        password=_db_credentials["password"],
        ssl_context=True,
    )

    try:
        cursor = conn.cursor()

        # Add LIMIT if not already in query
        if "LIMIT" not in query.upper():
            query = f"{query} LIMIT {limit}"
            params = list(params)  # Don't modify original
        else:
            # Replace existing LIMIT if it's larger than requested
            import re
            match = re.search(r"LIMIT\s+(\d+)", query, re.IGNORECASE)
            if match and int(match.group(1)) > limit:
                query = re.sub(r"LIMIT\s+\d+", f"LIMIT {limit}", query, flags=re.IGNORECASE)

        logger.info(f"Executing SQL: {query[:200]}...")
        cursor.execute(query, params)

        # Get column names
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        # Fetch results
        rows = cursor.fetchall()
        results = []

        for row in rows:
            result = {}
            for i, col in enumerate(columns):
                value = row[i]
                # Convert non-serializable types
                if hasattr(value, "isoformat"):
                    value = value.isoformat()
                elif isinstance(value, (bytes, bytearray)):
                    value = value.decode("utf-8", errors="replace")
                elif hasattr(value, "__str__") and not isinstance(value, (str, int, float, bool, type(None), list, dict)):
                    value = str(value)
                result[col] = value
            results.append(result)

        logger.info(f"Query returned {len(results)} results")
        return results

    finally:
        cursor.close()
        conn.close()


def run_job_matching(query: str, limit: int = 10) -> dict | None:
    """
    Run intelligent job matching for queries that return 0 results.

    Uses the JobMatcher to find candidates matching MOST criteria.

    Args:
        query: Natural language query
        limit: Maximum candidates to return

    Returns:
        Job matching result dict or None on failure
    """
    global _db_credentials

    try:
        import pg8000
        from lcmgo_cagenai.matching import JobMatcher, ResponseFormatter
        from lcmgo_cagenai.llm import BedrockProvider
    except ImportError as e:
        logger.error(f"Failed to import job matching modules: {e}")
        return None

    # Get credentials if needed
    if _db_credentials is None and DB_SECRET_ARN:
        secret_response = secrets_client.get_secret_value(SecretId=DB_SECRET_ARN)
        _db_credentials = json.loads(secret_response["SecretString"])

    if not _db_credentials:
        logger.error("No database credentials available for job matching")
        return None

    # Create database connection
    conn = pg8000.connect(
        host=_db_credentials["host"],
        port=int(_db_credentials.get("port", 5432)),
        database=_db_credentials.get("dbname", "cagenai"),
        user=_db_credentials["username"],
        password=_db_credentials["password"],
        ssl_context=True,
    )

    try:
        # Create LLM provider
        llm = BedrockProvider(region=AWS_REGION)

        # Create job matcher
        matcher = JobMatcher(db_connection=conn, llm_provider=llm)

        # Run matching
        result = matcher.match(query, limit=limit)

        # Format as JSON
        formatted = ResponseFormatter.format_as_json(result)

        # Also include formatted text response
        formatted["formatted_response"] = ResponseFormatter.format_match_result(result)

        # Ensure all UUIDs and Decimals are serializable
        # by round-tripping through JSON
        formatted = json.loads(json.dumps(formatted, cls=JSONEncoderWithUUID))

        return formatted

    except Exception as e:
        logger.error(f"Job matching failed: {e}")
        return None
    finally:
        conn.close()


def _parse_request(event: dict) -> dict:
    """Parse request from direct invocation or API Gateway."""
    # Check for API Gateway format
    if "body" in event:
        body = event.get("body", "{}")
        if isinstance(body, str):
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON in request body")
        return body

    # Direct invocation format
    return event


def _check_cache(query: str) -> dict | None:
    """Check query cache in DynamoDB."""
    try:
        import hashlib
        query_hash = hashlib.sha256(query.lower().encode()).hexdigest()[:16]

        table = dynamodb.Table(QUERY_CACHE_TABLE)
        response = table.get_item(Key={"query_hash": query_hash})

        item = response.get("Item")
        if item:
            # Check TTL (24 hours)
            cached_at = item.get("cached_at", 0)
            if time.time() - cached_at < 86400:  # 24 hours
                logger.info(f"Cache hit: {query_hash}")
                return json.loads(item.get("result", "{}"))

    except Exception as e:
        logger.warning(f"Cache check failed: {e}")

    return None


def _cache_result(query: str, result: dict) -> None:
    """Cache query result in DynamoDB."""
    try:
        import hashlib
        query_hash = hashlib.sha256(query.lower().encode()).hexdigest()[:16]

        # Remove execution-specific fields
        cache_result = {k: v for k, v in result.items()
                       if k not in ("request_id", "latency_ms", "cached", "results", "result_count")}

        table = dynamodb.Table(QUERY_CACHE_TABLE)
        table.put_item(Item={
            "query_hash": query_hash,
            "query": query[:500],  # Truncate for storage
            "result": json.dumps(cache_result),
            "cached_at": int(time.time()),
            "ttl": int(time.time()) + 86400,  # 24 hour TTL
        })
        logger.info(f"Cached result: {query_hash}")

    except Exception as e:
        logger.warning(f"Cache write failed: {e}")


def _generate_suggestions(translation) -> list[str]:
    """Generate query suggestions based on unknown terms."""
    suggestions = []

    if translation.unknown_terms:
        suggestions.append(f"Δοκιμάστε να αντικαταστήσετε: {', '.join(translation.unknown_terms[:3])}")

    if not translation.has_filters():
        suggestions.extend([
            "Προσθέστε τοποθεσία (π.χ. Αθήνα, Θεσσαλονίκη)",
            "Προσθέστε εμπειρία (π.χ. 5+ χρόνια)",
            "Προσθέστε δεξιότητες (π.χ. SAP, Excel)",
        ])

    return suggestions


def _success_response(data: dict) -> dict:
    """Build success response."""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(data, ensure_ascii=False, default=str),
    }


def _error_response(status_code: int, message: str, request_id: str) -> dict:
    """Build error response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({
            "error": message,
            "request_id": request_id,
        }, ensure_ascii=False),
    }


# For local testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python handler.py 'λογιστής με SAP' [--execute]")
        sys.exit(1)

    query = sys.argv[1]
    execute = "--execute" in sys.argv

    # Simulate direct invocation
    event = {
        "query": query,
        "execute": execute,
        "limit": 10,
    }

    result = handler(event, None)
    print(json.dumps(json.loads(result["body"]), indent=2, ensure_ascii=False))
