"""
CV Quality Checker Module.

Performs quality checks on parsed CVs and generates warnings for:
- Date range errors (automatically fixed)
- Contact validation issues (email/phone)
- Missing critical/optional fields
- LLM-detected spelling issues
- OCR artifacts

Session 46: CV Quality Check Feature
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WarningSeverity(str, Enum):
    """Warning severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class WarningCategory(str, Enum):
    """Warning categories matching PostgreSQL enum."""
    DATE_ERROR = "date_error"
    CONTACT_ISSUE = "contact_issue"
    MISSING_CRITICAL = "missing_critical"
    MISSING_OPTIONAL = "missing_optional"
    SPELLING_SUSPECT = "spelling_suspect"
    FORMAT_ISSUE = "format_issue"
    DATA_QUALITY = "data_quality"
    TAXONOMY_MISMATCH = "taxonomy_mismatch"
    OCR_ARTIFACT = "ocr_artifact"


# Greek translations for warning messages
GREEK_MESSAGES = {
    # Missing fields
    "missing_name": "Λείπει το όνομα ή το επώνυμο",
    "missing_email": "Λείπει η διεύθυνση email",
    "missing_phone": "Λείπει ο αριθμός τηλεφώνου",
    "missing_contact": "Δεν υπάρχουν στοιχεία επικοινωνίας (email ή τηλέφωνο)",
    "missing_location": "Δεν αναφέρεται η τοποθεσία (πόλη)",
    "missing_education": "Δεν αναφέρεται εκπαίδευση",
    "missing_experience": "Δεν αναφέρεται εργασιακή εμπειρία",

    # Date errors
    "date_range_swapped": "Η ημερομηνία λήξης είναι πριν την ημερομηνία έναρξης",
    "date_range_fixed": "Διορθώθηκε αυτόματα: ημερομηνίες αντιστράφηκαν",

    # Contact issues
    "email_format": "Πιθανό σφάλμα μορφής email",
    "email_typo": "Πιθανό τυπογραφικό λάθος στο email",
    "phone_format": "Μη έγκυρη μορφή τηλεφώνου",

    # Spelling/OCR
    "spelling_suspect": "Πιθανό ορθογραφικό λάθος",
    "ocr_artifact": "Πιθανό σφάλμα OCR",
}


@dataclass
class QualityWarning:
    """Single quality warning."""

    category: WarningCategory
    severity: WarningSeverity
    message: str
    message_greek: str | None = None
    field_name: str | None = None
    section: str | None = None
    original_value: str | None = None
    suggested_value: str | None = None
    was_auto_fixed: bool = False
    llm_detected: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "message_greek": self.message_greek,
            "field_name": self.field_name,
            "section": self.section,
            "original_value": self.original_value,
            "suggested_value": self.suggested_value,
            "was_auto_fixed": self.was_auto_fixed,
            "llm_detected": self.llm_detected,
        }


@dataclass
class QualityCheckResult:
    """Result of quality check on a CV."""

    warnings: list[QualityWarning] = field(default_factory=list)

    @property
    def warning_count(self) -> int:
        """Count of all warnings."""
        return len(self.warnings)

    @property
    def error_count(self) -> int:
        """Count of error-level warnings."""
        return sum(1 for w in self.warnings if w.severity == WarningSeverity.ERROR)

    @property
    def info_count(self) -> int:
        """Count of info-level warnings."""
        return sum(1 for w in self.warnings if w.severity == WarningSeverity.INFO)

    @property
    def has_errors(self) -> bool:
        """True if there are any error-level warnings."""
        return self.error_count > 0

    @property
    def has_warnings(self) -> bool:
        """True if there are any warnings (excluding info)."""
        return any(w.severity in (WarningSeverity.WARNING, WarningSeverity.ERROR) for w in self.warnings)

    @property
    def auto_fixed_count(self) -> int:
        """Count of auto-fixed issues."""
        return sum(1 for w in self.warnings if w.was_auto_fixed)

    @property
    def llm_detected_count(self) -> int:
        """Count of LLM-detected issues."""
        return sum(1 for w in self.warnings if w.llm_detected)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "warning_count": self.warning_count,
            "error_count": self.error_count,
            "info_count": self.info_count,
            "auto_fixed_count": self.auto_fixed_count,
            "llm_detected_count": self.llm_detected_count,
            "has_errors": self.has_errors,
            "warnings": [w.to_dict() for w in self.warnings],
        }


