"""
Data validators for CV parsing.

Task 1.7: Email/Phone Validation Enhancement
Detects email typos and suspicious patterns during CV parsing.
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class ValidationResult:
    """Result of validation check."""

    is_valid: bool
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.suggestions is None:
            self.suggestions = []


def validate_email(email: str | None) -> ValidationResult:
    """
    Validate email and detect common typos.

    Checks:
    - Basic format validation
    - Repeated character detection (e.g., 'nnn' in 'katsigiannnnis')
    - Common domain typos (e.g., 'gmial.com' vs 'gmail.com')
    - Suspicious patterns (spaces, double dots)

    Args:
        email: Email address to validate

    Returns:
        ValidationResult with warnings and suggestions
    """
    if not email:
        return ValidationResult(is_valid=True, warnings=[], suggestions=[])

    warnings = []
    suggestions = []

    # Basic format check
    if "@" not in email:
        return ValidationResult(
            is_valid=False, warnings=["Invalid email format: missing @"], suggestions=[]
        )

    # Check for spaces (common OCR error)
    if " " in email:
        warnings.append("Email contains spaces (possible OCR error)")
        suggestions.append(email.replace(" ", ""))

    # Check for double dots
    if ".." in email:
        warnings.append("Email contains consecutive dots")
        clean_email = re.sub(r"\.+", ".", email)
        if clean_email != email:
            suggestions.append(clean_email)

    # Split email
    try:
        local_part, domain = email.rsplit("@", 1)
    except ValueError:
        return ValidationResult(
            is_valid=False, warnings=["Invalid email format"], suggestions=[]
        )

    # Check for repeated characters (3+ in a row) in local part
    repeated = re.findall(r"(.)\1{2,}", local_part)
    if repeated:
        chars = "".join(set(repeated))
        warnings.append(f"Suspicious repeated characters in email: '{chars}'")
        # Suggest fixing repeated chars (reduce to 2)
        fixed_local = re.sub(r"(.)\1{2,}", r"\1\1", local_part)
        if fixed_local != local_part:
            suggestions.append(f"{fixed_local}@{domain}")

    # Common domain typos
    common_domains = {
        "gmail.com": [
            "gmial.com",
            "gmai.com",
            "gmailcom",
            "gmail.co",
            "gmaill.com",
            "gamil.com",
            "gmal.com",
            "gnail.com",
            "gemail.com",
            "g-mail.com",
        ],
        "hotmail.com": [
            "hotmai.com",
            "hotmal.com",
            "hotmial.com",
            "homail.com",
            "hotmailcom",
            "hotamil.com",
            "hotmail.co",
        ],
        "yahoo.com": [
            "yaho.com",
            "yahooo.com",
            "yahoo.co",
            "yahoocom",
            "yaoo.com",
            "yhaoo.com",
        ],
        "outlook.com": [
            "outlok.com",
            "outllook.com",
            "outlook.co",
            "outlookcom",
            "outloook.com",
        ],
        "icloud.com": [
            "iclould.com",
            "icoud.com",
            "icloud.co",
            "iclooud.com",
        ],
    }

    # Greek-specific domains
    greek_domains = {
        "cosmote.gr": ["cosmotte.gr", "cosmot.gr"],
        "vodafone.gr": ["vodafon.gr", "vodaphone.gr"],
        "otenet.gr": ["otene.gr", "otennet.gr"],
        "forthnet.gr": ["forthent.gr", "fortnet.gr"],
    }
    common_domains.update(greek_domains)

    domain_lower = domain.lower()

    # Check exact typo matches
    typo_found = False
    for correct, typos in common_domains.items():
        if domain_lower in typos:
            warnings.append(f"Possible domain typo: '{domain}' may be '{correct}'")
            suggestions.append(f"{local_part}@{correct}")
            typo_found = True
            break

    # Check similarity to common domains (if no exact typo match)
    if not typo_found and domain_lower not in common_domains:
        for correct in common_domains.keys():
            similarity = SequenceMatcher(None, domain_lower, correct).ratio()
            if 0.75 < similarity < 1.0:
                warnings.append(
                    f"Domain '{domain}' is similar to '{correct}' "
                    f"(similarity: {similarity:.0%})"
                )
                suggestions.append(f"{local_part}@{correct}")
                break

    # Determine validity
    # Invalid if there's a likely typo
    has_typo = any("typo" in w.lower() or "similar" in w.lower() for w in warnings)
    is_valid = not has_typo

    return ValidationResult(
        is_valid=is_valid, warnings=warnings, suggestions=suggestions
    )


def validate_phone(phone: str | None, country_code: str = "GR") -> ValidationResult:
    """
    Validate phone number format.

    For Greece (GR), accepts:
    - 69XXXXXXXX (mobile, 10 digits)
    - 2XXXXXXXXX (landline, 10 digits)
    - +30XXXXXXXXXX (with country code, 12 digits)
    - 003069XXXXXXXX (with prefix, 14 digits)

    Args:
        phone: Phone number to validate
        country_code: Country code (default: GR for Greece)

    Returns:
        ValidationResult with warnings and suggestions
    """
    if not phone:
        return ValidationResult(is_valid=True, warnings=[], suggestions=[])

    warnings = []
    suggestions = []

    # Normalize: remove spaces, dashes, parentheses, dots
    normalized = re.sub(r"[\s\-\(\)\.]", "", phone)

    if country_code == "GR":
        # Greek patterns
        gr_mobile = re.compile(r"^(\+30|0030)?69\d{8}$")
        gr_landline = re.compile(r"^(\+30|0030)?2\d{9}$")

        if gr_mobile.match(normalized) or gr_landline.match(normalized):
            return ValidationResult(is_valid=True, warnings=[], suggestions=[])

        # Check for common issues
        if normalized.startswith("69"):
            if len(normalized) < 10:
                warnings.append(
                    f"Greek mobile too short: {len(normalized)} digits (expected 10)"
                )
            elif len(normalized) > 10:
                warnings.append(
                    f"Greek mobile too long: {len(normalized)} digits (expected 10)"
                )
                # Suggest truncated version
                suggestions.append(normalized[:10])

        elif normalized.startswith("2"):
            if len(normalized) < 10:
                warnings.append(
                    f"Greek landline too short: {len(normalized)} digits (expected 10)"
                )
            elif len(normalized) > 10:
                warnings.append(
                    f"Greek landline too long: {len(normalized)} digits (expected 10)"
                )
                suggestions.append(normalized[:10])

        elif normalized.startswith("+30") or normalized.startswith("0030"):
            prefix_len = 3 if normalized.startswith("+30") else 4
            remaining = normalized[prefix_len:]

            if remaining.startswith("69"):
                expected_len = 10
                if len(remaining) != expected_len:
                    warnings.append(
                        f"Greek mobile with country code: "
                        f"got {len(remaining)} digits after prefix (expected {expected_len})"
                    )
            elif remaining.startswith("2"):
                expected_len = 10
                if len(remaining) != expected_len:
                    warnings.append(
                        f"Greek landline with country code: "
                        f"got {len(remaining)} digits after prefix (expected {expected_len})"
                    )
            else:
                warnings.append(
                    f"Greek phone after country code should start with 2 or 69, "
                    f"got '{remaining[:2]}'"
                )
        else:
            # Doesn't match any Greek pattern
            if normalized.isdigit():
                warnings.append(
                    f"Phone doesn't match Greek format "
                    f"(should start with 2, 69, +30, or 0030)"
                )
            else:
                warnings.append(f"Phone contains non-digit characters")

        # Check for repeated digits (possible typo)
        digit_only = re.sub(r"\D", "", normalized)
        repeated = re.findall(r"(\d)\1{4,}", digit_only)
        if repeated:
            warnings.append(
                f"Phone has suspicious repeated digits: {''.join(repeated)}"
            )

    # Determine validity
    is_valid = len(warnings) == 0

    return ValidationResult(
        is_valid=is_valid, warnings=warnings, suggestions=suggestions
    )


def validate_contact_info(
    email: str | None = None,
    phone: str | None = None,
    phone_secondary: str | None = None,
    email_secondary: str | None = None,
) -> dict[str, ValidationResult]:
    """
    Validate all contact information.

    Args:
        email: Primary email
        phone: Primary phone
        phone_secondary: Secondary phone
        email_secondary: Secondary email

    Returns:
        Dict with validation results for each field
    """
    results = {}

    if email:
        results["email"] = validate_email(email)

    if email_secondary:
        results["email_secondary"] = validate_email(email_secondary)

    if phone:
        results["phone"] = validate_phone(phone)

    if phone_secondary:
        results["phone_secondary"] = validate_phone(phone_secondary)

    return results
