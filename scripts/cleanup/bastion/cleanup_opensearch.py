#!/usr/bin/env python3
"""
OpenSearch Cleanup Script for Bastion Host.

Cleans candidate documents from OpenSearch index.
Run this script on the bastion host (inside VPC).

Usage:
    # Count documents
    python3 cleanup_opensearch.py --count

    # Dry run (show what would be deleted)
    python3 cleanup_opensearch.py --dry-run

    # Delete specific document
    python3 cleanup_opensearch.py --candidate-id <UUID>

    # Delete ALL documents
    python3 cleanup_opensearch.py --all

Prerequisites:
    pip3 install --user opensearch-py requests-aws4auth boto3
"""

import argparse
import logging
import sys

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
AWS_REGION = "eu-north-1"
OPENSEARCH_ENDPOINT = "vpc-lcmgo-cagenai-prod-search-zg67rx23eou363nwlybpkkmlea.eu-north-1.es.amazonaws.com"
OPENSEARCH_INDEX = "cosmos-hr-candidates"


def get_opensearch_client():
    """Get OpenSearch client with AWS SigV4 authentication."""
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, AWS_REGION, "es")

    return OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def count_documents(client) -> int:
    """Count total documents in index."""
    try:
        response = client.count(index=OPENSEARCH_INDEX)
        return response["count"]
    except Exception as e:
        logger.error(f"Failed to count documents: {e}")
        return 0


def list_documents(client, limit: int = 20) -> list:
    """List documents in index."""
    try:
        response = client.search(
            index=OPENSEARCH_INDEX,
            body={
                "query": {"match_all": {}},
                "_source": ["first_name", "last_name", "email"],
                "size": limit,
                "sort": [{"_id": "asc"}],
            },
        )
        return response["hits"]["hits"]
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        return []


def delete_document(client, candidate_id: str, dry_run: bool = True) -> bool:
    """Delete a specific document."""
    try:
        # Check if exists
        if not client.exists(index=OPENSEARCH_INDEX, id=candidate_id):
            logger.warning(f"Document not found: {candidate_id}")
            return False

        if dry_run:
            # Get document details for logging
            doc = client.get(index=OPENSEARCH_INDEX, id=candidate_id, _source=["first_name", "last_name"])
            source = doc.get("_source", {})
            logger.info(f"[DRY RUN] Would delete: {candidate_id} ({source.get('first_name', '')} {source.get('last_name', '')})")
        else:
            response = client.delete(index=OPENSEARCH_INDEX, id=candidate_id)
            logger.info(f"Deleted document: {candidate_id} (result: {response.get('result')})")

        return True

    except Exception as e:
        logger.error(f"Failed to delete document {candidate_id}: {e}")
        return False


def delete_all_documents(client, dry_run: bool = True) -> int:
    """Delete all documents from index."""
    try:
        count = count_documents(client)

        if count == 0:
            logger.info("No documents to delete")
            return 0

        if dry_run:
            logger.info(f"[DRY RUN] Would delete {count} documents")
        else:
            response = client.delete_by_query(
                index=OPENSEARCH_INDEX,
                body={"query": {"match_all": {}}},
            )
            deleted = response.get("deleted", 0)
            logger.info(f"Deleted {deleted} documents")
            return deleted

        return count

    except Exception as e:
        logger.error(f"Failed to delete documents: {e}")
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean OpenSearch documents (run on bastion)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--count", action="store_true", help="Count documents")
    parser.add_argument("--list", action="store_true", help="List recent documents")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    parser.add_argument("--candidate-id", type=str, help="Delete specific document")
    parser.add_argument("--all", action="store_true", help="Delete ALL documents")

    args = parser.parse_args()

    if not any([args.count, args.list, args.dry_run, args.candidate_id, args.all]):
        parser.print_help()
        sys.exit(1)

    try:
        client = get_opensearch_client()
        logger.info("Connected to OpenSearch")

        if args.count:
            count = count_documents(client)
            print(f"\nTotal documents: {count}")

        elif args.list:
            docs = list_documents(client)
            print(f"\nDocuments ({len(docs)}):")
            print("-" * 80)
            for doc in docs:
                source = doc.get("_source", {})
                print(f"  {doc['_id']} | {source.get('first_name', '')} {source.get('last_name', '')} | {source.get('email', '')}")
            print("-" * 80)
            count = count_documents(client)
            print(f"Total: {count}")

        elif args.candidate_id:
            delete_document(client, args.candidate_id, dry_run=args.dry_run)

        elif args.all:
            if not args.dry_run:
                print("\n" + "!" * 60)
                print("WARNING: This will DELETE ALL documents from OpenSearch!")
                print("!" * 60)
                response = input("\nType 'DELETE ALL' to confirm: ")
                if response != "DELETE ALL":
                    print("Aborted.")
                    sys.exit(0)

            deleted = delete_all_documents(client, dry_run=args.dry_run)
            print(f"\n{'Would delete' if args.dry_run else 'Deleted'}: {deleted} documents")

        elif args.dry_run:
            # Just show count when dry-run without other options
            count = count_documents(client)
            print(f"\n[DRY RUN] Would delete {count} documents")

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
