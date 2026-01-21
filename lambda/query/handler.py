"""
Query Lambda Handler.

Exposes Text-to-SQL functionality via API.
Translates natural language HR queries (Greek/English) into PostgreSQL queries.

Supports:
- Direct invocation (from other Lambdas)
- API Gateway integration (POST /query)
- Intelligent job matching fallback when strict query returns 0 results
- HR Intelligence analysis for candidate evaluation (Phase 3)
- Async mode for long-running HR analysis (avoids API Gateway 30s timeout)

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

# Lambda client for async invocation
lambda_client = boto3.client("lambda")


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
        "context": {},              // Optional: additional context
        "include_hr_analysis": true, // Optional: include HR Intelligence analysis (default: false)
        "async_hr": true,           // Optional: run HR analysis asynchronously (returns job_id)
        "job_id": "abc123"          // Optional: fetch async HR results by job_id
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
        Query result with SQL, candidates, and HR analysis
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
        include_hr_analysis = body.get("include_hr_analysis", False)  # Default: disabled (for fast 30s responses)
        async_hr = body.get("async_hr", False)  # Run HR analysis asynchronously
        job_id = body.get("job_id")  # Fetch async results by job_id
        is_async_worker = body.get("_async_worker", False)  # Internal: marks async invocation

        # If job_id provided, fetch and return async HR results
        if job_id:
            return _fetch_async_results(job_id, request_id)

        if not user_query:
            return _error_response(400, "Missing 'query' parameter", request_id)

        logger.info(f"Processing query: '{user_query[:100]}...' execute={execute}")

        # Handle async worker mode - just run HR analysis on pre-fetched data
        if is_async_worker:
            logger.info(f"Async worker mode for job: {body.get('_job_id')}")
            candidates = body.get("_candidates", [])
            if candidates:
                try:
                    hr_analysis = run_hr_intelligence(
                        user_query=user_query,
                        candidates=candidates,
                        translation=body.get("_translation", {}),
                        direct_count=body.get("_direct_count", 0),
                        total_count=body.get("_total_count", len(candidates)),
                        relaxation_applied=body.get("_relaxation_applied", False),
                    )
                    if hr_analysis:
                        _store_async_job(body["_job_id"], {
                            "status": "completed",
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                            "hr_analysis": hr_analysis,
                        })
                        logger.info(f"Async HR completed for job: {body['_job_id']}")
                except Exception as e:
                    logger.error(f"Async HR analysis failed: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    _store_async_job(body["_job_id"], {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    })
            return _success_response({"status": "async_worker_done", "job_id": body.get("_job_id")})

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
        relaxation_applied = False
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
                    relaxation_applied = True
                    logger.info(f"Job matching found {job_match_result.get('total_found')} candidates")
            except Exception as e:
                logger.warning(f"Job matching fallback failed: {e}")
                result["job_matching_error"] = str(e)

        # HR Intelligence Analysis (Phase 3)
        # Run HR analysis on the candidates if requested and we have results
        if execute and include_hr_analysis:
            candidates_to_analyze = result.get("results", [])

            # If job matching was used, get candidates from there instead
            if result.get("fallback_used") and result.get("job_matching"):
                job_matching_candidates = result["job_matching"].get("candidates", [])
                if job_matching_candidates:
                    candidates_to_analyze = job_matching_candidates

            if candidates_to_analyze:
                # Async mode: return immediately and process HR in background
                if async_hr and not is_async_worker:
                    logger.info(f"Starting async HR analysis for {len(candidates_to_analyze)} candidates")
                    hr_job_id = f"hr-{request_id}"

                    # Store initial results in DynamoDB
                    _store_async_job(hr_job_id, {
                        "status": "processing",
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "query": user_query,
                        "candidate_count": len(candidates_to_analyze),
                    })

                    # Invoke Lambda asynchronously for HR analysis
                    _invoke_async_hr(
                        query=user_query,
                        candidates=candidates_to_analyze,
                        translation=result.get("translation", {}),
                        direct_count=result.get("result_count", 0) if not relaxation_applied else 0,
                        total_count=len(candidates_to_analyze),
                        relaxation_applied=relaxation_applied,
                        job_id=hr_job_id,
                    )

                    result["hr_job_id"] = hr_job_id
                    result["hr_status"] = "processing"
                    logger.info(f"Async HR job started: {hr_job_id}")
                else:
                    # Sync mode: run HR analysis now
                    logger.info(f"Running HR Intelligence analysis on {len(candidates_to_analyze)} candidates")
                    hr_start_time = time.time()
                    try:
                        hr_analysis = run_hr_intelligence(
                            user_query=user_query,
                            candidates=candidates_to_analyze,
                            translation=result.get("translation", {}),
                            direct_count=result.get("result_count", 0) if not relaxation_applied else 0,
                            total_count=len(candidates_to_analyze),
                            relaxation_applied=relaxation_applied,
                        )
                        if hr_analysis:
                            result["hr_analysis"] = hr_analysis
                            result["hr_analysis"]["latency_ms"] = int((time.time() - hr_start_time) * 1000)
                            logger.info(f"HR analysis completed in {result['hr_analysis']['latency_ms']}ms")

                            # If this is async worker, store results
                            if is_async_worker and body.get("_job_id"):
                                _store_async_job(body["_job_id"], {
                                    "status": "completed",
                                    "completed_at": datetime.now(timezone.utc).isoformat(),
                                    "hr_analysis": hr_analysis,
                                })
                                logger.info(f"Async HR results stored for job: {body['_job_id']}")
                    except Exception as e:
                        logger.warning(f"HR Intelligence analysis failed: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        result["hr_analysis_error"] = str(e)

                        # Store error if async worker
                        if is_async_worker and body.get("_job_id"):
                            _store_async_job(body["_job_id"], {
                                "status": "failed",
                                "error": str(e),
                                "completed_at": datetime.now(timezone.utc).isoformat(),
                            })
            else:
                logger.info("No candidates to analyze for HR Intelligence")

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


def enrich_candidates(candidate_ids: list[str]) -> dict[str, dict]:
    """
    Enrich candidate data by fetching full profiles from PostgreSQL.

    Uses the get_candidate_full_profile() function to get complete data
    including experience, skills, software, certifications, education, languages.

    Args:
        candidate_ids: List of candidate UUIDs

    Returns:
        Dictionary mapping candidate_id to transformed profile data
        ready for CandidateProfile creation
    """
    global _db_credentials

    if not candidate_ids:
        return {}

    try:
        import pg8000
    except ImportError:
        logger.error("pg8000 not available for enrichment")
        return {}

    # Get credentials if needed
    if _db_credentials is None and DB_SECRET_ARN:
        secret_response = secrets_client.get_secret_value(SecretId=DB_SECRET_ARN)
        _db_credentials = json.loads(secret_response["SecretString"])

    if not _db_credentials:
        logger.error("No database credentials available for enrichment")
        return {}

    conn = pg8000.connect(
        host=_db_credentials["host"],
        port=int(_db_credentials.get("port", 5432)),
        database=_db_credentials.get("dbname", "cagenai"),
        user=_db_credentials["username"],
        password=_db_credentials["password"],
        ssl_context=True,
    )

    enriched = {}
    cursor = conn.cursor()

    try:
        for candidate_id in candidate_ids:
            try:
                cursor.execute(
                    "SELECT get_candidate_full_profile(%s)",
                    (candidate_id,)
                )
                result = cursor.fetchone()

                if result and result[0]:
                    raw_profile = result[0] if isinstance(result[0], dict) else json.loads(result[0])

                    # Transform PostgreSQL function output to CandidateProfile format
                    transformed = _transform_profile_for_hr(raw_profile)
                    enriched[candidate_id] = transformed

                    logger.debug(
                        f"Enriched candidate {candidate_id}: "
                        f"roles={len(transformed.get('roles', []))}, "
                        f"software={len(transformed.get('software', []))}, "
                        f"exp={transformed.get('total_experience_years', 0):.1f}y"
                    )
            except Exception as e:
                logger.warning(f"Failed to enrich candidate {candidate_id}: {e}")
                continue

        logger.info(f"Enriched {len(enriched)} of {len(candidate_ids)} candidates")
        return enriched

    finally:
        cursor.close()
        conn.close()


def _transform_profile_for_hr(raw_profile: dict) -> dict:
    """
    Transform PostgreSQL get_candidate_full_profile() output to CandidateProfile format.

    PostgreSQL returns:
    - name: "First Last"
    - experience: [{company, role, role_en, duration_months, ...}]
    - skills: [{name, name_en, level}]
    - software: [{name, level}]
    - certifications: [{name, name_en, issuer, date}]
    - languages: [{code, level}]
    - education: [{institution, degree, field, level, graduation_year}]

    CandidateProfile needs:
    - first_name, last_name (separate)
    - roles: list[str] (unique roles from experience)
    - software: list[str] (just names)
    - skills: list[str] (just names)
    - certifications: list[str] (just names)
    - languages: list[dict] (code, level)
    - education: list[dict]
    - experience_entries: list[dict]
    """
    # Split name
    full_name = raw_profile.get("name", "")
    name_parts = full_name.split(" ", 1) if full_name else ["", ""]
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Extract unique roles from experience
    experience_list = raw_profile.get("experience") or []
    roles = []
    for exp in experience_list:
        role = exp.get("role") or exp.get("role_en")
        if role and role not in roles:
            roles.append(role)

    # Transform experience entries
    experience_entries = []
    for exp in experience_list:
        experience_entries.append({
            "role": exp.get("role") or exp.get("role_en", ""),
            "company": exp.get("company", ""),
            "duration_months": exp.get("duration_months", 0),
            "start_date": exp.get("start_date"),
            "end_date": exp.get("end_date"),
            "description": exp.get("description"),
        })

    # Extract software names
    software_list = raw_profile.get("software") or []
    software = [s.get("name", "") for s in software_list if s.get("name")]

    # Extract skill names
    skills_list = raw_profile.get("skills") or []
    skills = [s.get("name") or s.get("name_en", "") for s in skills_list if s.get("name") or s.get("name_en")]

    # Extract certification names
    certs_list = raw_profile.get("certifications") or []
    certifications = [c.get("name") or c.get("name_en", "") for c in certs_list if c.get("name") or c.get("name_en")]

    # Languages - keep code and level
    languages_list = raw_profile.get("languages") or []
    languages = [
        {"code": lang.get("code", ""), "level": lang.get("level", "")}
        for lang in languages_list
        if lang.get("code")
    ]

    # Education - keep as is but normalize field names
    education_list = raw_profile.get("education") or []
    education = [
        {
            "institution": edu.get("institution", ""),
            "degree": edu.get("degree", ""),
            "field": edu.get("field", ""),
            "level": edu.get("level", ""),
            "graduation_year": edu.get("graduation_year"),
        }
        for edu in education_list
    ]

    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": raw_profile.get("email"),
        "phone": raw_profile.get("phone"),
        "city": raw_profile.get("city"),
        "region": raw_profile.get("region"),
        "total_experience_years": raw_profile.get("total_experience_years", 0),
        "roles": roles,
        "software": software,
        "skills": skills,
        "soft_skills": [],  # Not in PostgreSQL function output
        "certifications": certifications,
        "languages": languages,
        "education": education,
        "experience_entries": experience_entries,
    }


def run_hr_intelligence(
    user_query: str,
    candidates: list[dict],
    translation: dict,
    direct_count: int,
    total_count: int,
    relaxation_applied: bool,
) -> dict | None:
    """
    Run HR Intelligence analysis on candidates.

    Args:
        user_query: Original user query
        candidates: List of candidate dictionaries from SQL results
        translation: Query translation with filters
        direct_count: Number of direct matches (before relaxation)
        total_count: Total number of candidates
        relaxation_applied: Whether criteria relaxation was used

    Returns:
        HR analysis result dict or None on failure
    """
    try:
        from lcmgo_cagenai.hr_intelligence import (
            HRIntelligenceAnalyzer,
            HRAnalysisInput,
            JobRequirements,
            CandidateProfile,
            format_api_response,
        )
        from lcmgo_cagenai.llm import BedrockProvider
    except ImportError as e:
        logger.error(f"Failed to import HR Intelligence modules: {e}")
        return None

    if not candidates:
        logger.info("No candidates provided for HR analysis")
        return None

    try:
        # Create LLM provider
        llm = BedrockProvider(region=AWS_REGION)

        # Create analyzer
        analyzer = HRIntelligenceAnalyzer(llm)

        # CRITICAL: Enrich candidates with full profiles before analysis
        # The SQL query only returns basic info (id, name, email)
        # We need full profiles (experience, skills, software, certifications, etc.)
        candidate_ids = [str(c.get("candidate_id", c.get("id", ""))) for c in candidates]
        enriched_data = enrich_candidates(candidate_ids)
        logger.info(f"Enriched {len(enriched_data)} candidates for HR analysis")

        # Convert raw candidate dictionaries to CandidateProfile objects
        candidate_profiles = []
        for c in candidates:
            try:
                candidate_id = str(c.get("candidate_id", c.get("id", "")))

                # Merge enriched data with original candidate data
                enriched = enriched_data.get(candidate_id, {})

                profile = CandidateProfile(
                    candidate_id=candidate_id,
                    first_name=enriched.get("first_name") or c.get("first_name", ""),
                    last_name=enriched.get("last_name") or c.get("last_name", ""),
                    email=enriched.get("email") or c.get("email"),
                    total_experience_years=_parse_float(enriched.get("total_experience_years") or c.get("total_experience_years")),
                    roles=enriched.get("roles", []) if enriched.get("roles") else (c.get("roles", []) if isinstance(c.get("roles"), list) else []),
                    skills=enriched.get("skills", []) if enriched.get("skills") else (c.get("skills", []) if isinstance(c.get("skills"), list) else []),
                    soft_skills=enriched.get("soft_skills", []) if enriched.get("soft_skills") else (c.get("soft_skills", []) if isinstance(c.get("soft_skills"), list) else []),
                    software=enriched.get("software", []) if enriched.get("software") else (c.get("software", []) if isinstance(c.get("software"), list) else []),
                    certifications=enriched.get("certifications", []) if enriched.get("certifications") else (c.get("certifications", []) if isinstance(c.get("certifications"), list) else []),
                    languages=enriched.get("languages", []) if enriched.get("languages") else (c.get("languages", []) if isinstance(c.get("languages"), list) else []),
                    education=enriched.get("education", []) if enriched.get("education") else (c.get("education", []) if isinstance(c.get("education"), list) else []),
                    city=enriched.get("city") or c.get("city") or c.get("current_location") or c.get("location") or c.get("address_city"),
                    region=enriched.get("region") or c.get("region") or c.get("address_region"),
                    experience_entries=enriched.get("experience_entries", []) if enriched.get("experience_entries") else (c.get("experience_entries", []) if isinstance(c.get("experience_entries"), list) else []),
                )
                candidate_profiles.append(profile)
            except Exception as e:
                logger.warning(f"Failed to create CandidateProfile for {c.get('candidate_id')}: {e}")
                continue

        if not candidate_profiles:
            logger.warning("No valid candidate profiles could be created")
            return None

        # Create JobRequirements from translation filters
        filters = translation.get("filters", {})
        requirements = JobRequirements(
            source_type="query",
            source_text=user_query,
            detected_language="el" if _is_greek(user_query) else "en",
            roles=filters.get("role", []) if isinstance(filters.get("role"), list) else [filters.get("role")] if filters.get("role") else [],
            min_experience_years=filters.get("min_experience"),
            max_experience_years=filters.get("max_experience"),
            software=filters.get("software", []) if isinstance(filters.get("software"), list) else [],
            skills=filters.get("skills", []) if isinstance(filters.get("skills"), list) else [],
            certifications=filters.get("certifications", []) if isinstance(filters.get("certifications"), list) else [],
            locations=filters.get("location", []) if isinstance(filters.get("location"), list) else [filters.get("location")] if filters.get("location") else [],
            education_level=filters.get("education_level"),
            education_fields=filters.get("education_field", []) if isinstance(filters.get("education_field"), list) else [],
        )

        # Build relaxations list if applicable
        relaxations_applied = []
        if relaxation_applied:
            relaxations_applied.append("Criteria relaxation was applied to find more candidates")

        # Create input for analyzer
        analysis_input = HRAnalysisInput(
            original_query=user_query,
            requirements=requirements,
            candidates=candidate_profiles,
            direct_result_count=direct_count,
            total_result_count=total_count,
            relaxations_applied=relaxations_applied,
        )

        # Run analysis
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(analyzer.analyze(analysis_input))
        finally:
            loop.close()

        # Format for API response
        return format_api_response(report)

    except Exception as e:
        logger.error(f"HR Intelligence analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def _parse_float(value) -> float | None:
    """Safely parse a float value."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_greek(text: str) -> bool:
    """Check if text contains Greek characters."""
    return any('\u0370' <= char <= '\u03FF' or '\u1F00' <= char <= '\u1FFF' for char in text)


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


