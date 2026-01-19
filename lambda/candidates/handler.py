"""
Candidates API Lambda Handler.

Lists, retrieves, and deletes candidates from PostgreSQL database.
"""

import json
import logging
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import boto3
import pg8000.native

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Database configuration
DB_SECRET_ARN = os.environ.get("DB_SECRET_ARN", "lcmgo-cagenai-prod-db-credentials")
DB_HOST = os.environ.get("DB_HOST", "lcmgo-cagenai-prod-postgres.c324io6eq6iv.eu-north-1.rds.amazonaws.com")
DB_NAME = os.environ.get("DB_NAME", "cagenai")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
AWS_REGION = os.environ.get("AWS_REGION_NAME", "eu-north-1")


def get_db_credentials() -> dict:
    """Get database credentials from Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=AWS_REGION)
    response = client.get_secret_value(SecretId=DB_SECRET_ARN)
    return json.loads(response["SecretString"])


def get_db_connection():
    """Get database connection."""
    creds = get_db_credentials()
    return pg8000.native.Connection(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=creds["username"],
        password=creds["password"],
        ssl_context=True,
    )


def json_serializer(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    # Handle UUID type
    if hasattr(obj, 'hex'):  # UUID has a hex attribute
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def build_response(status_code: int, body: dict) -> dict:
    """Build API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, DELETE, OPTIONS",
        },
        "body": json.dumps(body, default=json_serializer),
    }


def list_candidates(conn, limit: int = 100, offset: int = 0) -> list:
    """List all candidates with their full data."""

    # Get candidates with basic info
    candidates_query = """
        SELECT
            c.id,
            c.first_name,
            c.last_name,
            c.email,
            c.phone,
            c.date_of_birth,
            c.nationality,
            c.address_street,
            c.address_city,
            c.address_postal_code,
            c.address_country,
            c.military_status,
            c.created_at,
            c.updated_at,
            c.quality_score,
            cd.file_name,
            cd.s3_key
        FROM candidates c
        LEFT JOIN candidate_documents cd ON c.id = cd.candidate_id AND cd.is_primary = true
        ORDER BY c.created_at DESC
        LIMIT :limit OFFSET :offset
    """

    rows = conn.run(candidates_query, limit=limit, offset=offset)
    columns = [
        "candidate_id", "first_name", "last_name", "email", "phone",
        "date_of_birth", "nationality", "address_street", "address_city",
        "address_postal_code", "address_country", "military_status",
        "created_at", "updated_at", "quality_score",
        "original_filename", "s3_key"
    ]

    candidates = []
    for row in rows:
        candidate = dict(zip(columns, row))
        candidate_id = candidate["candidate_id"]

        # Get experience
        candidate["experience"] = get_candidate_experience(conn, candidate_id)

        # Get education
        candidate["education"] = get_candidate_education(conn, candidate_id)

        # Get skills
        candidate["skills"] = get_candidate_skills(conn, candidate_id)

        # Get languages
        candidate["languages"] = get_candidate_languages(conn, candidate_id)

        # Get certifications
        candidate["certifications"] = get_candidate_certifications(conn, candidate_id)

        # Get training
        candidate["training"] = get_candidate_training(conn, candidate_id)

        # Get software
        candidate["software"] = get_candidate_software(conn, candidate_id)

        # Get driving licenses
        candidate["driving_licenses"] = get_candidate_licenses(conn, candidate_id)

        candidates.append(candidate)

    return candidates


def get_candidate_experience(conn, candidate_id: str) -> list:
    """Get candidate work experience."""
    query = """
        SELECT job_title, company_name, start_date, end_date, is_current, description
        FROM candidate_experience
        WHERE candidate_id = :candidate_id
        ORDER BY COALESCE(end_date, CURRENT_DATE) DESC, start_date DESC
    """
    rows = conn.run(query, candidate_id=candidate_id)
    return [
        {
            "job_title": r[0],
            "company_name": r[1],
            "start_date": r[2].isoformat() if r[2] else None,
            "end_date": r[3].isoformat() if r[3] else None,
            "is_current": r[4],
            "description": r[5],
        }
        for r in rows
    ]