class CVQualityChecker:
    """
    Quality checker for parsed CVs.

    Checks for common data quality issues and generates warnings
    that can be displayed to users during upload.

    Usage:
        checker = CVQualityChecker()
        checker.check_completeness(parsed_cv)
        checker.add_email_warnings(parsed_cv.personal.email_warnings, ...)
        result = checker.get_result()
    """

    def __init__(self):
        """Initialize quality checker."""
        self._warnings: list[QualityWarning] = []

    def check_completeness(self, parsed_cv: Any) -> None:
        """
        Check parsed CV for completeness issues.

        Args:
            parsed_cv: ParsedCV object
        """
        personal = parsed_cv.personal

        # Critical: Name
        if not personal.first_name or not personal.last_name:
            self._warnings.append(QualityWarning(
                category=WarningCategory.MISSING_CRITICAL,
                severity=WarningSeverity.ERROR,
                message="Name (first or last) is missing",
                message_greek=GREEK_MESSAGES["missing_name"],
                field_name="name",
                section="personal",
            ))

        # Critical: Contact info (need at least one)
        has_email = bool(personal.email)
        has_phone = bool(personal.phone)

        if not has_email and not has_phone:
            self._warnings.append(QualityWarning(
                category=WarningCategory.MISSING_CRITICAL,
                severity=WarningSeverity.ERROR,
                message="No contact information (email or phone)",
                message_greek=GREEK_MESSAGES["missing_contact"],
                field_name="contact",
                section="personal",
            ))

        # Optional: Location
        if not personal.address_city and not personal.address_region:
            self._warnings.append(QualityWarning(
                category=WarningCategory.MISSING_OPTIONAL,
                severity=WarningSeverity.INFO,
                message="Location (city) not specified",
                message_greek=GREEK_MESSAGES["missing_location"],
                field_name="address_city",
                section="personal",
            ))

        # Optional: Education or Experience (should have at least one)
        has_education = len(parsed_cv.education) > 0
        has_experience = len(parsed_cv.experience) > 0

        if not has_education and not has_experience:
            self._warnings.append(QualityWarning(
                category=WarningCategory.MISSING_OPTIONAL,
                severity=WarningSeverity.WARNING,
                message="No education or work experience listed",
                message_greek="Δεν αναφέρεται εκπαίδευση ή εργασιακή εμπειρία",
                field_name="history",
                section="general",
            ))

    def add_email_warnings(
        self,
        warnings: list[str] | None,
        suggestions: list[str] | None,
        email: str | None,
    ) -> None:
        """
        Add email validation warnings.

        Args:
            warnings: List of warning messages from email validation
            suggestions: List of suggested corrections
            email: The original email address
        """
        if not warnings:
            return

        for i, warning in enumerate(warnings):
            suggestion = suggestions[i] if suggestions and i < len(suggestions) else None
            self._warnings.append(QualityWarning(
                category=WarningCategory.CONTACT_ISSUE,
                severity=WarningSeverity.WARNING,
                message=f"Email: {warning}",
                message_greek=GREEK_MESSAGES.get("email_typo", warning),
                field_name="email",
                section="personal",
                original_value=email,
                suggested_value=suggestion,
            ))

    def add_phone_warnings(
        self,
        warnings: list[str] | None,
        suggestions: list[str] | None,
        phone: str | None,
    ) -> None:
        """
        Add phone validation warnings.

        Args:
            warnings: List of warning messages from phone validation
            suggestions: List of suggested corrections
            phone: The original phone number
        """
        if not warnings:
            return

        for i, warning in enumerate(warnings):
            suggestion = suggestions[i] if suggestions and i < len(suggestions) else None
            self._warnings.append(QualityWarning(
                category=WarningCategory.CONTACT_ISSUE,
                severity=WarningSeverity.WARNING,
                message=f"Phone: {warning}",
                message_greek=GREEK_MESSAGES.get("phone_format", warning),
                field_name="phone",
                section="personal",
                original_value=phone,
                suggested_value=suggestion,
            ))

    def add_date_swap_warning(
        self,
        section: str,
        index: int,
        description: str,
        start_date: str,
        end_date: str,
    ) -> None:
        """
        Add warning for auto-fixed date range swap.

        Args:
            section: CV section (experience, education)
            index: Index in the list
            description: Description of the item (job title, degree)
            start_date: Original start date
            end_date: Original end date
        """
        self._warnings.append(QualityWarning(
            category=WarningCategory.DATE_ERROR,
            severity=WarningSeverity.WARNING,
            message=f"Date range corrected: {section}[{index}] had end_date before start_date",
            message_greek=f"{GREEK_MESSAGES['date_range_fixed']}: {description}",
            field_name="date_range",
            section=section,
            original_value=f"{start_date} - {end_date}",
            suggested_value=f"{end_date} - {start_date}",
            was_auto_fixed=True,
        ))

    def add_llm_warnings(self, llm_warnings: list[dict] | None) -> None:
        """
        Add warnings detected by LLM during parsing.

        Expected format:
        [
            {
                "type": "spelling" | "ocr_artifact",
                "field": "skills" | "certifications" | ...,
                "original": "ιδιοτιτες",
                "suggested": "ιδιότητες",
                "context": "..."
            }
        ]

        Args:
            llm_warnings: List of warning dicts from LLM
        """
        if not llm_warnings:
            return

        for warning in llm_warnings:
            warning_type = warning.get("type", "spelling")

            if warning_type == "ocr_artifact":
                category = WarningCategory.OCR_ARTIFACT
                message = f"Possible OCR error in '{warning.get('field', 'unknown')}'"
                message_greek = GREEK_MESSAGES["ocr_artifact"]
            else:
                category = WarningCategory.SPELLING_SUSPECT
                message = f"Possible spelling error: '{warning.get('original', '')}'"
                message_greek = f"{GREEK_MESSAGES['spelling_suspect']}: {warning.get('original', '')}"

            self._warnings.append(QualityWarning(
                category=category,
                severity=WarningSeverity.INFO,
                message=message,
                message_greek=message_greek,
                field_name=warning.get("field"),
                section=warning.get("section"),
                original_value=warning.get("original"),
                suggested_value=warning.get("suggested"),
                llm_detected=True,
            ))

    def add_taxonomy_mismatch_warning(
        self,
        item_type: str,
        item_name: str,
        count: int | None = None,
    ) -> None:
        """
        Add warning for items not found in taxonomy.

        Args:
            item_type: Type of item (skill, software, certification)
            item_name: Name of the unmatched item (or count description)
            count: Number of unmatched items (optional)
        """
        if count and count > 0:
            message = f"{count} {item_type}(s) not found in taxonomy"
            message_greek = f"{count} {item_type}(s) δεν βρέθηκαν στην ταξινομία"
        else:
            message = f"{item_type} not in taxonomy: '{item_name}'"
            message_greek = f"{item_type} δεν βρέθηκε στην ταξινομία: '{item_name}'"

        self._warnings.append(QualityWarning(
            category=WarningCategory.TAXONOMY_MISMATCH,
            severity=WarningSeverity.INFO,
            message=message,
            message_greek=message_greek,
            field_name=item_type,
            section="taxonomy",
            original_value=item_name if not count else None,
        ))

    def add_custom_warning(
        self,
        category: WarningCategory,
        severity: WarningSeverity,
        message: str,
        message_greek: str | None = None,
        field_name: str | None = None,
        section: str | None = None,
        original_value: str | None = None,
        suggested_value: str | None = None,
        was_auto_fixed: bool = False,
        llm_detected: bool = False,
    ) -> None:
        """
        Add a custom warning.

        Args:
            category: Warning category
            severity: Warning severity
            message: Warning message
            message_greek: Greek translation (optional)
            field_name: Field name (optional)
            section: Section name (optional)
            original_value: Original value (optional)
            suggested_value: Suggested value (optional)
            was_auto_fixed: Whether issue was auto-fixed
            llm_detected: Whether detected by LLM
        """
        self._warnings.append(QualityWarning(
            category=category,
            severity=severity,
            message=message,
            message_greek=message_greek,
            field_name=field_name,
            section=section,
            original_value=original_value,
            suggested_value=suggested_value,
            was_auto_fixed=was_auto_fixed,
            llm_detected=llm_detected,
        ))

    def get_result(self) -> QualityCheckResult:
        """
        Get the quality check result.

        Returns:
            QualityCheckResult with all warnings
        """
        return QualityCheckResult(warnings=self._warnings.copy())

    def clear(self) -> None:
        """Clear all warnings."""
        self._warnings = []