# =============================================================================
# ASYNC HR ANALYSIS HELPERS
# =============================================================================

def _fetch_async_results(job_id: str, request_id: str) -> dict:
    """Fetch async HR analysis results by job_id."""
    try:
        table = dynamodb.Table(QUERY_CACHE_TABLE)
        response = table.get_item(Key={"cache_key": f"async:{job_id}"})

        if "Item" not in response:
            return _error_response(404, f"Job not found: {job_id}", request_id)

        item = response["Item"]
        status = item.get("status", "unknown")

        result = {
            "job_id": job_id,
            "status": status,
            "request_id": request_id,
        }

        if status == "completed":
            result["hr_analysis"] = item.get("hr_analysis", {})
        elif status == "failed":
            result["error"] = item.get("error", "Unknown error")
        elif status == "processing":
            result["started_at"] = item.get("started_at")
            result["candidate_count"] = item.get("candidate_count", 0)

        return _success_response(result)

    except Exception as e:
        logger.error(f"Failed to fetch async results: {e}")
        return _error_response(500, f"Failed to fetch results: {e}", request_id)


def _store_async_job(job_id: str, data: dict) -> None:
    """Store async job data in DynamoDB."""
    try:
        table = dynamodb.Table(QUERY_CACHE_TABLE)

        item = {
            "cache_key": f"async:{job_id}",
            "job_id": job_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "ttl": int(time.time()) + 3600,  # 1 hour TTL
            **data,
        }

        # Convert any nested dicts/lists that might have non-DynamoDB types
        item = json.loads(json.dumps(item, default=str))

        table.put_item(Item=item)
        logger.info(f"Stored async job: {job_id}")

    except Exception as e:
        logger.error(f"Failed to store async job: {e}")


def _invoke_async_hr(
    query: str,
    candidates: list,
    translation: dict,
    direct_count: int,
    total_count: int,
    relaxation_applied: bool,
    job_id: str,
) -> None:
    """Invoke Lambda asynchronously for HR analysis."""
    try:
        function_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "lcmgo-cagenai-prod-query")

        payload = {
            "query": query,
            "execute": True,
            "include_hr_analysis": True,
            "_async_worker": True,  # Mark as async worker
            "_job_id": job_id,
            "_candidates": candidates,
            "_translation": translation,
            "_direct_count": direct_count,
            "_total_count": total_count,
            "_relaxation_applied": relaxation_applied,
        }

        lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="Event",  # Async invocation
            Payload=json.dumps(payload, default=str),
        )

        logger.info(f"Async HR invocation triggered for job: {job_id}")

    except Exception as e:
        logger.error(f"Failed to invoke async HR: {e}")
        # Store failure in DynamoDB
        _store_async_job(job_id, {
            "status": "failed",
            "error": f"Failed to start async processing: {e}",
        })


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
