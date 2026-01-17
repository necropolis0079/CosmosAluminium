#!/usr/bin/env python3
"""
CV Data Cleanup Script for LCMGoCloud-CAGenAI.

Removes CV processing data from all storage locations:
- S3: Upload and processed buckets
- DynamoDB: Processing state table
- PostgreSQL: Candidate records (CASCADE deletes related tables)
- OpenSearch: Search index documents

Usage:
    # Dry run (shows what would be deleted)
    python cleanup_cv_data.py --dry-run

    # Clean specific correlation_id
    python cleanup_cv_data.py --correlation-id <UUID>

    # Clean specific candidate
    python cleanup_cv_data.py --candidate-id <UUID>

    # Clean ALL test data (requires confirmation)
    python cleanup_cv_data.py --all

    # Find orphaned data
    python cleanup_cv_data.py --find-orphans

Environment Variables:
    AWS_REGION: AWS region (default: eu-north-1)
    DB_SECRET_ARN: Secrets Manager ARN for database credentials
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = os.environ.get("AWS_REGION", "eu-north-1")

# Resource names
CV_UPLOADS_BUCKET = "lcmgo-cagenai-prod-cv-uploads-eun1"
PROCESSED_BUCKET = "lcmgo-cagenai-prod-processed-eun1"
STATE_TABLE = "lcmgo-cagenai-prod-cv-processing-state"
OPENSEARCH_ENDPOINT = "vpc-lcmgo-cagenai-prod-search-zg67rx23eou363nwlybpkkmlea.eu-north-1.es.amazonaws.com"
OPENSEARCH_INDEX = "cosmos-hr-candidates"
DB_SECRET_ARN = os.environ.get(
    "DB_SECRET_ARN",
    "arn:aws:secretsmanager:eu-north-1:132934401449:secret:lcmgo-cagenai-prod-db-credentials",
)


@dataclass
class CleanupResult:
    """Result of cleanup operation."""

    s3_uploads_deleted: list[str] = field(default_factory=list)
    s3_processed_deleted: list[str] = field(default_factory=list)
    dynamodb_deleted: list[str] = field(default_factory=list)
    postgresql_deleted: list[str] = field(default_factory=list)
    opensearch_deleted: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "s3_uploads_deleted": self.s3_uploads_deleted,
            "s3_processed_deleted": self.s3_processed_deleted,
            "dynamodb_deleted": self.dynamodb_deleted,
            "postgresql_deleted": self.postgresql_deleted,
            "opensearch_deleted": self.opensearch_deleted,
            "errors": self.errors,
            "total_deleted": (
                len(self.s3_uploads_deleted)
                + len(self.s3_processed_deleted)
                + len(self.dynamodb_deleted)
                + len(self.postgresql_deleted)
                + len(self.opensearch_deleted)
            ),
        }

    def print_summary(self):
        """Print cleanup summary."""
        print("\n" + "=" * 60)
        print("CLEANUP SUMMARY")
        print("=" * 60)
        print(f"S3 Uploads deleted:    {len(self.s3_uploads_deleted)}")
        print(f"S3 Processed deleted:  {len(self.s3_processed_deleted)}")
        print(f"DynamoDB deleted:      {len(self.dynamodb_deleted)}")
        print(f"PostgreSQL deleted:    {len(self.postgresql_deleted)}")
        print(f"OpenSearch deleted:    {len(self.opensearch_deleted)}")
        print("-" * 60)
        print(f"Total items deleted:   {self.to_dict()['total_deleted']}")
        if self.errors:
            print(f"Errors encountered:    {len(self.errors)}")
            for error in self.errors:
                print(f"  - {error}")
        print("=" * 60)


@dataclass
class OrphanReport:
    """Report of orphaned data."""

    dynamodb_without_postgres: list[dict] = field(default_factory=list)
    s3_without_dynamodb: list[str] = field(default_factory=list)
    opensearch_without_postgres: list[str] = field(default_factory=list)
    postgres_without_opensearch: list[str] = field(default_factory=list)

    def print_report(self):
        """Print orphan report."""
        print("\n" + "=" * 60)
        print("ORPHAN DATA REPORT")
        print("=" * 60)

        print(f"\nDynamoDB entries without PostgreSQL candidate: {len(self.dynamodb_without_postgres)}")
        for item in self.dynamodb_without_postgres[:10]:
            print(f"  - correlation_id: {item.get('correlation_id')}, status: {item.get('status')}")
        if len(self.dynamodb_without_postgres) > 10:
            print(f"  ... and {len(self.dynamodb_without_postgres) - 10} more")

        print(f"\nS3 files without DynamoDB state: {len(self.s3_without_dynamodb)}")
        for key in self.s3_without_dynamodb[:10]:
            print(f"  - {key}")
        if len(self.s3_without_dynamodb) > 10:
            print(f"  ... and {len(self.s3_without_dynamodb) - 10} more")

        print(f"\nOpenSearch docs without PostgreSQL: {len(self.opensearch_without_postgres)}")
        for doc_id in self.opensearch_without_postgres[:10]:
            print(f"  - {doc_id}")
        if len(self.opensearch_without_postgres) > 10:
            print(f"  ... and {len(self.opensearch_without_postgres) - 10} more")

        print(f"\nPostgreSQL candidates without OpenSearch: {len(self.postgres_without_opensearch)}")
        for cand_id in self.postgres_without_opensearch[:10]:
            print(f"  - {cand_id}")
        if len(self.postgres_without_opensearch) > 10:
            print(f"  ... and {len(self.postgres_without_opensearch) - 10} more")

        print("=" * 60)


class CVDataCleaner:
    """
    Cleans CV processing data from all storage locations.

    Supports:
    - Cleanup by correlation_id
    - Cleanup by candidate_id
    - Full cleanup (all data)
    - Orphan detection
    - Dry-run mode
    """

    def __init__(self, dry_run: bool = True):
        """
        Initialize cleaner.

        Args:
            dry_run: If True, only report what would be deleted
        """
        self.dry_run = dry_run
        self.s3 = boto3.client("s3", region_name=AWS_REGION)
        self.dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        self.secrets = boto3.client("secretsmanager", region_name=AWS_REGION)
        self._db_connection = None

        if dry_run:
            logger.info("DRY RUN MODE - No data will be deleted")

    def _get_db_connection(self):
        """Get PostgreSQL connection."""
        if self._db_connection is not None:
            return self._db_connection

        try:
            import pg8000

            secret_response = self.secrets.get_secret_value(SecretId=DB_SECRET_ARN)
            credentials = json.loads(secret_response["SecretString"])

            self._db_connection = pg8000.connect(
                host=credentials["host"],
                port=int(credentials.get("port", 5432)),
                database=credentials.get("dbname", "cagenai"),
                user=credentials["username"],
                password=credentials["password"],
                ssl_context=True,
            )
            return self._db_connection

        except ImportError:
            logger.warning("pg8000 not installed - PostgreSQL cleanup unavailable")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return None

    def _get_opensearch_client(self):
        """Get OpenSearch client with AWS auth."""
        try:
            from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection

            credentials = boto3.Session().get_credentials()
            auth = AWSV4SignerAuth(credentials, AWS_REGION, "es")

            return OpenSearch(
                hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
                http_auth=auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
            )
        except ImportError:
            logger.warning("opensearch-py not installed - OpenSearch cleanup unavailable")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to OpenSearch: {e}")
            return None

    def cleanup_by_correlation_id(self, correlation_id: str) -> CleanupResult:
        """
        Clean all data for a specific correlation_id.

        Args:
            correlation_id: The correlation_id to clean

        Returns:
            CleanupResult with details
        """
        result = CleanupResult()
        logger.info(f"Cleaning data for correlation_id: {correlation_id}")

        # 1. Get candidate_id from DynamoDB (if exists)
        candidate_id = self._get_candidate_id_from_dynamodb(correlation_id)

        # 2. Clean S3 processed files
        self._clean_s3_processed(correlation_id, result)

        # 3. Clean DynamoDB state
        self._clean_dynamodb(correlation_id, result)

        # 4. Clean PostgreSQL and OpenSearch (if we have candidate_id)
        if candidate_id:
            self._clean_postgresql(candidate_id, result)
            self._clean_opensearch(candidate_id, result)

        return result

    def cleanup_by_candidate_id(self, candidate_id: str) -> CleanupResult:
        """
        Clean all data for a specific candidate_id.

        Args:
            candidate_id: The candidate_id to clean

        Returns:
            CleanupResult with details
        """
        result = CleanupResult()
        logger.info(f"Cleaning data for candidate_id: {candidate_id}")

        # 1. Find correlation_ids from DynamoDB
        correlation_ids = self._find_correlation_ids_for_candidate(candidate_id)

        # 2. Clean S3 and DynamoDB for each correlation_id
        for corr_id in correlation_ids:
            self._clean_s3_processed(corr_id, result)
            self._clean_dynamodb(corr_id, result)

        # 3. Clean PostgreSQL
        self._clean_postgresql(candidate_id, result)

        # 4. Clean OpenSearch
        self._clean_opensearch(candidate_id, result)

        return result

    def cleanup_all(self, confirm: bool = False) -> CleanupResult:
        """
        Clean ALL CV processing data.

        Args:
            confirm: Must be True to proceed

        Returns:
            CleanupResult with details
        """
        if not confirm and not self.dry_run:
            raise ValueError("Must pass confirm=True to delete all data")

        result = CleanupResult()
        logger.warning("CLEANING ALL CV PROCESSING DATA")

        # 1. Get all correlation_ids from DynamoDB
        correlation_ids = self._list_all_correlation_ids()
        logger.info(f"Found {len(correlation_ids)} correlation_ids in DynamoDB")

        # 2. Get all candidate_ids from PostgreSQL
        candidate_ids = self._list_all_candidate_ids()
        logger.info(f"Found {len(candidate_ids)} candidates in PostgreSQL")

        # 3. Clean S3 uploads (all files in uploads/ prefix)
        self._clean_s3_uploads_all(result)

        # 4. Clean S3 processed (all files)
        self._clean_s3_processed_all(result)

        # 5. Clean all DynamoDB entries
        for corr_id in correlation_ids:
            self._clean_dynamodb(corr_id, result)

        # 6. Clean all PostgreSQL candidates
        for cand_id in candidate_ids:
            self._clean_postgresql(cand_id, result)

        # 7. Clean all OpenSearch documents
        self._clean_opensearch_all(result)

        return result

    def find_orphans(self) -> OrphanReport:
        """
        Find orphaned data across all storage locations.

        Returns:
            OrphanReport with findings
        """
        report = OrphanReport()
        logger.info("Scanning for orphaned data...")

        # Get all IDs from each system
        dynamodb_entries = self._list_all_dynamodb_entries()
        postgres_candidates = set(self._list_all_candidate_ids())
        opensearch_candidates = set(self._list_all_opensearch_ids())
        s3_correlation_ids = self._list_s3_correlation_ids()

        # 1. DynamoDB entries with candidate_id not in PostgreSQL
        for entry in dynamodb_entries:
            candidate_id = entry.get("candidate_id")
            if candidate_id and candidate_id not in postgres_candidates:
                report.dynamodb_without_postgres.append(entry)

        # 2. S3 files without DynamoDB state
        dynamodb_correlation_ids = {e.get("correlation_id") for e in dynamodb_entries}
        for corr_id in s3_correlation_ids:
            if corr_id not in dynamodb_correlation_ids:
                report.s3_without_dynamodb.append(corr_id)

        # 3. OpenSearch documents without PostgreSQL
        for os_id in opensearch_candidates:
            if os_id not in postgres_candidates:
                report.opensearch_without_postgres.append(os_id)

        # 4. PostgreSQL candidates without OpenSearch
        for pg_id in postgres_candidates:
            if pg_id not in opensearch_candidates:
                report.postgres_without_opensearch.append(pg_id)

        return report

    def _get_candidate_id_from_dynamodb(self, correlation_id: str) -> str | None:
        """Get candidate_id from DynamoDB state."""
        try:
            table = self.dynamodb.Table(STATE_TABLE)
            response = table.get_item(Key={"correlation_id": correlation_id})
            item = response.get("Item", {})
            return item.get("candidate_id")
        except Exception as e:
            logger.warning(f"Failed to get candidate_id from DynamoDB: {e}")
            return None

    def _find_correlation_ids_for_candidate(self, candidate_id: str) -> list[str]:
        """Find all correlation_ids for a candidate."""
        correlation_ids = []
        try:
            table = self.dynamodb.Table(STATE_TABLE)
            # Scan with filter (not ideal but DynamoDB doesn't have index on candidate_id)
            response = table.scan(
                FilterExpression="candidate_id = :cid",
                ExpressionAttributeValues={":cid": candidate_id},
            )
            correlation_ids = [item["correlation_id"] for item in response.get("Items", [])]
        except Exception as e:
            logger.warning(f"Failed to find correlation_ids: {e}")
        return correlation_ids

    def _clean_s3_processed(self, correlation_id: str, result: CleanupResult):
        """Clean S3 processed files for correlation_id."""
        prefixes = [
            f"extracted/{correlation_id}.txt",
            f"metadata/{correlation_id}.json",
            f"parsed/{correlation_id}.json",
        ]

        for key in prefixes:
            try:
                # Check if exists
                self.s3.head_object(Bucket=PROCESSED_BUCKET, Key=key)

                if self.dry_run:
                    logger.info(f"[DRY RUN] Would delete s3://{PROCESSED_BUCKET}/{key}")
                else:
                    self.s3.delete_object(Bucket=PROCESSED_BUCKET, Key=key)
                    logger.info(f"Deleted s3://{PROCESSED_BUCKET}/{key}")

                result.s3_processed_deleted.append(key)

            except ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    result.errors.append(f"S3 error for {key}: {e}")

    def _clean_s3_uploads_all(self, result: CleanupResult):
        """Clean all files in S3 uploads bucket."""
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=CV_UPLOADS_BUCKET, Prefix="uploads/"):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if self.dry_run:
                        logger.info(f"[DRY RUN] Would delete s3://{CV_UPLOADS_BUCKET}/{key}")
                    else:
                        self.s3.delete_object(Bucket=CV_UPLOADS_BUCKET, Key=key)
                        logger.info(f"Deleted s3://{CV_UPLOADS_BUCKET}/{key}")
                    result.s3_uploads_deleted.append(key)
        except Exception as e:
            result.errors.append(f"S3 uploads cleanup error: {e}")

    def _clean_s3_processed_all(self, result: CleanupResult):
        """Clean all files in S3 processed bucket."""
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            for prefix in ["extracted/", "metadata/", "parsed/"]:
                for page in paginator.paginate(Bucket=PROCESSED_BUCKET, Prefix=prefix):
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        if self.dry_run:
                            logger.info(f"[DRY RUN] Would delete s3://{PROCESSED_BUCKET}/{key}")
                        else:
                            self.s3.delete_object(Bucket=PROCESSED_BUCKET, Key=key)
                            logger.info(f"Deleted s3://{PROCESSED_BUCKET}/{key}")
                        result.s3_processed_deleted.append(key)
        except Exception as e:
            result.errors.append(f"S3 processed cleanup error: {e}")

    def _clean_dynamodb(self, correlation_id: str, result: CleanupResult):
        """Clean DynamoDB state entry."""
        try:
            table = self.dynamodb.Table(STATE_TABLE)

            if self.dry_run:
                logger.info(f"[DRY RUN] Would delete DynamoDB item: {correlation_id}")
            else:
                table.delete_item(Key={"correlation_id": correlation_id})
                logger.info(f"Deleted DynamoDB item: {correlation_id}")

            result.dynamodb_deleted.append(correlation_id)

        except Exception as e:
            result.errors.append(f"DynamoDB error for {correlation_id}: {e}")

    def _clean_postgresql(self, candidate_id: str, result: CleanupResult):
        """Clean PostgreSQL candidate (CASCADE deletes related records)."""
        conn = self._get_db_connection()
        if not conn:
            result.errors.append("PostgreSQL connection unavailable")
            return

        try:
            cursor = conn.cursor()

            if self.dry_run:
                # Check if exists
                cursor.execute("SELECT id FROM candidates WHERE id = %s", (candidate_id,))
                if cursor.fetchone():
                    logger.info(f"[DRY RUN] Would delete PostgreSQL candidate: {candidate_id}")
                    result.postgresql_deleted.append(candidate_id)
            else:
                cursor.execute("DELETE FROM candidates WHERE id = %s RETURNING id", (candidate_id,))
                deleted = cursor.fetchone()
                conn.commit()

                if deleted:
                    logger.info(f"Deleted PostgreSQL candidate: {candidate_id}")
                    result.postgresql_deleted.append(candidate_id)

            cursor.close()

        except Exception as e:
            conn.rollback()
            result.errors.append(f"PostgreSQL error for {candidate_id}: {e}")

    def _clean_opensearch(self, candidate_id: str, result: CleanupResult):
        """Clean OpenSearch document."""
        client = self._get_opensearch_client()
        if not client:
            result.errors.append("OpenSearch connection unavailable")
            return

        try:
            if self.dry_run:
                # Check if exists
                if client.exists(index=OPENSEARCH_INDEX, id=candidate_id):
                    logger.info(f"[DRY RUN] Would delete OpenSearch doc: {candidate_id}")
                    result.opensearch_deleted.append(candidate_id)
            else:
                response = client.delete(
                    index=OPENSEARCH_INDEX,
                    id=candidate_id,
                    ignore=[404],
                )
                if response.get("result") == "deleted":
                    logger.info(f"Deleted OpenSearch doc: {candidate_id}")
                    result.opensearch_deleted.append(candidate_id)

        except Exception as e:
            result.errors.append(f"OpenSearch error for {candidate_id}: {e}")

    def _clean_opensearch_all(self, result: CleanupResult):
        """Clean all documents from OpenSearch index."""
        client = self._get_opensearch_client()
        if not client:
            result.errors.append("OpenSearch connection unavailable")
            return

        try:
            if self.dry_run:
                # Count documents
                count = client.count(index=OPENSEARCH_INDEX)["count"]
                logger.info(f"[DRY RUN] Would delete {count} OpenSearch documents")
                result.opensearch_deleted.append(f"[{count} documents]")
            else:
                # Delete by query (all documents)
                response = client.delete_by_query(
                    index=OPENSEARCH_INDEX,
                    body={"query": {"match_all": {}}},
                )
                deleted = response.get("deleted", 0)
                logger.info(f"Deleted {deleted} OpenSearch documents")
                result.opensearch_deleted.append(f"[{deleted} documents]")

        except Exception as e:
            result.errors.append(f"OpenSearch cleanup error: {e}")

    def _list_all_correlation_ids(self) -> list[str]:
        """List all correlation_ids from DynamoDB."""
        correlation_ids = []
        try:
            table = self.dynamodb.Table(STATE_TABLE)
            response = table.scan(ProjectionExpression="correlation_id")
            correlation_ids = [item["correlation_id"] for item in response.get("Items", [])]

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(
                    ProjectionExpression="correlation_id",
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                correlation_ids.extend([item["correlation_id"] for item in response.get("Items", [])])

        except Exception as e:
            logger.error(f"Failed to list correlation_ids: {e}")
        return correlation_ids

    def _list_all_dynamodb_entries(self) -> list[dict]:
        """List all DynamoDB entries with details."""
        entries = []
        try:
            table = self.dynamodb.Table(STATE_TABLE)
            response = table.scan()
            entries = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                entries.extend(response.get("Items", []))

        except Exception as e:
            logger.error(f"Failed to list DynamoDB entries: {e}")
        return entries

    def _list_all_candidate_ids(self) -> list[str]:
        """List all candidate_ids from PostgreSQL."""
        candidate_ids = []
        conn = self._get_db_connection()
        if not conn:
            return candidate_ids

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id::text FROM candidates")
            candidate_ids = [row[0] for row in cursor.fetchall()]
            cursor.close()
        except Exception as e:
            logger.error(f"Failed to list candidate_ids: {e}")
        return candidate_ids

    def _list_all_opensearch_ids(self) -> list[str]:
        """List all document IDs from OpenSearch."""
        doc_ids = []
        client = self._get_opensearch_client()
        if not client:
            return doc_ids

        try:
            response = client.search(
                index=OPENSEARCH_INDEX,
                body={
                    "query": {"match_all": {}},
                    "_source": False,
                    "size": 10000,
                },
            )
            doc_ids = [hit["_id"] for hit in response["hits"]["hits"]]
        except Exception as e:
            logger.error(f"Failed to list OpenSearch IDs: {e}")
        return doc_ids

    def _list_s3_correlation_ids(self) -> set[str]:
        """List correlation_ids from S3 processed bucket."""
        correlation_ids = set()
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=PROCESSED_BUCKET, Prefix="parsed/"):
                for obj in page.get("Contents", []):
                    # Extract correlation_id from parsed/{correlation_id}.json
                    key = obj["Key"]
                    if key.endswith(".json"):
                        corr_id = key.replace("parsed/", "").replace(".json", "")
                        correlation_ids.add(corr_id)
        except Exception as e:
            logger.error(f"Failed to list S3 correlation_ids: {e}")
        return correlation_ids

    def close(self):
        """Close connections."""
        if self._db_connection:
            try:
                self._db_connection.close()
            except Exception:
                pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean CV processing data from all storage locations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry run to see what would be deleted
    python cleanup_cv_data.py --dry-run

    # Clean specific correlation_id
    python cleanup_cv_data.py --correlation-id a1b2c3d4-e5f6-7890-abcd-ef1234567890

    # Clean specific candidate
    python cleanup_cv_data.py --candidate-id a1b2c3d4-e5f6-7890-abcd-ef1234567890

    # Find orphaned data
    python cleanup_cv_data.py --find-orphans

    # Clean ALL data (DANGEROUS!)
    python cleanup_cv_data.py --all --confirm
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show what would be deleted, don't actually delete",
    )
    parser.add_argument(
        "--correlation-id",
        type=str,
        help="Clean data for specific correlation_id",
    )
    parser.add_argument(
        "--candidate-id",
        type=str,
        help="Clean data for specific candidate_id",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Clean ALL CV processing data (requires --confirm)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm destructive operations",
    )
    parser.add_argument(
        "--find-orphans",
        action="store_true",
        help="Find orphaned data across storage locations",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        help="Output results to JSON file",
    )

    args = parser.parse_args()

    # Validate arguments
    if not any([args.correlation_id, args.candidate_id, args.all, args.find_orphans, args.dry_run]):
        parser.print_help()
        sys.exit(1)

    # Create cleaner
    cleaner = CVDataCleaner(dry_run=args.dry_run)

    try:
        result = None

        if args.find_orphans:
            report = cleaner.find_orphans()
            report.print_report()

            if args.output_json:
                with open(args.output_json, "w") as f:
                    json.dump(
                        {
                            "dynamodb_without_postgres": report.dynamodb_without_postgres,
                            "s3_without_dynamodb": list(report.s3_without_dynamodb),
                            "opensearch_without_postgres": report.opensearch_without_postgres,
                            "postgres_without_opensearch": report.postgres_without_opensearch,
                        },
                        f,
                        indent=2,
                    )
            return

        elif args.correlation_id:
            result = cleaner.cleanup_by_correlation_id(args.correlation_id)

        elif args.candidate_id:
            result = cleaner.cleanup_by_candidate_id(args.candidate_id)

        elif args.all:
            if not args.confirm and not args.dry_run:
                print("ERROR: --all requires --confirm flag to proceed")
                print("Use --dry-run to preview what would be deleted")
                sys.exit(1)

            # Double confirmation for non-dry-run
            if not args.dry_run:
                print("\n" + "!" * 60)
                print("WARNING: This will DELETE ALL CV processing data!")
                print("!" * 60)
                response = input("\nType 'DELETE ALL' to confirm: ")
                if response != "DELETE ALL":
                    print("Aborted.")
                    sys.exit(0)

            result = cleaner.cleanup_all(confirm=True)

        if result:
            result.print_summary()

            if args.output_json:
                with open(args.output_json, "w") as f:
                    json.dump(result.to_dict(), f, indent=2)
                print(f"\nResults saved to: {args.output_json}")

    finally:
        cleaner.close()


if __name__ == "__main__":
    main()
