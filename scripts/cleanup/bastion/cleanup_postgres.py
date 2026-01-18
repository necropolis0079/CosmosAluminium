#!/usr/bin/env python3
"""
PostgreSQL Cleanup Script for Bastion Host.

Cleans candidate records from PostgreSQL database.
Run this script on the bastion host (inside VPC).

Usage:
    # Count candidates
    python3 cleanup_postgres.py --count

    # Dry run (show what would be deleted)
    python3 cleanup_postgres.py --dry-run

    # Delete specific candidate
    python3 cleanup_postgres.py --candidate-id <UUID>

    # Delete ALL candidates
    python3 cleanup_postgres.py --all

Prerequisites:
    pip3 install --user pg8000 boto3
"""

import argparse
import json
import logging
import sys

import boto3
import pg8000

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
AWS_REGION = "eu-north-1"
DB_SECRET_ARN = "arn:aws:secretsmanager:eu-north-1:132934401449:secret:lcmgo-cagenai-prod-db-credentials"


def get_db_connection():
    """Get PostgreSQL connection using Secrets Manager credentials."""
    secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)
    secret_response = secrets_client.get_secret_value(SecretId=DB_SECRET_ARN)
    credentials = json.loads(secret_response["SecretString"])

    return pg8000.connect(
        host=credentials["host"],
        port=int(credentials.get("port", 5432)),
        database=credentials.get("dbname", "cagenai"),
        user=credentials["username"],
        password=credentials["password"],
        ssl_context=True,
    )


def count_candidates(conn) -> int:
    """Count total candidates in database."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM candidates")
    count = cursor.fetchone()[0]
    cursor.close()
    return count


def list_candidates(conn, limit: int = 20) -> list:
    """List candidates in database."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id::text, first_name, last_name, email, created_at
        FROM candidates
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows


def delete_candidate(conn, candidate_id: str, dry_run: bool = True) -> bool:
    """Delete a specific candidate (CASCADE deletes related records)."""
    cursor = conn.cursor()

    # Check if exists
    cursor.execute("SELECT id, first_name, last_name FROM candidates WHERE id = %s", (candidate_id,))
    row = cursor.fetchone()

    if not row:
        logger.warning(f"Candidate not found: {candidate_id}")
        cursor.close()
        return False

    if dry_run:
        logger.info(f"[DRY RUN] Would delete candidate: {candidate_id} ({row[1]} {row[2]})")
    else:
        cursor.execute("DELETE FROM candidates WHERE id = %s RETURNING id", (candidate_id,))
        conn.commit()
        logger.info(f"Deleted candidate: {candidate_id} ({row[1]} {row[2]})")

    cursor.close()
    return True


def delete_all_candidates(conn, dry_run: bool = True) -> int:
    """Delete all candidates."""
    cursor = conn.cursor()

    # Get count first
    cursor.execute("SELECT COUNT(*) FROM candidates")
    count = cursor.fetchone()[0]

    if count == 0:
        logger.info("No candidates to delete")
        cursor.close()
        return 0

    if dry_run:
        logger.info(f"[DRY RUN] Would delete {count} candidates")
    else:
        cursor.execute("DELETE FROM candidates")
        conn.commit()
        logger.info(f"Deleted {count} candidates")

    cursor.close()
    return count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean PostgreSQL candidates (run on bastion)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--count", action="store_true", help="Count candidates")
    parser.add_argument("--list", action="store_true", help="List recent candidates")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    parser.add_argument("--candidate-id", type=str, help="Delete specific candidate")
    parser.add_argument("--all", action="store_true", help="Delete ALL candidates")

    args = parser.parse_args()

    if not any([args.count, args.list, args.dry_run, args.candidate_id, args.all]):
        parser.print_help()
        sys.exit(1)

    try:
        conn = get_db_connection()
        logger.info("Connected to PostgreSQL")

        if args.count:
            count = count_candidates(conn)
            print(f"\nTotal candidates: {count}")

        elif args.list:
            rows = list_candidates(conn)
            print(f"\nRecent candidates ({len(rows)}):")
            print("-" * 80)
            for row in rows:
                print(f"  {row[0]} | {row[1]} {row[2]} | {row[3]} | {row[4]}")
            print("-" * 80)
            count = count_candidates(conn)
            print(f"Total: {count}")

        elif args.candidate_id:
            delete_candidate(conn, args.candidate_id, dry_run=args.dry_run)

        elif args.all:
            if not args.dry_run:
                print("\n" + "!" * 60)
                print("WARNING: This will DELETE ALL candidates!")
                print("!" * 60)
                response = input("\nType 'DELETE ALL' to confirm: ")
                if response != "DELETE ALL":
                    print("Aborted.")
                    sys.exit(0)

            deleted = delete_all_candidates(conn, dry_run=args.dry_run)
            print(f"\n{'Would delete' if args.dry_run else 'Deleted'}: {deleted} candidates")

        elif args.dry_run:
            # Just show count when dry-run without other options
            count = count_candidates(conn)
            print(f"\n[DRY RUN] Would delete {count} candidates")

        conn.close()

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
