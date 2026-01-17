"""
LCMGoCloud-CAGenAI - Database Initialization Lambda

This Lambda function initializes the PostgreSQL database schema by executing
SQL scripts in order. It retrieves database credentials from AWS Secrets Manager.

Uses pg8000 (pure Python PostgreSQL driver) - no binary dependencies required.

Environment Variables:
    - DB_SECRET_ARN: ARN of the Secrets Manager secret containing DB credentials
    - DB_HOST: RDS endpoint (optional if using secret)
    - DB_NAME: Database name (default: cagenai)
"""

import json
import logging
import os
from pathlib import Path

import boto3
import pg8000.native

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# SQL files to execute in order
SQL_FILES = [
    "001_extensions.sql",
    "002_enum_types.sql",
    "003_core_tables.sql",
    "004_taxonomy_tables.sql",
    "005_candidate_detail_tables.sql",
    "006_job_tables.sql",
    "007_matching_tables.sql",
    "008_search_system_tables.sql",
    "009_gdpr_tables.sql",
    "010_functions.sql",
    "011_triggers.sql",
    "012_views.sql",
    "013_initial_data.sql",
]


def get_db_credentials():
    """Retrieve database credentials from Secrets Manager."""
    secret_arn = os.environ.get("DB_SECRET_ARN")

    if not secret_arn:
        # Fallback to environment variables for local testing
        return {
            "host": os.environ.get("DB_HOST"),
            "port": int(os.environ.get("DB_PORT", 5432)),
            "dbname": os.environ.get("DB_NAME", "cagenai"),
            "username": os.environ.get("DB_USERNAME"),
            "password": os.environ.get("DB_PASSWORD"),
        }

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])

    return {
        "host": secret["host"],
        "port": int(secret.get("port", 5432)),
        "dbname": secret.get("dbname", os.environ.get("DB_NAME", "cagenai")),
        "username": secret["username"],
        "password": secret["password"],
    }


def get_connection(credentials):
    """Create a database connection using pg8000."""
    return pg8000.native.Connection(
        host=credentials["host"],
        port=credentials["port"],
        database=credentials["dbname"],
        user=credentials["username"],
        password=credentials["password"],
        timeout=30,
    )


def execute_sql_file(conn, sql_content, filename):
    """Execute a SQL file content."""
    logger.info(f"Executing {filename}...")

    try:
        # pg8000 native connection executes directly
        # Split by semicolons but handle multi-statement carefully
        conn.run(sql_content)
        logger.info(f"Successfully executed {filename}")
        return True, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error executing {filename}: {error_msg}")
        return False, error_msg


