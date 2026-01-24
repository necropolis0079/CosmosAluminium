"""
Database Writer for storing parsed CV data in PostgreSQL.

Writes parsed CV data to the PostgreSQL v4.0 schema, handling:
- Candidate creation/update
- Education, experience, skills, languages, certifications, licenses
- GDPR consent records
- Duplicate detection
- Post-write verification (Task 1.2)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

import boto3
import pg8000

from .quality_checker import QualityCheckResult
from .schema import CVCompletenessAudit, ParsedCV, ParsedTraining, ParsedUnmatchedData
from .taxonomy_mapper import normalize_text

logger = logging.getLogger(__name__)


# =============================================================================
# Data Sanitization Helpers
# =============================================================================

# Greek lookalike characters that cause email validation failures
GREEK_LOOKALIKES = {
    'Α': 'A', 'Β': 'B', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Ι': 'I',
    'Κ': 'K', 'Μ': 'M', 'Ν': 'N', 'Ο': 'O', 'Ρ': 'P', 'Τ': 'T',
    'Υ': 'Y', 'Χ': 'X',
    'α': 'a', 'ε': 'e', 'ι': 'i', 'κ': 'k', 'ν': 'n', 'ο': 'o',
    'ρ': 'p', 'τ': 't', 'υ': 'u', 'χ': 'x',
}


def _sanitize_string(value: str | None, max_length: int | None = None) -> str | None:
    """
    Sanitize a string value for database insertion.

    - Strips null bytes (0x00) that cause UTF-8 encoding errors
    - Optionally truncates to max_length

    Args:
        value: String to sanitize
        max_length: Maximum length (optional)

    Returns:
        Sanitized string or None
    """
    if value is None:
        return None

    # Strip null bytes
    value = value.replace('\x00', '')

    # Strip and normalize whitespace
    value = ' '.join(value.split())

    # Truncate if needed
    if max_length and len(value) > max_length:
        value = value[:max_length]

    return value if value else None


def _sanitize_email(email: str | None) -> str | None:
    """
    Sanitize email address for database insertion.

    Fixes common issues:
    - Greek lookalike characters (Μ→M, Ο→O, etc.)
    - Null bytes
    - Common typos (missing dots in domains)

    Args:
        email: Email to sanitize

    Returns:
        Sanitized email or None
    """
    if not email:
        return None

    # Strip null bytes and whitespace
    email = email.replace('\x00', '').strip()

    # Replace Greek lookalike characters
    for greek, latin in GREEK_LOOKALIKES.items():
        email = email.replace(greek, latin)

    # Common domain typo fixes (missing dots)
    domain_fixes = {
        '@gmailcom': '@gmail.com',
        '@yahoocom': '@yahoo.com',
        '@hotmailcom': '@hotmail.com',
        '@outlookcom': '@outlook.com',
        '@windowslivecom': '@windowslive.com',
        '@liveco': '@live.com',
    }
    email_lower = email.lower()
    for typo, fix in domain_fixes.items():
        if typo in email_lower:
            # Find the position and replace preserving case
            pos = email_lower.find(typo)
            email = email[:pos] + fix
            break

    return email if email else None


def _ensure_name(first_name: str | None, last_name: str | None, raw_text: str | None) -> tuple[str, str]:
    """
    Ensure first_name and last_name are not null.

    Falls back to extracting from raw_text or using "Unknown".

    Args:
        first_name: Parsed first name (may be None)
        last_name: Parsed last name (may be None)
        raw_text: Raw CV text for fallback extraction

    Returns:
        Tuple of (first_name, last_name), never None
    """
    # Sanitize existing names
    first_name = _sanitize_string(first_name, max_length=100)
    last_name = _sanitize_string(last_name, max_length=100)

    # If both are missing, try to extract from raw_text
    if not first_name and not last_name and raw_text:
        # Try to find a name pattern in first few lines
        lines = raw_text.strip().split('\n')[:5]
        for line in lines:
            words = line.strip().split()
            if 2 <= len(words) <= 4:
                # Could be a name - check if it's all letters
                if all(w.isalpha() for w in words):
                    first_name = words[0]
                    last_name = ' '.join(words[1:])
                    break

    # Final fallbacks
    if not first_name:
        first_name = "Unknown"
        logger.warning("Using fallback first_name='Unknown' - LLM failed to extract name")

    if not last_name:
        last_name = "Unknown"
        logger.warning("Using fallback last_name='Unknown' - LLM failed to extract name")

    return first_name, last_name


def _sanitize_json(obj: Any) -> Any:
    """
    Recursively sanitize JSON object, removing null bytes from all strings.

    PostgreSQL cannot store null bytes (0x00) in text/json fields.

    Args:
        obj: JSON object (dict, list, str, or primitive)

    Returns:
        Sanitized JSON object
    """
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_json(item) for item in obj]
    elif isinstance(obj, str):
        # Remove null bytes
        return obj.replace('\x00', '')
    else:
        return obj


@dataclass
class WriteVerification:
    """
    Result of post-write verification.

    Tracks expected vs actual record counts for each CV section,
    enabling detection of silent data loss during database writes.

    Task 1.2: Post-Write Verification
    """

    candidate_id: UUID
    success: bool = False

    # Expected vs actual counts
    education_expected: int = 0
    education_actual: int = 0
    experience_expected: int = 0
    experience_actual: int = 0
    skills_expected: int = 0
    skills_actual: int = 0
    skills_unmatched: int = 0
    languages_expected: int = 0
    languages_actual: int = 0
    certifications_expected: int = 0
    certifications_actual: int = 0
    certifications_unmatched: int = 0
    driving_licenses_expected: int = 0
    driving_licenses_actual: int = 0
    software_expected: int = 0
    software_actual: int = 0
    software_unmatched: int = 0

    # Error and warning details
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def coverage_score(self) -> float:
        """Calculate what percentage of expected records were written."""
        total_expected = (
            self.education_expected
            + self.experience_expected
            + self.skills_expected
            + self.languages_expected
            + self.certifications_expected
            + self.driving_licenses_expected
            + self.software_expected
        )
        total_actual = (
            self.education_actual
            + self.experience_actual
            + self.skills_actual
            + self.languages_actual
            + self.certifications_actual
            + self.driving_licenses_actual
            + self.software_actual
        )

        if total_expected == 0:
            return 1.0
        return total_actual / total_expected

    @property
    def total_unmatched(self) -> int:
        """Total count of unmatched taxonomy items."""
        return self.skills_unmatched + self.software_unmatched + self.certifications_unmatched

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "candidate_id": str(self.candidate_id),
            "success": self.success,
            "coverage_score": round(self.coverage_score, 4),
            "total_unmatched": self.total_unmatched,
            "education": {
                "expected": self.education_expected,
                "actual": self.education_actual,
            },
            "experience": {
                "expected": self.experience_expected,
                "actual": self.experience_actual,
            },
            "skills": {
                "expected": self.skills_expected,
                "actual": self.skills_actual,
                "unmatched": self.skills_unmatched,
            },
            "languages": {
                "expected": self.languages_expected,
                "actual": self.languages_actual,
            },
            "certifications": {
                "expected": self.certifications_expected,
                "actual": self.certifications_actual,
                "unmatched": self.certifications_unmatched,
            },
            "driving_licenses": {
                "expected": self.driving_licenses_expected,
                "actual": self.driving_licenses_actual,
            },
            "software": {
                "expected": self.software_expected,
                "actual": self.software_actual,
                "unmatched": self.software_unmatched,
            },
            "errors": self.errors,
            "warnings": self.warnings,
        }


class DatabaseWriter:
    """
    Writes parsed CV data to PostgreSQL database.

    Handles transactional writes across multiple tables:
    - candidates (main record)
    - candidate_education
    - candidate_experience
    - candidate_skills
    - candidate_languages
    - candidate_certifications
    - candidate_driving_licenses
    - candidate_software
    - consent_records

    Example:
        writer = DatabaseWriter(db_secret_arn="arn:aws:secretsmanager:...")
        candidate_id = await writer.write_candidate(parsed_cv, correlation_id)
    """

    def __init__(
        self,
        db_secret_arn: str | None = None,
        db_connection: Any | None = None,
        region: str = "eu-north-1",
    ):
        """
        Initialize database writer.

        Args:
            db_secret_arn: ARN of Secrets Manager secret with DB credentials
            db_connection: Existing database connection (for reuse)
            region: AWS region
        """
        self.db_secret_arn = db_secret_arn
        self._connection = db_connection
        self.region = region

    def _get_connection(self, force_new: bool = False) -> pg8000.Connection:
        """Get database connection.

        Args:
            force_new: If True, close existing connection and create a new one.
        """
        if force_new and self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

        if self._connection is not None:
            return self._connection

        if not self.db_secret_arn:
            raise ValueError("db_secret_arn required when no connection provided")

        # Get credentials from Secrets Manager
        secrets_client = boto3.client("secretsmanager", region_name=self.region)
        secret_response = secrets_client.get_secret_value(SecretId=self.db_secret_arn)
        credentials = json.loads(secret_response["SecretString"])

        self._connection = pg8000.connect(
            host=credentials["host"],
            port=int(credentials.get("port", 5432)),
            database=credentials.get("dbname", "cagenai"),
            user=credentials["username"],
            password=credentials["password"],
            ssl_context=True,
        )

        return self._connection

    def _ensure_clean_connection(self) -> pg8000.Connection:
        """Ensure connection is in a clean state, ready for new transaction.

        Tries to rollback any existing transaction. If that fails,
        creates a fresh connection.

        Returns:
            A connection in a clean transaction state.
        """
        conn = self._get_connection()

        try:
            # Try to rollback any existing transaction
            conn.rollback()

            # Verify connection is healthy with a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()

            return conn

        except Exception as e:
            # Connection is broken or in bad state - get a fresh one
            logger.warning(f"Connection in bad state, creating fresh connection: {e}")
            return self._get_connection(force_new=True)

    async def write_candidate(
        self,
        parsed_cv: ParsedCV,
        correlation_id: str,
        source_key: str | None = None,
        check_duplicates: bool = True,
        verify_write: bool = True,
        quality_result: QualityCheckResult | None = None,
    ) -> tuple[UUID, WriteVerification | None, CVCompletenessAudit | None]:
        """
        Write parsed CV data to database with post-write verification and completeness audit.

        Args:
            parsed_cv: Parsed CV data
            correlation_id: Processing correlation ID
            source_key: S3 key of source file
            check_duplicates: Whether to check for duplicate candidates
            verify_write: Whether to verify records after write (Task 1.2)
            quality_result: QualityCheckResult with warnings to store (Session 46)

        Returns:
            Tuple of (candidate_id, WriteVerification result or None, CVCompletenessAudit or None)

        Raises:
            Exception: On database errors
        """
        # ALWAYS use a fresh connection for write operations
        # This fixes "transaction is aborted" errors that occur when Lambda reuses
        # a warm container with a cached connection in a bad state
        conn = self._get_connection(force_new=True)
        logger.info(f"Using fresh database connection for write operation")

        cursor = conn.cursor()
        verification = None
        completeness_audit = None

        try:
            # pg8000 uses autocommit=False by default, so transactions are implicit
            # No explicit begin() needed - transaction starts with first statement

            # Check for duplicates
            logger.info("DB Step 1: Checking for duplicates")
            existing_id = None
            if check_duplicates:
                existing_id = self._find_duplicate(
                    cursor,
                    parsed_cv.personal.email,
                    parsed_cv.personal.phone,
                    parsed_cv.personal.first_name,
                    parsed_cv.personal.last_name,
                )
            logger.info(f"DB Step 1 complete: existing_id={existing_id}")

            if existing_id:
                logger.info(f"Found duplicate candidate: {existing_id}")
                candidate_id = existing_id
                self._update_candidate(cursor, candidate_id, parsed_cv)
            else:
                logger.info("DB Step 2: Inserting new candidate")
                candidate_id = self._insert_candidate(cursor, parsed_cv, correlation_id, source_key)
            logger.info(f"DB Step 2 complete: candidate_id={candidate_id}")

            # Insert related records - wrap each in try/except to identify exact failure point
            # pg8000 defers errors, so we check after each step

            try:
                logger.info("DB Step 3: Inserting education")
                self._insert_education(cursor, candidate_id, parsed_cv.education)
                cursor.execute("SELECT 1")  # Force error surface
                cursor.fetchone()
                logger.info("DB Step 3 complete")
            except Exception as e:
                logger.error(f"DB Step 3 FAILED (education): {e}")
                raise Exception(f"Failed inserting education: {e}")

            try:
                logger.info("DB Step 4: Inserting experience")
                self._insert_experience(cursor, candidate_id, parsed_cv.experience)
                cursor.execute("SELECT 1")  # Force error surface
                cursor.fetchone()
                logger.info("DB Step 4 complete")
            except Exception as e:
                logger.error(f"DB Step 4 FAILED (experience): {e}")
                raise Exception(f"Failed inserting experience: {e}")

            # Insert skills, software, certifications - capturing unmatched items
            try:
                logger.info("DB Step 5: Inserting skills")
                skill_stats = self._insert_skills(cursor, candidate_id, parsed_cv.skills, correlation_id)
                cursor.execute("SELECT 1")  # Force error surface
                cursor.fetchone()
                logger.info(f"DB Step 5 complete: {skill_stats}")
            except Exception as e:
                logger.error(f"DB Step 5 FAILED (skills): {e}")
                raise Exception(f"Failed inserting skills: {e}")

            try:
                logger.info("DB Step 6: Inserting languages")
                self._insert_languages(cursor, candidate_id, parsed_cv.languages)
                cursor.execute("SELECT 1")  # Force error surface
                cursor.fetchone()
                logger.info("DB Step 6 complete")
            except Exception as e:
                logger.error(f"DB Step 6 FAILED (languages): {e}")
                raise Exception(f"Failed inserting languages: {e}")

            try:
                logger.info("DB Step 7: Inserting certifications")
                cert_stats = self._insert_certifications(cursor, candidate_id, parsed_cv.certifications, correlation_id)
                cursor.execute("SELECT 1")  # Force error surface
                cursor.fetchone()
                logger.info(f"DB Step 7 complete: {cert_stats}")
            except Exception as e:
                logger.error(f"DB Step 7 FAILED (certifications): {e}")
                raise Exception(f"Failed inserting certifications: {e}")

            try:
                logger.info("DB Step 8: Inserting driving licenses")
                self._insert_driving_licenses(cursor, candidate_id, parsed_cv.driving_licenses)
                cursor.execute("SELECT 1")  # Force error surface
                cursor.fetchone()
                logger.info("DB Step 8 complete")
            except Exception as e:
                logger.error(f"DB Step 8 FAILED (driving_licenses): {e}")
                raise Exception(f"Failed inserting driving licenses: {e}")

            try:
                logger.info("DB Step 9: Inserting software")
                software_stats = self._insert_software(cursor, candidate_id, parsed_cv.software, correlation_id)
                cursor.execute("SELECT 1")  # Force error surface
                cursor.fetchone()
                logger.info(f"DB Step 9 complete: {software_stats}")
            except Exception as e:
                logger.error(f"DB Step 9 FAILED (software): {e}")
                raise Exception(f"Failed inserting software: {e}")

            try:
                logger.info("DB Step 10: Inserting training")
                self._insert_training(cursor, candidate_id, parsed_cv.training)
                cursor.execute("SELECT 1")  # Force error surface
                cursor.fetchone()
                logger.info("DB Step 10 complete")
            except Exception as e:
                logger.error(f"DB Step 10 FAILED (training): {e}")
                raise Exception(f"Failed inserting training: {e}")

            # Log unmatched item stats
            total_unmatched = skill_stats["unmatched"] + cert_stats["unmatched"] + software_stats["unmatched"]
            if total_unmatched > 0:
                logger.info(
                    f"Captured {total_unmatched} unmatched taxonomy items: "
                    f"skills={skill_stats['unmatched']}, certs={cert_stats['unmatched']}, software={software_stats['unmatched']}"
                )

            # Insert quality warnings (Session 46)
            quality_warnings_count = 0
            if quality_result and quality_result.warnings:
                try:
                    logger.info("DB Step 11: Inserting quality warnings")
                    quality_warnings_count = self._insert_quality_warnings(
                        cursor, candidate_id, correlation_id, quality_result
                    )
                    cursor.execute("SELECT 1")  # Force error surface
                    cursor.fetchone()
                    logger.info(f"DB Step 11 complete: {quality_warnings_count} warnings")
                except Exception as e:
                    logger.warning(f"DB Step 11 failed (quality warnings): {e}")
                    # Non-fatal: quality warnings are informational

            # Insert GDPR consent record (basic processing consent)
            self._insert_consent(cursor, candidate_id)

            # Update parsed JSON
            self._update_parsed_json(cursor, candidate_id, parsed_cv)

            # Write unmatched CV data (zero data loss policy)
            unmatched_cv_count = 0
            if parsed_cv.unmatched_data:
                unmatched_cv_count = self.write_unmatched_cv_data(
                    cursor, candidate_id, parsed_cv.unmatched_data
                )

            # Write raw CV JSON backup (zero data loss policy)
            if parsed_cv.raw_json:
                self.write_raw_cv_json(cursor, candidate_id, parsed_cv.raw_json)

            # Commit transaction
            conn.commit()

            logger.info(
                f"Successfully wrote candidate {candidate_id}"
                + (f", {unmatched_cv_count} unmatched CV data items" if unmatched_cv_count > 0 else "")
                + (f", {quality_warnings_count} quality warnings" if quality_warnings_count > 0 else "")
            )

            # Post-write verification (Task 1.2)
            if verify_write:
                verification = self._verify_write(
                    cursor, candidate_id, parsed_cv,
                    skill_stats, cert_stats, software_stats
                )

                if not verification.success:
                    logger.error(
                        f"Write verification FAILED for {candidate_id}: {verification.errors}"
                    )
                elif verification.warnings:
                    logger.warning(
                        f"Write verification passed with warnings for {candidate_id}: "
                        f"{len(verification.warnings)} warnings"
                    )
                else:
                    logger.info(
                        f"Write verification PASSED for {candidate_id}: "
                        f"coverage={verification.coverage_score:.2%}"
                    )

            # CV Completeness Audit (Task 1.3)
            completeness_audit = CVCompletenessAudit.from_parsed_cv(
                parsed_cv,
                skills_matched=skill_stats.get("inserted", 0),
                certs_matched=cert_stats.get("inserted", 0) - cert_stats.get("unmatched", 0),
                software_matched=software_stats.get("inserted", 0),
            )

            logger.info(
                f"CV Completeness Audit for {candidate_id}: "
                f"score={completeness_audit.completeness_score:.2%}, "
                f"level={completeness_audit.quality_level}, "
                f"taxonomy_coverage={completeness_audit.taxonomy_coverage:.2%}"
            )

            # Store verification and audit in DynamoDB
            if verify_write or completeness_audit:
                self._store_verification_and_audit(
                    candidate_id, verification, completeness_audit, correlation_id
                )

            return candidate_id, verification, completeness_audit

        except Exception as e:
            try:
                conn.rollback()
            except Exception as rollback_err:
                # Connection might be broken, reset it for next call
                logger.warning(f"Rollback failed, resetting connection: {rollback_err}")
                try:
                    conn.close()
                except Exception:
                    pass
                self._connection = None
            logger.error(f"Failed to write candidate: {e}")
            raise

        finally:
            try:
                cursor.close()
            except Exception:
                pass  # Ignore cursor close errors

    def _find_duplicate(
        self,
        cursor: Any,
        email: str | None,
        phone: str | None,
        first_name: str,
        last_name: str,
    ) -> UUID | None:
        """Find existing candidate by email, phone, or name."""
        # Check email first (strongest match)
        if email:
            cursor.execute(
                "SELECT id FROM candidates WHERE email = %s AND is_active = true",
                (email,),
            )
            row = cursor.fetchone()
            if row:
                return UUID(str(row[0]))

        # Check phone
        if phone:
            cursor.execute(
                "SELECT id FROM candidates WHERE phone = %s AND is_active = true",
                (phone,),
            )
            row = cursor.fetchone()
            if row:
                return UUID(str(row[0]))

        # Check normalized name (fuzzy)
        if first_name and last_name:
            normalized_name = f"{normalize_text(first_name)} {normalize_text(last_name)}"
            cursor.execute(
                """
                SELECT id FROM candidates
                WHERE similarity(full_name_search, %s) > 0.8
                AND is_active = true
                ORDER BY similarity(full_name_search, %s) DESC
                LIMIT 1
                """,
                (normalized_name, normalized_name),
            )
            row = cursor.fetchone()
            if row:
                return UUID(str(row[0]))

        return None

    def _insert_candidate(
        self,
        cursor: Any,
        parsed_cv: ParsedCV,
        correlation_id: str,
        source_key: str | None,
    ) -> UUID:
        """Insert new candidate record."""
        personal = parsed_cv.personal

        # Sanitize and ensure names are not null
        first_name, last_name = _ensure_name(
            personal.first_name,
            personal.last_name,
            parsed_cv.raw_cv_text
        )

        # Sanitize email (Greek lookalikes, missing dots, null bytes)
        email = _sanitize_email(personal.email)
        email_secondary = _sanitize_email(personal.email_secondary)

        # Sanitize other string fields
        phone = _sanitize_string(personal.phone, max_length=50)
        phone_secondary = _sanitize_string(personal.phone_secondary, max_length=50)
        nationality = _sanitize_string(personal.nationality, max_length=100)
        address_street = _sanitize_string(personal.address_street, max_length=255)
        address_city = _sanitize_string(personal.address_city, max_length=100)
        address_region = _sanitize_string(personal.address_region, max_length=100)
        address_postal_code = _sanitize_string(personal.address_postal_code, max_length=20)
        address_country = _sanitize_string(personal.address_country, max_length=100) or 'Greece'

        # Sanitize raw_cv_text (strip null bytes)
        raw_cv_text = _sanitize_string(parsed_cv.raw_cv_text)

        cursor.execute(
            """
            INSERT INTO candidates (
                first_name, last_name,
                first_name_normalized, last_name_normalized,
                email, email_secondary, phone, phone_secondary,
                date_of_birth, gender, marital_status, nationality,
                address_street, address_city, address_region, address_postal_code, address_country,
                employment_status, availability_status, military_status,
                willing_to_relocate, expected_salary_min, expected_salary_max, salary_currency,
                cv_source, processing_status, quality_score, quality_level,
                raw_cv_text, tags
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                first_name,
                last_name,
                normalize_text(first_name) if first_name else None,
                normalize_text(last_name) if last_name else None,
                email,
                email_secondary,
                phone,
                phone_secondary,
                personal.date_of_birth,
                personal.gender.value if personal.gender else "unknown",
                personal.marital_status.value if personal.marital_status else "unknown",
                nationality,
                address_street,
                address_city,
                address_region,
                address_postal_code,
                address_country,
                personal.employment_status.value if personal.employment_status else "unknown",
                personal.availability_status.value if personal.availability_status else "unknown",
                personal.military_status.value if personal.military_status else "unknown",
                personal.willing_to_relocate,
                personal.expected_salary_min,
                personal.expected_salary_max,
                personal.salary_currency,
                "website",  # cv_source
                "parsed",  # processing_status
                parsed_cv.completeness_score,
                self._get_quality_level(parsed_cv.completeness_score),
                raw_cv_text,
                [f"correlation_id:{correlation_id}"],
            ),
        )

        row = cursor.fetchone()
        return UUID(str(row[0]))

    def _update_candidate(
        self,
        cursor: Any,
        candidate_id: UUID,
        parsed_cv: ParsedCV,
    ) -> None:
        """Update existing candidate record."""
        personal = parsed_cv.personal

        # Sanitize fields
        first_name = _sanitize_string(personal.first_name, max_length=100)
        last_name = _sanitize_string(personal.last_name, max_length=100)
        email = _sanitize_email(personal.email)
        phone = _sanitize_string(personal.phone, max_length=50)
        address_city = _sanitize_string(personal.address_city, max_length=100)
        address_region = _sanitize_string(personal.address_region, max_length=100)

        cursor.execute(
            """
            UPDATE candidates SET
                first_name = COALESCE(%s, first_name),
                last_name = COALESCE(%s, last_name),
                email = COALESCE(%s, email),
                phone = COALESCE(%s, phone),
                address_city = COALESCE(%s, address_city),
                address_region = COALESCE(%s, address_region),
                processing_status = 'parsed',
                quality_score = GREATEST(quality_score, %s),
                updated_at = CURRENT_TIMESTAMP,
                last_activity_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                first_name,
                last_name,
                email,
                phone,
                address_city,
                address_region,
                parsed_cv.completeness_score,
                str(candidate_id),
            ),
        )

        # Delete existing related records before re-inserting
        for table in [
            "candidate_education",
            "candidate_experience",
            "candidate_skills",
            "candidate_languages",
            "candidate_certifications",
            "candidate_driving_licenses",
            "candidate_software",
        ]:
            cursor.execute(f"DELETE FROM {table} WHERE candidate_id = %s", (str(candidate_id),))

    def _insert_education(self, cursor: Any, candidate_id: UUID, education: list) -> None:
        """Insert education records."""
        for edu in education:
            # Validate and fix date range if needed
            start_date = edu.start_date
            end_date = edu.end_date

            # Fix invalid date ranges: if end_date < start_date, swap them
            if start_date and end_date and end_date < start_date:
                logger.warning(
                    f"Education date range invalid: {start_date} > {end_date} "
                    f"for '{edu.degree_title}' at '{edu.institution_name}'. Swapping dates."
                )
                start_date, end_date = end_date, start_date

            # Sanitize string fields (null bytes, truncation)
            institution_name = _sanitize_string(edu.institution_name, max_length=255)
            institution_city = _sanitize_string(edu.institution_city, max_length=100)
            institution_country = _sanitize_string(edu.institution_country, max_length=100)
            degree_title = _sanitize_string(edu.degree_title, max_length=255)
            field_of_study_detail = _sanitize_string(edu.field_of_study_detail, max_length=255)
            specialization = _sanitize_string(edu.specialization, max_length=255)
            grade_value = _sanitize_string(edu.grade_value, max_length=20)  # VARCHAR(20)
            grade_scale = _sanitize_string(edu.grade_scale, max_length=50)
            thesis_title = _sanitize_string(edu.thesis_title, max_length=500)
            honors = _sanitize_string(edu.honors, max_length=255)
            raw_text = _sanitize_string(edu.raw_text)

            cursor.execute(
                """
                INSERT INTO candidate_education (
                    candidate_id, institution_name, institution_name_normalized,
                    institution_city, institution_country,
                    degree_level, degree_title, degree_title_normalized,
                    field_of_study, field_of_study_detail, specialization,
                    start_date, end_date, is_current, graduation_year,
                    grade_value, grade_scale, thesis_title, honors,
                    raw_text, confidence_score
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    str(candidate_id),
                    institution_name,
                    normalize_text(institution_name) if institution_name else None,
                    institution_city,
                    institution_country,
                    edu.degree_level.value if edu.degree_level else None,
                    degree_title,
                    normalize_text(degree_title) if degree_title else None,
                    edu.field_of_study.value if edu.field_of_study else None,
                    field_of_study_detail,
                    specialization,
                    start_date,
                    end_date,
                    edu.is_current,
                    edu.graduation_year,
                    grade_value,
                    grade_scale,
                    thesis_title,
                    honors,
                    raw_text,
                    edu.confidence,
                ),
            )

    def _insert_experience(self, cursor: Any, candidate_id: UUID, experience: list) -> None:
        """Insert experience records."""
        for exp in experience:
            # Validate and fix date range if needed
            start_date = exp.start_date
            end_date = exp.end_date

            # Fix invalid date ranges: if end_date < start_date, swap them
            if start_date and end_date and end_date < start_date:
                logger.warning(
                    f"Experience date range invalid: {start_date} > {end_date} "
                    f"for '{exp.job_title}' at '{exp.company_name}'. Swapping dates."
                )
                start_date, end_date = end_date, start_date

            # Sanitize string fields (null bytes, truncation)
            company_name = _sanitize_string(exp.company_name, max_length=255)
            company_industry = _sanitize_string(exp.company_industry, max_length=100)
            company_city = _sanitize_string(exp.company_city, max_length=100)
            company_country = _sanitize_string(exp.company_country, max_length=100)
            job_title = _sanitize_string(exp.job_title, max_length=255)
            department = _sanitize_string(exp.department, max_length=100)
            description = _sanitize_string(exp.description)
            reports_to = _sanitize_string(exp.reports_to, max_length=255)
            raw_text = _sanitize_string(exp.raw_text)

            # Sanitize array fields
            responsibilities = [_sanitize_string(r) for r in (exp.responsibilities or []) if r]
            achievements = [_sanitize_string(a) for a in (exp.achievements or []) if a]
            technologies_used = [_sanitize_string(t) for t in (exp.technologies_used or []) if t]

            cursor.execute(
                """
                INSERT INTO candidate_experience (
                    candidate_id, company_name, company_name_normalized,
                    company_industry, company_city, company_country,
                    job_title, job_title_normalized, role_id,
                    department, employment_type,
                    start_date, end_date, is_current,
                    description, responsibilities, achievements, technologies_used,
                    team_size, reports_to,
                    raw_text, confidence_score
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    str(candidate_id),
                    company_name,
                    normalize_text(company_name) if company_name else None,
                    company_industry,
                    company_city,
                    company_country,
                    job_title,
                    normalize_text(job_title) if job_title else None,
                    str(exp.role_id) if exp.role_id else None,
                    department,
                    exp.employment_type.value if exp.employment_type else None,
                    start_date,
                    end_date,
                    exp.is_current,
                    description,
                    responsibilities,
                    achievements,
                    technologies_used,
                    exp.team_size,
                    reports_to,
                    raw_text,
                    exp.confidence,
                ),
            )

    def _insert_unmatched_item(
        self,
        cursor: Any,
        candidate_id: UUID,
        item_type: str,
        raw_value: str,
        normalized_value: str,
        source_context: str | None = None,
        source_section: str | None = None,
        suggested_taxonomy_id: UUID | None = None,
        suggested_canonical_id: str | None = None,
        semantic_similarity: float | None = None,
        match_method: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """
        Insert unmatched taxonomy item for later review.

        Uses upsert to increment occurrence count if same item exists.

        Args:
            candidate_id: Candidate UUID
            item_type: 'skill', 'software', 'certification', 'role', etc.
            raw_value: Original value from CV
            normalized_value: Normalized value for matching
            source_context: Surrounding text for context
            source_section: Section of CV where found
            suggested_taxonomy_id: Best match taxonomy ID (if any)
            suggested_canonical_id: Best match canonical ID (if any)
            semantic_similarity: Match similarity score
            match_method: How match was determined
            correlation_id: Processing correlation ID
        """
        try:
            # Use the upsert function if available, otherwise direct insert
            cursor.execute(
                """
                SELECT upsert_unmatched_item(
                    %s::uuid, %s::unmatched_item_type, %s, %s, %s, %s,
                    %s::uuid, %s, %s::decimal(5,4), %s, %s
                )
                """,
                (
                    str(candidate_id),
                    item_type,
                    raw_value,
                    normalized_value,
                    source_context,
                    source_section,
                    str(suggested_taxonomy_id) if suggested_taxonomy_id else None,
                    suggested_canonical_id,
                    semantic_similarity,
                    match_method or 'none',
                    correlation_id,
                ),
            )
        except Exception as e:
            # Fallback to direct insert if upsert function doesn't exist
            logger.debug(f"upsert_unmatched_item failed, using direct insert: {e}")
            cursor.execute(
                """
                INSERT INTO unmatched_taxonomy_items (
                    candidate_id, correlation_id, item_type,
                    raw_value, normalized_value, source_context, source_section,
                    suggested_taxonomy_id, suggested_canonical_id, semantic_similarity,
                    match_method
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (
                    str(candidate_id),
                    correlation_id,
                    item_type,
                    raw_value,
                    normalized_value,
                    source_context,
                    source_section,
                    str(suggested_taxonomy_id) if suggested_taxonomy_id else None,
                    suggested_canonical_id,
                    semantic_similarity,
                    match_method or 'none',
                ),
            )

    def _insert_skills(
        self,
        cursor: Any,
        candidate_id: UUID,
        skills: list,
        correlation_id: str | None = None,
    ) -> dict:
        """
        Insert skill records, capturing unmatched items.

        Returns:
            Stats dict with 'inserted' and 'unmatched' counts
        """
        stats = {"inserted": 0, "unmatched": 0}

        for skill in skills:
            if not skill.skill_id:
                # Capture unmatched skill instead of silently skipping
                self._insert_unmatched_item(
                    cursor=cursor,
                    candidate_id=candidate_id,
                    item_type="skill",
                    raw_value=skill.name,
                    normalized_value=normalize_text(skill.name),
                    source_context=skill.source_context,
                    source_section="skills",
                    suggested_taxonomy_id=skill.suggested_taxonomy_id,
                    suggested_canonical_id=skill.suggested_canonical_id,
                    semantic_similarity=skill.semantic_similarity,
                    match_method=skill.match_method,
                    correlation_id=correlation_id,
                )
                stats["unmatched"] += 1
                continue

            cursor.execute(
                """
                INSERT INTO candidate_skills (
                    candidate_id, skill_id,
                    skill_level, years_of_experience, last_used_year,
                    source, source_context, confidence_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (candidate_id, skill_id) DO UPDATE SET
                    skill_level = COALESCE(EXCLUDED.skill_level, candidate_skills.skill_level),
                    years_of_experience = GREATEST(EXCLUDED.years_of_experience, candidate_skills.years_of_experience),
                    confidence_score = GREATEST(EXCLUDED.confidence_score, candidate_skills.confidence_score),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(candidate_id),
                    str(skill.skill_id),
                    skill.level.value if skill.level else None,
                    skill.years_of_experience,
                    skill.last_used_year,
                    "cv_parsed",
                    skill.source_context,
                    skill.confidence,
                ),
            )
            stats["inserted"] += 1

        return stats

    def _insert_languages(self, cursor: Any, candidate_id: UUID, languages: list) -> None:
        """Insert language records."""
        for lang in languages:
            cursor.execute(
                """
                INSERT INTO candidate_languages (
                    candidate_id, language_code, language_name,
                    proficiency_level, reading_level, writing_level, speaking_level, listening_level,
                    certification_name, certification_score, certification_date, certification_expiry,
                    is_native, is_verified
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (candidate_id, language_code) DO UPDATE SET
                    proficiency_level = COALESCE(EXCLUDED.proficiency_level, candidate_languages.proficiency_level),
                    certification_name = COALESCE(EXCLUDED.certification_name, candidate_languages.certification_name),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    str(candidate_id),
                    lang.language_code,
                    lang.language_name,
                    lang.proficiency_level.value if lang.proficiency_level else "unknown",
                    lang.reading_level.value if lang.reading_level else None,
                    lang.writing_level.value if lang.writing_level else None,
                    lang.speaking_level.value if lang.speaking_level else None,
                    lang.listening_level.value if lang.listening_level else None,
                    lang.certification_name,
                    lang.certification_score,
                    lang.certification_date,
                    lang.certification_expiry,
                    lang.is_native,
                    False,  # is_verified
                ),
            )

    def _insert_certifications(
        self,
        cursor: Any,
        candidate_id: UUID,
        certifications: list,
        correlation_id: str | None = None,
    ) -> dict:
        """
        Insert certification records, capturing unmatched items.

        Certifications are always inserted (even unmatched ones), but
        unmatched ones are also captured in unmatched_taxonomy_items
        for later review and taxonomy expansion.

        Returns:
            Stats dict with 'inserted' and 'unmatched' counts
        """
        stats = {"inserted": 0, "unmatched": 0}

        for cert in certifications:
            # Always insert the certification record
            cursor.execute(
                """
                INSERT INTO candidate_certifications (
                    candidate_id, certification_name, certification_name_normalized,
                    certification_id_taxonomy, issuing_organization, issuing_organization_normalized,
                    credential_id, credential_url,
                    issue_date, expiry_date,
                    raw_text, confidence_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(candidate_id),
                    cert.certification_name,
                    normalize_text(cert.certification_name) if cert.certification_name else None,
                    str(cert.certification_id) if cert.certification_id else None,
                    cert.issuing_organization,
                    normalize_text(cert.issuing_organization) if cert.issuing_organization else None,
                    cert.credential_id,
                    cert.credential_url,
                    cert.issue_date,
                    cert.expiry_date,
                    cert.raw_text,
                    cert.confidence,
                ),
            )
            stats["inserted"] += 1

            # Also capture in unmatched table if no taxonomy match
            if not cert.certification_id:
                self._insert_unmatched_item(
                    cursor=cursor,
                    candidate_id=candidate_id,
                    item_type="certification",
                    raw_value=cert.certification_name,
                    normalized_value=normalize_text(cert.certification_name) if cert.certification_name else "",
                    source_context=cert.raw_text,
                    source_section="certifications",
                    suggested_taxonomy_id=cert.suggested_taxonomy_id,
                    suggested_canonical_id=cert.suggested_canonical_id,
                    semantic_similarity=cert.semantic_similarity,
                    match_method=cert.match_method,
                    correlation_id=correlation_id,
                )
                stats["unmatched"] += 1

        return stats

    def _insert_driving_licenses(self, cursor: Any, candidate_id: UUID, licenses: list) -> None:
        """Insert driving license records."""
        for dl in licenses:
            cursor.execute(
                """
                INSERT INTO candidate_driving_licenses (
                    candidate_id, license_category,
                    issue_date, expiry_date, issuing_country, license_number,
                    is_verified
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (candidate_id, license_category) DO UPDATE SET
                    issue_date = COALESCE(EXCLUDED.issue_date, candidate_driving_licenses.issue_date),
                    expiry_date = COALESCE(EXCLUDED.expiry_date, candidate_driving_licenses.expiry_date)
                """,
                (
                    str(candidate_id),
                    dl.license_category.value,
                    dl.issue_date,
                    dl.expiry_date,
                    dl.issuing_country,
                    dl.license_number,
                    False,  # is_verified
                ),
            )

    def _insert_software(
        self,
        cursor: Any,
        candidate_id: UUID,
        software: list,
        correlation_id: str | None = None,
    ) -> dict:
        """
        Insert software records, capturing unmatched items.

        Returns:
            Stats dict with 'inserted' and 'unmatched' counts
        """
        stats = {"inserted": 0, "unmatched": 0}

        for sw in software:
            if not sw.software_id:
                # Capture unmatched software instead of silently skipping
                self._insert_unmatched_item(
                    cursor=cursor,
                    candidate_id=candidate_id,
                    item_type="software",
                    raw_value=sw.name,
                    normalized_value=normalize_text(sw.name),
                    source_context=None,
                    source_section="software",
                    suggested_taxonomy_id=sw.suggested_taxonomy_id,
                    suggested_canonical_id=sw.suggested_canonical_id,
                    semantic_similarity=sw.semantic_similarity,
                    match_method=sw.match_method,
                    correlation_id=correlation_id,
                )
                stats["unmatched"] += 1
                continue

            cursor.execute(
                """
                INSERT INTO candidate_software (
                    candidate_id, software_id,
                    proficiency_level, version_used, years_of_experience, last_used_year,
                    source, confidence_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (candidate_id, software_id) DO UPDATE SET
                    proficiency_level = COALESCE(EXCLUDED.proficiency_level, candidate_software.proficiency_level),
                    years_of_experience = GREATEST(EXCLUDED.years_of_experience, candidate_software.years_of_experience)
                """,
                (
                    str(candidate_id),
                    str(sw.software_id),
                    sw.proficiency_level.value if sw.proficiency_level else None,
                    sw.version_used,
                    sw.years_of_experience,
                    sw.last_used_year,
                    "cv_parsed",
                    sw.confidence,
                ),
            )
            stats["inserted"] += 1

        return stats

    def _insert_training(
        self,
        cursor: Any,
        candidate_id: UUID,
        training_list: list[ParsedTraining],
    ) -> int:
        """
        Insert training/seminar records for a candidate.

        Args:
            cursor: Database cursor
            candidate_id: Candidate UUID
            training_list: List of ParsedTraining objects

        Returns:
            Number of training records inserted
        """
        if not training_list:
            return 0

        count = 0
        for training in training_list:
            try:
                cursor.execute(
                    """
                    INSERT INTO candidate_training (
                        candidate_id,
                        training_name,
                        provider_name,
                        provider_type,
                        training_type,
                        category,
                        duration_hours,
                        duration_days,
                        completion_date,
                        start_date,
                        description,
                        skills_gained,
                        certificate_received,
                        raw_text,
                        confidence
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(candidate_id),
                        training.training_name,
                        training.provider_name,
                        training.provider_type,
                        training.training_type,
                        training.category,
                        training.duration_hours,
                        training.duration_days,
                        training.completion_date,
                        training.start_date,
                        training.description,
                        training.skills_gained if training.skills_gained else None,
                        training.certificate_received,
                        training.raw_text,
                        training.confidence,
                    ),
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to insert training '{training.training_name}': {e}")

        if count > 0:
            logger.info(f"Inserted {count} training/seminar records for candidate {candidate_id}")

        return count

    def _insert_quality_warnings(
        self,
        cursor: Any,
        candidate_id: UUID,
        correlation_id: str,
        quality_result: QualityCheckResult,
    ) -> int:
        """
        Insert quality warnings from quality check result.

        Args:
            cursor: Database cursor
            candidate_id: Candidate UUID
            correlation_id: Processing correlation ID
            quality_result: QualityCheckResult with warnings

        Returns:
            Number of warnings inserted
        """
        if not quality_result or not quality_result.warnings:
            return 0

        count = 0
        for warning in quality_result.warnings:
            try:
                cursor.execute(
                    """
                    INSERT INTO cv_quality_warnings (
                        candidate_id,
                        correlation_id,
                        category,
                        severity,
                        field_name,
                        section,
                        message,
                        message_greek,
                        original_value,
                        suggested_value,
                        was_auto_fixed,
                        llm_detected
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(candidate_id),
                        correlation_id,
                        warning.category.value,
                        warning.severity.value,
                        warning.field_name,
                        warning.section,
                        warning.message,
                        warning.message_greek,
                        warning.original_value[:500] if warning.original_value else None,
                        warning.suggested_value[:500] if warning.suggested_value else None,
                        warning.was_auto_fixed,
                        warning.llm_detected,
                    ),
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to insert quality warning: {e}")

        if count > 0:
            logger.info(f"Inserted {count} quality warnings for candidate {candidate_id}")

        return count

    def _insert_consent(self, cursor: Any, candidate_id: UUID) -> None:
        """Insert basic GDPR consent record."""
        cursor.execute(
            """
            INSERT INTO consent_records (
                candidate_id, consent_type, status,
                consent_text, consent_version,
                collection_method, granted_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                str(candidate_id),
                "data_processing",
                "granted",
                "CV submitted for job application processing",
                "1.0",
                "cv_upload",
                datetime.now(timezone.utc),
            ),
        )

    def _update_parsed_json(self, cursor: Any, candidate_id: UUID, parsed_cv: ParsedCV) -> None:
        """Update candidate with parsed JSON data."""
        cursor.execute(
            """
            UPDATE candidates SET
                parsed_cv_json = %s
            WHERE id = %s
            """,
            (
                json.dumps(parsed_cv.to_dict(), ensure_ascii=False),
                str(candidate_id),
            ),
        )

    def _verify_write(
        self,
        cursor: Any,
        candidate_id: UUID,
        parsed_cv: ParsedCV,
        skill_stats: dict,
        cert_stats: dict,
        software_stats: dict,
    ) -> WriteVerification:
        """
        Verify all records were written correctly after commit.

        Compares expected counts (from parsed CV) with actual counts in database.
        This is Task 1.2: Post-Write Verification.

        Args:
            cursor: Database cursor
            candidate_id: ID of written candidate
            parsed_cv: Original parsed CV data
            skill_stats: Stats from _insert_skills
            cert_stats: Stats from _insert_certifications
            software_stats: Stats from _insert_software

        Returns:
            WriteVerification with counts, success status, and any errors/warnings
        """
        verification = WriteVerification(
            candidate_id=candidate_id,
            success=False,
            # Expected counts - matched items only
            education_expected=len(parsed_cv.education),
            experience_expected=len(parsed_cv.experience),
            skills_expected=skill_stats.get("inserted", 0) + skill_stats.get("unmatched", 0),
            skills_unmatched=skill_stats.get("unmatched", 0),
            languages_expected=len(parsed_cv.languages),
            certifications_expected=cert_stats.get("inserted", 0),
            certifications_unmatched=cert_stats.get("unmatched", 0),
            driving_licenses_expected=len(parsed_cv.driving_licenses),
            software_expected=software_stats.get("inserted", 0) + software_stats.get("unmatched", 0),
            software_unmatched=software_stats.get("unmatched", 0),
        )

        # Verify candidate exists
        cursor.execute("SELECT 1 FROM candidates WHERE id = %s", (str(candidate_id),))
        if not cursor.fetchone():
            verification.errors.append("Candidate record not found after insert")
            return verification

        # Count education records
        cursor.execute(
            "SELECT COUNT(*) FROM candidate_education WHERE candidate_id = %s",
            (str(candidate_id),),
        )
        verification.education_actual = cursor.fetchone()[0]

        # Count experience records
        cursor.execute(
            "SELECT COUNT(*) FROM candidate_experience WHERE candidate_id = %s",
            (str(candidate_id),),
        )
        verification.experience_actual = cursor.fetchone()[0]

        # Count skill records (matched only - unmatched go to unmatched_taxonomy_items)
        cursor.execute(
            "SELECT COUNT(*) FROM candidate_skills WHERE candidate_id = %s",
            (str(candidate_id),),
        )
        verification.skills_actual = cursor.fetchone()[0]

        # Count language records
        cursor.execute(
            "SELECT COUNT(*) FROM candidate_languages WHERE candidate_id = %s",
            (str(candidate_id),),
        )
        verification.languages_actual = cursor.fetchone()[0]

        # Count certification records (all certs are inserted)
        cursor.execute(
            "SELECT COUNT(*) FROM candidate_certifications WHERE candidate_id = %s",
            (str(candidate_id),),
        )
        verification.certifications_actual = cursor.fetchone()[0]

        # Count driving license records
        cursor.execute(
            "SELECT COUNT(*) FROM candidate_driving_licenses WHERE candidate_id = %s",
            (str(candidate_id),),
        )
        verification.driving_licenses_actual = cursor.fetchone()[0]

        # Count software records (matched only)
        cursor.execute(
            "SELECT COUNT(*) FROM candidate_software WHERE candidate_id = %s",
            (str(candidate_id),),
        )
        verification.software_actual = cursor.fetchone()[0]

        # Check for mismatches - education and experience are critical
        if verification.education_actual != verification.education_expected:
            verification.errors.append(
                f"Education mismatch: expected {verification.education_expected}, got {verification.education_actual}"
            )

        if verification.experience_actual != verification.experience_expected:
            verification.errors.append(
                f"Experience mismatch: expected {verification.experience_expected}, got {verification.experience_actual}"
            )

        # Skills: matched count should equal inserted count
        expected_matched_skills = skill_stats.get("inserted", 0)
        if verification.skills_actual != expected_matched_skills:
            verification.errors.append(
                f"Skills mismatch: expected {expected_matched_skills} matched, got {verification.skills_actual}"
            )

        if verification.languages_actual != verification.languages_expected:
            verification.warnings.append(
                f"Languages mismatch: expected {verification.languages_expected}, got {verification.languages_actual}"
            )

        if verification.certifications_actual != verification.certifications_expected:
            verification.warnings.append(
                f"Certifications mismatch: expected {verification.certifications_expected}, got {verification.certifications_actual}"
            )

        if verification.driving_licenses_actual != verification.driving_licenses_expected:
            verification.warnings.append(
                f"Driving licenses mismatch: expected {verification.driving_licenses_expected}, got {verification.driving_licenses_actual}"
            )

        # Software: matched count should equal inserted count
        expected_matched_software = software_stats.get("inserted", 0)
        if verification.software_actual != expected_matched_software:
            verification.warnings.append(
                f"Software mismatch: expected {expected_matched_software} matched, got {verification.software_actual}"
            )

        # Add informational warnings for unmatched items
        if verification.skills_unmatched > 0:
            verification.warnings.append(
                f"{verification.skills_unmatched} skills captured as unmatched (pending taxonomy review)"
            )

        if verification.software_unmatched > 0:
            verification.warnings.append(
                f"{verification.software_unmatched} software captured as unmatched (pending taxonomy review)"
            )

        if verification.certifications_unmatched > 0:
            verification.warnings.append(
                f"{verification.certifications_unmatched} certifications captured as unmatched (pending taxonomy review)"
            )

        # Determine overall success - only critical errors cause failure
        verification.success = len(verification.errors) == 0

        return verification

    def _store_verification_and_audit(
        self,
        candidate_id: UUID,
        verification: WriteVerification | None,
        completeness_audit: CVCompletenessAudit | None,
        correlation_id: str,
    ) -> None:
        """
        Store verification and completeness audit results in DynamoDB for tracking.

        Updates the cv-processing-state table with verification and audit data,
        enabling monitoring and debugging of data integrity and quality.

        Task 1.2: Write Verification storage
        Task 1.3: Completeness Audit storage

        Args:
            candidate_id: Candidate UUID
            verification: WriteVerification result (may be None)
            completeness_audit: CVCompletenessAudit result (may be None)
            correlation_id: Processing correlation ID
        """
        from decimal import Decimal

        def convert_floats(obj: Any) -> Any:
            """Convert floats to Decimal for DynamoDB compatibility."""
            if isinstance(obj, float):
                return Decimal(str(obj))
            elif isinstance(obj, dict):
                return {k: convert_floats(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_floats(i) for i in obj]
            return obj

        try:
            dynamodb = boto3.resource("dynamodb", region_name=self.region)
            table = dynamodb.Table("lcmgo-cagenai-prod-cv-processing-state")

            # Determine status based on verification and audit results
            if verification:
                if verification.success and not verification.warnings:
                    status = "completed"
                elif verification.success:
                    status = "completed_with_warnings"
                else:
                    status = "completed_with_errors"
            else:
                status = "completed"

            # Build update expression and attribute values
            update_expr_parts = [
                "#s = :status",
                "candidate_id = :cid",
                "audit_time = :t",
            ]
            expr_attr_values = {
                ":status": status,
                ":cid": str(candidate_id),
                ":t": datetime.now(timezone.utc).isoformat(),
            }

            # Add verification data if available
            if verification:
                verification_data = convert_floats(verification.to_dict())
                update_expr_parts.append("write_verification = :v")
                expr_attr_values[":v"] = verification_data

            # Add completeness audit data if available (Task 1.3)
            if completeness_audit:
                audit_data = convert_floats(completeness_audit.to_dict())
                update_expr_parts.append("completeness_audit = :audit")
                update_expr_parts.append("completeness_score = :cscore")
                update_expr_parts.append("quality_level = :qlevel")
                update_expr_parts.append("taxonomy_coverage = :tcov")
                expr_attr_values[":audit"] = audit_data
                expr_attr_values[":cscore"] = Decimal(str(round(completeness_audit.completeness_score, 4)))
                expr_attr_values[":qlevel"] = completeness_audit.quality_level
                expr_attr_values[":tcov"] = Decimal(str(round(completeness_audit.taxonomy_coverage, 4)))

            table.update_item(
                Key={"cv_id": correlation_id},
                UpdateExpression="SET " + ", ".join(update_expr_parts),
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues=expr_attr_values,
            )

            logger.debug(
                f"Stored verification and audit for {correlation_id}: "
                f"status={status}, quality={completeness_audit.quality_level if completeness_audit else 'N/A'}"
            )

        except Exception as e:
            # Don't fail the whole operation if DynamoDB update fails
            logger.warning(f"Failed to store verification/audit in DynamoDB: {e}")

    def write_unmatched_cv_data(
        self,
        cursor: Any,
        candidate_id: UUID,
        unmatched_items: list[ParsedUnmatchedData],
    ) -> int:
        """
        Write unmatched CV data to the unmatched_cv_data table.

        This implements the zero data loss policy - any data that the LLM
        could not map to existing fields is captured here for later review.

        Args:
            cursor: Database cursor
            candidate_id: Candidate UUID
            unmatched_items: List of ParsedUnmatchedData from parsed CV

        Returns:
            Number of items written
        """
        if not unmatched_items:
            return 0

        count = 0
        for item in unmatched_items:
            try:
                cursor.execute(
                    """
                    INSERT INTO unmatched_cv_data (
                        candidate_id,
                        suggested_section,
                        field_name,
                        field_value,
                        field_value_normalized,
                        source_text,
                        extraction_confidence,
                        llm_reasoning,
                        review_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(candidate_id),
                        item.suggested_section,
                        item.field_name,
                        item.field_value,
                        normalize_text(item.field_value) if item.field_value else None,
                        item.source_text,
                        item.extraction_confidence,
                        item.llm_reasoning,
                        "pending",
                    ),
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to insert unmatched item '{item.field_name}': {e}")

        if count > 0:
            logger.info(f"Wrote {count} unmatched CV data items for candidate {candidate_id}")

        return count

    def write_raw_cv_json(
        self,
        cursor: Any,
        candidate_id: UUID,
        raw_json: dict,
    ) -> bool:
        """
        Write raw CV JSON to candidates.raw_cv_json column as backup.

        This ensures zero data loss - even if parsing/mapping fails,
        the complete raw JSON from the LLM is preserved.

        Args:
            cursor: Database cursor
            candidate_id: Candidate UUID
            raw_json: Complete parsed CV data as dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            # Sanitize JSON to remove null bytes that PostgreSQL can't handle
            sanitized_json = _sanitize_json(raw_json)
            cursor.execute(
                """
                UPDATE candidates
                SET raw_cv_json = %s
                WHERE id = %s
                """,
                (
                    json.dumps(sanitized_json, ensure_ascii=False),
                    str(candidate_id),
                ),
            )
            logger.debug(f"Stored raw CV JSON for candidate {candidate_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to store raw CV JSON: {e}")
            return False

    @staticmethod
    def _get_quality_level(score: float) -> str:
        """Map quality score to quality level enum."""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "fair"
        elif score >= 0.3:
            return "poor"
        else:
            return "insufficient"

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