def get_candidate_education(conn, candidate_id: str) -> list:
    """Get candidate education."""
    query = """
        SELECT institution_name, degree_level, degree_title, field_of_study,
               graduation_year, grade_value
        FROM candidate_education
        WHERE candidate_id = :candidate_id
        ORDER BY graduation_year DESC NULLS LAST
    """
    rows = conn.run(query, candidate_id=candidate_id)
    return [
        {
            "institution_name": r[0],
            "degree_level": str(r[1]) if r[1] else None,
            "degree_title": r[2],
            "field_of_study": str(r[3]) if r[3] else None,
            "graduation_year": r[4],
            "grade": r[5],
        }
        for r in rows
    ]


def get_candidate_skills(conn, candidate_id: str) -> list:
    """Get candidate skills (both technical and soft)."""
    query = """
        SELECT COALESCE(st.name_el, st.name_en), cs.skill_level, cs.years_of_experience, st.category
        FROM candidate_skills cs
        JOIN skill_taxonomy st ON cs.skill_id = st.id
        WHERE cs.candidate_id = :candidate_id
        ORDER BY st.category, st.name_en
    """
    rows = conn.run(query, candidate_id=candidate_id)
    return [
        {
            "name": r[0],
            "level": str(r[1]) if r[1] else None,
            "years": float(r[2]) if r[2] else None,
            "category": str(r[3]) if r[3] else "technical",
        }
        for r in rows
    ]


def get_candidate_languages(conn, candidate_id: str) -> list:
    """Get candidate languages."""
    query = """
        SELECT language_name, proficiency_level, is_native
        FROM candidate_languages
        WHERE candidate_id = :candidate_id
        ORDER BY is_native DESC NULLS LAST, language_name
    """
    rows = conn.run(query, candidate_id=candidate_id)
    return [
        {
            "language_name": r[0],
            "proficiency_level": str(r[1]) if r[1] else None,
            "is_native": r[2],
        }
        for r in rows
    ]


def get_candidate_certifications(conn, candidate_id: str) -> list:
    """Get candidate certifications."""
    query = """
        SELECT certification_name, issuing_organization, issue_date,
               expiry_date, credential_id
        FROM candidate_certifications
        WHERE candidate_id = :candidate_id
        ORDER BY issue_date DESC NULLS LAST
    """
    rows = conn.run(query, candidate_id=candidate_id)
    return [
        {
            "certification_name": r[0],
            "issuing_organization": r[1],
            "issue_date": r[2].isoformat() if r[2] else None,
            "expiry_date": r[3].isoformat() if r[3] else None,
            "credential_id": r[4],
        }
        for r in rows
    ]


def get_candidate_training(conn, candidate_id: str) -> list:
    """Get candidate training/seminars."""
    query = """
        SELECT training_name, provider_name, completion_date, duration_hours
        FROM candidate_training
        WHERE candidate_id = :candidate_id
        ORDER BY completion_date DESC NULLS LAST
    """
    rows = conn.run(query, candidate_id=candidate_id)
    return [
        {
            "training_name": r[0],
            "provider_name": r[1],
            "completion_date": r[2].isoformat() if r[2] else None,
            "duration_hours": r[3],
        }
        for r in rows
    ]


def get_candidate_software(conn, candidate_id: str) -> list:
    """Get candidate software proficiencies."""
    query = """
        SELECT st.name, cs.proficiency_level, cs.years_of_experience
        FROM candidate_software cs
        JOIN software_taxonomy st ON cs.software_id = st.id
        WHERE cs.candidate_id = :candidate_id
        ORDER BY st.name
    """
    rows = conn.run(query, candidate_id=candidate_id)
    return [
        {
            "name": r[0],
            "proficiency_level": str(r[1]) if r[1] else None,
            "years_experience": float(r[2]) if r[2] else None,
        }
        for r in rows
    ]


def get_candidate_licenses(conn, candidate_id: str) -> list:
    """Get candidate driving licenses."""
    query = """
        SELECT license_category, issue_date, expiry_date
        FROM candidate_driving_licenses
        WHERE candidate_id = :candidate_id
        ORDER BY license_category
    """
    rows = conn.run(query, candidate_id=candidate_id)
    return [
        {
            "license_category": r[0],
            "issue_date": r[1].isoformat() if r[1] else None,
            "expiry_date": r[2].isoformat() if r[2] else None,
        }
        for r in rows
    ]