def check_schema_exists(conn):
    """Check if schema has already been initialized."""
    result = conn.run("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'candidates'
        );
    """)
    return result[0][0] if result else False


def get_schema_version(conn):
    """Get current schema version if available."""
    try:
        result = conn.run("""
            SELECT value FROM system_config WHERE key = 'schema_version';
        """)
        if result and result[0]:
            return json.loads(result[0][0])
        return None
    except Exception:
        return None


def cleanup_schema(conn):
    """Drop all schema objects to start fresh."""
    logger.info("Cleaning up existing schema...")

    # Drop all tables, views, types, and user-defined functions (not extension functions)
    cleanup_sql = """
    -- Drop all views
    DO $$ DECLARE
        r RECORD;
    BEGIN
        FOR r IN (SELECT viewname FROM pg_views WHERE schemaname = 'public') LOOP
            EXECUTE 'DROP VIEW IF EXISTS public.' || quote_ident(r.viewname) || ' CASCADE';
        END LOOP;
    END $$;

    -- Drop all tables
    DO $$ DECLARE
        r RECORD;
    BEGIN
        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
            EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
        END LOOP;
    END $$;

    -- Drop all enum types
    DO $$ DECLARE
        r RECORD;
    BEGIN
        FOR r IN (SELECT typname FROM pg_type t
                  JOIN pg_namespace n ON t.typnamespace = n.oid
                  WHERE n.nspname = 'public' AND t.typtype = 'e') LOOP
            EXECUTE 'DROP TYPE IF EXISTS public.' || quote_ident(r.typname) || ' CASCADE';
        END LOOP;
    END $$;

    -- Drop user-defined functions (exclude extension functions)
    DO $$ DECLARE
        r RECORD;
    BEGIN
        FOR r IN (
            SELECT p.proname, pg_get_function_identity_arguments(p.oid) as args
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            LEFT JOIN pg_depend d ON d.objid = p.oid AND d.deptype = 'e'
            WHERE n.nspname = 'public'
            AND d.objid IS NULL  -- Not part of an extension
        ) LOOP
            BEGIN
                EXECUTE 'DROP FUNCTION IF EXISTS public.' || quote_ident(r.proname) || '(' || r.args || ') CASCADE';
            EXCEPTION WHEN OTHERS THEN
                -- Ignore errors for functions that can't be dropped
                NULL;
            END;
        END LOOP;
    END $$;
    """

    try:
        conn.run(cleanup_sql)
        logger.info("Schema cleanup completed")
        return True, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error during cleanup: {error_msg}")
        return False, error_msg


def handler(event, context):
    """
    Lambda handler for database initialization.

    Event parameters:
        - force: bool - Force re-initialization even if schema exists
        - clean: bool - Drop all objects before creating (implies force)
        - sql_dir: str - Directory containing SQL files (for testing)
    """
    force = event.get("force", False)
    clean = event.get("clean", False)
    sql_dir = event.get("sql_dir", "/var/task/sql")

    # Clean implies force
    if clean:
        force = True

    results = {
        "success": True,
        "files_executed": [],
        "files_failed": [],
        "errors": [],
        "schema_version": None,
        "cleaned": False,
    }

    try:
        # Get database credentials
        logger.info("Retrieving database credentials...")
        credentials = get_db_credentials()

        # Connect to database
        logger.info(f"Connecting to database at {credentials['host']}...")
        conn = get_connection(credentials)

        # Clean existing schema if requested
        if clean:
            success, error = cleanup_schema(conn)
            if not success:
                results["success"] = False
                results["errors"].append(f"Cleanup failed: {error}")
                conn.close()
                return results
            results["cleaned"] = True

        # Check if schema already exists
        if check_schema_exists(conn):
            version = get_schema_version(conn)
            if not force:
                logger.info(f"Schema already exists (version: {version}). Use force=true to re-initialize.")
                results["schema_version"] = version
                results["message"] = "Schema already initialized. Use force=true or clean=true to re-initialize."
                conn.close()
                return results
            else:
                logger.warning("Force flag set - proceeding with re-initialization")

        # Execute SQL files in order
        for sql_file in SQL_FILES:
            sql_path = Path(sql_dir) / sql_file

            if not sql_path.exists():
                error_msg = f"SQL file not found: {sql_path}"
                logger.error(error_msg)
                results["files_failed"].append(sql_file)
                results["errors"].append(error_msg)
                results["success"] = False
                continue

            sql_content = sql_path.read_text(encoding="utf-8")
            success, error = execute_sql_file(conn, sql_content, sql_file)

            if success:
                results["files_executed"].append(sql_file)
            else:
                results["files_failed"].append(sql_file)
                results["errors"].append(f"{sql_file}: {error}")
                results["success"] = False
                # Stop on first error
                break

        # Get final schema version
        if results["success"]:
            results["schema_version"] = get_schema_version(conn)

        conn.close()

    except Exception as e:
        logger.exception("Fatal error during initialization")
        results["success"] = False
        results["errors"].append(str(e))

    return results


# For local testing
if __name__ == "__main__":
    import sys

    # Set environment variables for local testing
    os.environ["DB_HOST"] = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    os.environ["DB_PORT"] = sys.argv[2] if len(sys.argv) > 2 else "5432"
    os.environ["DB_NAME"] = sys.argv[3] if len(sys.argv) > 3 else "cagenai"
    os.environ["DB_USERNAME"] = sys.argv[4] if len(sys.argv) > 4 else "cagenai_admin"
    os.environ["DB_PASSWORD"] = sys.argv[5] if len(sys.argv) > 5 else "password"

    # Get SQL directory from script location
    script_dir = Path(__file__).parent.parent.parent / "scripts" / "sql"

    result = handler({"sql_dir": str(script_dir)}, None)
    print(json.dumps(result, indent=2))