def get_candidate_by_id(conn, candidate_id: str) -> dict | None:
    """Get a single candidate by ID with full data."""
    # Query for specific candidate
    query = """
        SELECT
            c.id,
            c.first_name,
            c.last_name,
            c.email,
            c.phone,
            c.date_of_birth,
            c.nationality,
            c.address_street,
            c.address_city,
            c.address_postal_code,
            c.address_country,
            c.military_status,
            c.created_at,
            c.updated_at,
            c.quality_score,
            cd.file_name,
            cd.s3_key
        FROM candidates c
        LEFT JOIN candidate_documents cd ON c.id = cd.candidate_id AND cd.is_primary = true
        WHERE c.id = :candidate_id
    """

    rows = conn.run(query, candidate_id=candidate_id)
    if not rows:
        return None

    columns = [
        "candidate_id", "first_name", "last_name", "email", "phone",
        "date_of_birth", "nationality", "address_street", "address_city",
        "address_postal_code", "address_country", "military_status",
        "created_at", "updated_at", "quality_score",
        "original_filename", "s3_key"
    ]

    candidate = dict(zip(columns, rows[0]))
    cid = candidate["candidate_id"]

    candidate["experience"] = get_candidate_experience(conn, cid)
    candidate["education"] = get_candidate_education(conn, cid)
    candidate["skills"] = get_candidate_skills(conn, cid)
    candidate["languages"] = get_candidate_languages(conn, cid)
    candidate["certifications"] = get_candidate_certifications(conn, cid)
    candidate["training"] = get_candidate_training(conn, cid)
    candidate["software"] = get_candidate_software(conn, cid)
    candidate["driving_licenses"] = get_candidate_licenses(conn, cid)

    return candidate


def delete_candidate(conn, candidate_id: str) -> bool:
    """Delete a candidate and all related data."""
    # Check if exists
    check = conn.run(
        "SELECT id FROM candidates WHERE id = :candidate_id",
        candidate_id=candidate_id
    )
    if not check:
        return False

    # Delete related data (foreign keys should cascade, but be explicit)
    tables = [
        "candidate_experience",
        "candidate_education",
        "candidate_skills",
        "candidate_languages",
        "candidate_certifications",
        "candidate_training",
        "candidate_software",
        "candidate_driving_licenses",
        "candidate_documents",
        "unmatched_taxonomy_items",
        "unmatched_cv_data",
    ]

    for table in tables:
        try:
            conn.run(f"DELETE FROM {table} WHERE candidate_id = :candidate_id", candidate_id=candidate_id)
        except Exception as e:
            logger.warning(f"Error deleting from {table}: {e}")

    # Delete candidate
    conn.run("DELETE FROM candidates WHERE id = :candidate_id", candidate_id=candidate_id)

    return True


def get_candidates_count(conn) -> int:
    """Get total count of candidates."""
    result = conn.run("SELECT COUNT(*) FROM candidates")
    return result[0][0] if result else 0


def handler(event, context):
    """Lambda handler for candidates API."""
    logger.info(f"Event: {json.dumps(event)}")

    http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "")
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    # Handle OPTIONS for CORS
    if http_method == "OPTIONS":
        return build_response(200, {"message": "OK"})

    try:
        conn = get_db_connection()

        # GET /test/candidates - List all candidates
        if http_method == "GET" and not path_params.get("candidate_id"):
            limit = int(query_params.get("limit", 100))
            offset = int(query_params.get("offset", 0))

            candidates = list_candidates(conn, limit=limit, offset=offset)
            total = get_candidates_count(conn)

            conn.close()

            return build_response(200, {
                "candidates": candidates,
                "total": total,
                "limit": limit,
                "offset": offset,
            })

        # GET /test/candidates/{candidate_id} - Get single candidate
        if http_method == "GET" and path_params.get("candidate_id"):
            candidate_id = path_params["candidate_id"]
            candidate = get_candidate_by_id(conn, candidate_id)

            conn.close()

            if not candidate:
                return build_response(404, {"error": "Candidate not found"})

            return build_response(200, {"candidate": candidate})

        # DELETE /test/candidates/{candidate_id} - Delete candidate
        if http_method == "DELETE" and path_params.get("candidate_id"):
            candidate_id = path_params["candidate_id"]
            deleted = delete_candidate(conn, candidate_id)

            conn.close()

            if not deleted:
                return build_response(404, {"error": "Candidate not found"})

            return build_response(200, {"message": "Candidate deleted", "candidate_id": candidate_id})

        conn.close()
        return build_response(400, {"error": "Invalid request"})

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return build_response(500, {"error": str(e)})
