"""
CV Parser using Claude Sonnet 4.5 for structured extraction.

Parses raw CV text into structured JSON matching the PostgreSQL v4.0 schema.
Supports Greek and English CVs with intelligent field detection.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from ..llm.provider import BedrockProvider, LLMRequest, ModelType
from .schema import (
    ParsedCertification,
    ParsedCV,
    ParsedDrivingLicense,
    ParsedEducation,
    ParsedExperience,
    ParsedLanguage,
    ParsedPersonal,
    ParsedSkill,
    ParsedSoftware,
    ParsedTraining,
    ParsedUnmatchedData,
    get_language_code,
    normalize_language_proficiency,
    normalize_skill_level,
)
from .validators import validate_email, validate_phone

logger = logging.getLogger(__name__)

# Prompt template location - use package-relative path for Lambda compatibility
PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "cv_parsing"
DEFAULT_PROMPT_VERSION = "v1.0.0"


class CVParser:
    """
    CV Parser using Claude Sonnet 4.5 for structured extraction.

    Extracts structured data from raw CV text including:
    - Personal information (name, contact, address)
    - Education history
    - Work experience
    - Skills and competencies
    - Languages
    - Certifications
    - Driving licenses

    Example:
        parser = CVParser()
        parsed_cv = await parser.parse(cv_text, correlation_id="xxx")
    """

    MODEL = ModelType.CLAUDE_SONNET
    MAX_RETRIES = 2
    MAX_TOKENS = 64000  # Max tokens for Claude 4.5 Sonnet output

    def __init__(
        self,
        region: str = "eu-north-1",
        prompt_version: str = DEFAULT_PROMPT_VERSION,
    ):
        """
        Initialize CV parser.

        Args:
            region: AWS region for Bedrock
            prompt_version: Prompt template version to use
        """
        self.provider = BedrockProvider(region=region)
        self.prompt_version = prompt_version
        self._prompt_template: str | None = None

    @property
    def prompt_template(self) -> str:
        """Load prompt template lazily."""
        if self._prompt_template is None:
            self._prompt_template = self._load_prompt()
        return self._prompt_template

    def _load_prompt(self) -> str:
        """
        Load prompt template from file.

        Returns:
            Prompt template string
        """
        # Check environment variable for prompt path
        prompt_path = os.environ.get("CV_PARSING_PROMPT_PATH")

        if prompt_path:
            path = Path(prompt_path)
            logger.info(f"Using prompt from env var: {path}")
        else:
            path = PROMPTS_DIR / f"{self.prompt_version}.txt"
            logger.info(f"Using prompt from package: {path}")

        logger.info(f"PROMPTS_DIR resolved to: {PROMPTS_DIR}")
        logger.info(f"Full prompt path: {path}, exists: {path.exists()}")

        # Always use embedded prompt for reliability (file prompt causes timeout)
        logger.info("Using embedded prompt for reliability")
        return self._get_embedded_prompt()

    def _get_embedded_prompt(self) -> str:
        """Get embedded fallback prompt."""
        return """You are an expert HR document parser specializing in Greek and English CVs.

TASK: Parse the provided CV text and extract ALL structured information.

CRITICAL EXTRACTION RULES (MUST FOLLOW):
=========================================
1. NEVER output "Unknown Company", "Unknown Institution", "Unknown Certification" or ANY "Unknown X" value
2. Extract text EXACTLY AS WRITTEN even if format is unusual
3. company_name: Use whatever text describes the employer (industry description counts as company name)
4. institution_name: Extract FULL name with abbreviations (e.g., "Ο.Ε.Ε.Κ. (ΙΕΚ)-Λάρισα")
5. certification_name: Extract FULL title including description
6. degree_title: Keep ORIGINAL Greek text, don't translate or simplify
7. address_city: ALWAYS extract city if present (e.g., "Λάρισα" from "Λάρισα 41223")
8. address_postal_code: ALWAYS extract postal code if present
9. WHEN IN DOUBT: Extract text as-is rather than omitting

SKILL EXTRACTION FROM JOB RESPONSIBILITIES (CRITICAL):
=======================================================
Extract skills from TWO sources:
1. Explicit "Skills" or "Δεξιότητες" sections → source_context: "skills_section"
2. Job responsibilities/descriptions → source_context: "experience"

HOW TO IDENTIFY SKILLS IN JOB DESCRIPTIONS:
- Look for SPECIFIC TASKS: actions the person performed (e.g., "Τιμολόγηση", "Welding", "Programming")
- Look for PROCESSES: named procedures they handled (e.g., "Μηνιαίο κλείσιμο", "Quality Control", "ΦΠΑ")
- Look for TECHNICAL TERMS: domain-specific vocabulary (e.g., "διπλογραφικά βιβλία", "CNC", "ERP")
- Look for TOOLS/METHODS: specific approaches used (e.g., "TIG welding", "Agile", "ISO audit")
- Look for REGULATIONS/STANDARDS: compliance areas (e.g., "Α.Π.Δ.", "GDPR", "ISO 9001")

EXTRACTION RULES:
- Extract the skill as a SHORT, SPECIFIC term (not full sentences)
- Greek skills: keep in Greek (e.g., "Τιμολόγηση", "Υπολογισμός ΦΠΑ")
- English skills: keep in English (e.g., "CNC Operation", "Quality Control")
- Set category: "technical" for job-specific skills, "soft" for interpersonal skills, "domain" for industry knowledge
- Avoid duplicates: if same skill appears in multiple jobs, include once
- Be COMPREHENSIVE: extract 10-20+ skills from detailed CVs

OUTPUT FORMAT: Return ONLY a valid JSON object with this exact structure:
{
  "personal": {
    "first_name": "string",
    "last_name": "string",
    "email": "string or null",
    "phone": "string or null",
    "date_of_birth": "YYYY-MM-DD or null",
    "gender": "male|female|other|unknown",
    "marital_status": "single|married|divorced|widowed|unknown",
    "nationality": "string or null",
    "address_street": "string or null",
    "address_city": "string or null",
    "address_region": "string or null",
    "address_postal_code": "string or null",
    "address_country": "Greece",
    "military_status": "completed|exempt|pending|not_applicable|unknown",
    "linkedin_url": "string or null",
    "confidence": 0.0-1.0
  },
  "education": [
    {
      "institution_name": "string",
      "institution_city": "string or null",
      "institution_country": "string or null",
      "degree_level": "primary|secondary|lyceum|vocational|iek|tei|bachelor|master|doctorate|other",
      "degree_title": "string or null",
      "field_of_study": "engineering_mechanical|engineering_electrical|computer_science|business_administration|other|...",
      "specialization": "string or null",
      "start_date": "YYYY-MM-DD or null",
      "end_date": "YYYY-MM-DD or null",
      "is_current": false,
      "graduation_year": 2020,
      "grade_value": "string or null",
      "confidence": 0.0-1.0
    }
  ],
  "experience": [
    {
      "company_name": "string",
      "job_title": "string",
      "company_city": "string or null",
      "company_country": "string or null",
      "department": "string or null",
      "employment_type": "full_time|part_time|contract|temporary|internship|seasonal|freelance",
      "start_date": "YYYY-MM-DD or null",
      "end_date": "YYYY-MM-DD or null",
      "is_current": false,
      "description": "string or null",
      "responsibilities": ["string"],
      "achievements": ["string"],
      "technologies_used": ["string"],
      "confidence": 0.0-1.0
    }
  ],
  "skills": [
    {
      "name": "string",
      "level": "beginner|intermediate|advanced|expert|master",
      "years_of_experience": 2.5,
      "category": "technical|soft|domain",
      "source_context": "skills_section|experience|education|certifications",
      "confidence": 0.0-1.0
    }
  ],
  "languages": [
    {
      "language_name": "string",
      "language_code": "el|en|de|fr|...",
      "proficiency_level": "A1|A2|B1|B2|C1|C2|native|unknown",
      "is_native": false,
      "certification_name": "string or null",
      "confidence": 0.0-1.0
    }
  ],
  "certifications": [
    {
      "certification_name": "string",
      "issuing_organization": "string or null",
      "issue_date": "YYYY-MM-DD or null",
      "expiry_date": "YYYY-MM-DD or null",
      "credential_id": "string or null",
      "confidence": 0.0-1.0
    }
  ],
  "driving_licenses": [
    {
      "license_category": "A|A1|A2|AM|B|B1|BE|C|C1|CE|D|D1|forklift|crane|other",
      "issue_date": "YYYY-MM-DD or null",
      "confidence": 0.0-1.0
    }
  ],
  "software": [
    {
      "name": "string",
      "category": "erp|cad|office|database|other",
      "proficiency_level": "beginner|intermediate|advanced|expert",
      "confidence": 0.0-1.0
    }
  ],
  "training": [
    {
      "training_name": "string (name of training/seminar)",
      "provider_name": "string or null",
      "training_type": "seminar|workshop|course|conference|other",
      "category": "accounting|legal|hr|it|management|safety|technical|other",
      "duration_hours": "number or null",
      "completion_date": "YYYY-MM-DD or null",
      "raw_text": "original text",
      "confidence": 0.0-1.0
    }
  ],
  "overall_confidence": 0.0-1.0
}

IMPORTANT: Distinguish between CERTIFICATIONS (formal qualifications like degrees, licenses, ISO auditor) and TRAINING (seminars, workshops like "Σεμινάρια", "Οι Αλλαγές στην Εργατική Νομοθεσία").

RULES:
1. Extract ALL information found in the CV
2. For Greek text: normalize names by removing accents internally but preserve original in output
3. Date format: YYYY-MM-DD (if only year known, use YYYY-01-01)
4. Greek skill levels: αρχάριος→beginner, μέτριο→intermediate, καλό→advanced, άριστο→expert
5. Greek language levels: βασικό→A2, μέτριο→B1, καλό→B2, πολύ καλό→C1, άριστο→C2, μητρική→native
6. Set confidence scores (0.0-1.0) based on clarity of information
7. If information is unclear or missing, use null
8. Military status: common in Greek CVs (στρατιωτικές υποχρεώσεις)
9. Look for LinkedIn URLs in contact section
10. SKILLS FROM EXPERIENCE: Parse job responsibilities to extract specific competencies as skills with source_context="experience"
11. Avoid duplicate skills - if same skill appears in multiple jobs, include once with highest confidence

CV TEXT TO PARSE:
"""

    async def parse(
        self,
        cv_text: str,
        correlation_id: str | None = None,
    ) -> ParsedCV:
        """
        Parse CV text into structured data.

        Args:
            cv_text: Raw CV text to parse
            correlation_id: Tracking ID for logging

        Returns:
            ParsedCV with extracted information
        """
        logger.info(f"Parsing CV, correlation_id={correlation_id}, chars={len(cv_text)}")

        # Build prompt
        prompt = f"{self.prompt_template}\n{cv_text}"
        logger.info(f"Prompt built: {len(prompt)} chars total")

        # Call Claude with retries (only retry on network/API errors, not JSON parse failures)
        raw_json = None
        last_error = None
        response_content = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                logger.info(f"Calling Claude API, attempt {attempt + 1}/{self.MAX_RETRIES + 1}")
                response = await self.provider.complete(
                    LLMRequest(
                        prompt=prompt,
                        model=self.MODEL,
                        max_tokens=self.MAX_TOKENS,
                        temperature=0.0,
                    )
                )
                logger.info(
                    f"Claude API response received: "
                    f"tokens_in={response.input_tokens}, "
                    f"tokens_out={response.output_tokens}, "
                    f"latency={response.latency_ms:.0f}ms"
                )
                response_content = response.content

                # Extract JSON from response
                raw_json = self._extract_json(response.content)

                if raw_json:
                    logger.info("CV parsed successfully")
                    break
                else:
                    # JSON extraction failed - don't retry, same prompt gives same result
                    logger.error("JSON extraction failed, not retrying (would produce same result)")
                    break

            except Exception as e:
                last_error = e
                logger.warning(f"Parse attempt {attempt + 1} failed: {e}")

        if not raw_json:
            # Return minimal parsed CV on failure
            logger.error(f"Failed to parse CV after {self.MAX_RETRIES + 1} attempts")
            return ParsedCV(
                personal=ParsedPersonal(first_name="", last_name=""),
                correlation_id=correlation_id,
                raw_cv_text=cv_text,
                overall_confidence=0.0,
                parsing_errors=[str(last_error) if last_error else "Failed to extract JSON"],
            )

        # Build ParsedCV from JSON
        parsed = self._build_parsed_cv(raw_json, correlation_id, cv_text)
        parsed.model_used = self.MODEL.value

        # Calculate completeness
        parsed.calculate_completeness()

        return parsed

    def _extract_json(self, response_text: str) -> dict[str, Any] | None:
        """
        Extract JSON object from Claude response.

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed JSON dict or None
        """
        logger.info(f"Extracting JSON from response ({len(response_text)} chars)")

        # Try direct parse first
        try:
            result = json.loads(response_text)
            logger.info("JSON parsed directly")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Direct parse failed: {e}")

        # Extract from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                logger.info("JSON extracted from markdown block")
                return result
            except json.JSONDecodeError as e:
                logger.debug(f"Markdown block parse failed: {e}")

        # Try to find JSON object
        brace_match = re.search(r"\{[\s\S]*\}", response_text)
        if brace_match:
            try:
                result = json.loads(brace_match.group(0))
                logger.info("JSON extracted from brace match")
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"Brace match parse failed: {e}")

        # Log failure with response preview
        preview = response_text[:500] if len(response_text) > 500 else response_text
        logger.error(f"Failed to extract JSON. Response preview: {preview}")
        return None

    def _build_parsed_cv(
        self,
        data: dict[str, Any],
        correlation_id: str | None,
        cv_text: str,
    ) -> ParsedCV:
        """
        Build ParsedCV from extracted JSON.

        Args:
            data: JSON data from Claude
            correlation_id: Tracking ID
            cv_text: Original CV text

        Returns:
            ParsedCV instance
        """
        warnings = []

        # Parse personal info
        personal_data = data.get("personal", {})
        personal = ParsedPersonal(
            first_name=personal_data.get("first_name", ""),
            last_name=personal_data.get("last_name", ""),
            email=personal_data.get("email"),
            email_secondary=personal_data.get("email_secondary"),
            phone=personal_data.get("phone"),
            phone_secondary=personal_data.get("phone_secondary"),
            address_city=personal_data.get("address_city"),
            address_region=personal_data.get("address_region"),
            address_postal_code=personal_data.get("address_postal_code"),
            address_country=personal_data.get("address_country", "Greece"),
            address_street=personal_data.get("address_street"),
            nationality=personal_data.get("nationality"),
            linkedin_url=personal_data.get("linkedin_url"),
            confidence=personal_data.get("confidence", 0.0),
        )

        # Parse date_of_birth
        if personal_data.get("date_of_birth"):
            try:
                from datetime import date

                personal.date_of_birth = date.fromisoformat(personal_data["date_of_birth"])
            except ValueError:
                warnings.append(f"Invalid date_of_birth: {personal_data['date_of_birth']}")

        # Parse military status
        if personal_data.get("military_status"):
            from .schema import MilitaryStatus

            try:
                personal.military_status = MilitaryStatus(personal_data["military_status"])
            except ValueError:
                personal.military_status = MilitaryStatus.UNKNOWN

        # Task 1.7: Validate email and phone
        email_validation = validate_email(personal.email)
        personal.email_validated = True
        if email_validation.warnings:
            personal.email_warnings = email_validation.warnings
            personal.email_suggestions = email_validation.suggestions
            for warning in email_validation.warnings:
                warnings.append(f"Email validation: {warning}")
            logger.warning(
                f"Email validation warnings for '{personal.email}': {email_validation.warnings}"
            )

        phone_validation = validate_phone(personal.phone)
        personal.phone_validated = True
        if phone_validation.warnings:
            personal.phone_warnings = phone_validation.warnings
            personal.phone_suggestions = phone_validation.suggestions
            for warning in phone_validation.warnings:
                warnings.append(f"Phone validation: {warning}")
            logger.warning(
                f"Phone validation warnings for '{personal.phone}': {phone_validation.warnings}"
            )

        # Parse education
        education = []
        for edu_data in data.get("education", []):
            edu = self._parse_education(edu_data, warnings)
            if edu:
                education.append(edu)

        # Parse experience
        experience = []
        for exp_data in data.get("experience", []):
            exp = self._parse_experience(exp_data, warnings)
            if exp:
                experience.append(exp)

        # Parse skills
        skills = []
        for skill_data in data.get("skills", []):
            skill = self._parse_skill(skill_data, warnings)
            if skill:
                skills.append(skill)

        # Parse languages
        languages = []
        for lang_data in data.get("languages", []):
            lang = self._parse_language(lang_data, warnings)
            if lang:
                languages.append(lang)

        # Parse certifications
        certifications = []
        for cert_data in data.get("certifications", []):
            cert = self._parse_certification(cert_data, warnings)
            if cert:
                certifications.append(cert)

        # Post-process: Reclassify seminars from certifications to training
        certifications, reclassified_training = self._reclassify_certifications_to_training(
            certifications, cv_text
        )

        # Parse driving licenses
        driving_licenses = []
        for dl_data in data.get("driving_licenses", []):
            dl = self._parse_driving_license(dl_data, warnings)
            if dl:
                driving_licenses.append(dl)

        # Parse software
        software = []
        for sw_data in data.get("software", []):
            sw = self._parse_software(sw_data, warnings)
            if sw:
                software.append(sw)

        # Parse training/seminars from LLM output
        training = []
        for tr_data in data.get("training", []):
            tr = self._parse_training(tr_data)
            if tr:
                training.append(tr)

        # Merge LLM-detected training with reclassified training
        training.extend(reclassified_training)

        if training:
            logger.info(
                f"Total training records: {len(training)} "
                f"(LLM: {len(training) - len(reclassified_training)}, "
                f"reclassified: {len(reclassified_training)})"
            )

        # Parse unmatched data (zero data loss policy)
        unmatched_data = []
        for unmatched_item in data.get("unmatched_data", []):
            unmatched = self._parse_unmatched_data(unmatched_item)
            if unmatched:
                unmatched_data.append(unmatched)

        if unmatched_data:
            logger.info(f"Captured {len(unmatched_data)} unmatched CV data items")

        return ParsedCV(
            personal=personal,
            education=education,
            experience=experience,
            skills=skills,
            languages=languages,
            certifications=certifications,
            driving_licenses=driving_licenses,
            software=software,
            training=training,
            unmatched_data=unmatched_data,
            correlation_id=correlation_id,
            raw_cv_text=cv_text,
            raw_json=data,
            overall_confidence=data.get("overall_confidence", 0.0),
            warnings=warnings,
        )

    def _parse_education(
        self,
        data: dict[str, Any],
        warnings: list[str],
    ) -> ParsedEducation | None:
        """Parse education entry."""
        if not data.get("institution_name"):
            return None

        from datetime import date

        from .schema import EducationField, EducationLevel

        edu = ParsedEducation(
            institution_name=data["institution_name"],
            institution_city=data.get("institution_city"),
            institution_country=data.get("institution_country"),
            degree_title=data.get("degree_title"),
            specialization=data.get("specialization"),
            graduation_year=data.get("graduation_year"),
            grade_value=data.get("grade_value"),
            is_current=data.get("is_current", False),
            confidence=data.get("confidence", 0.0),
        )

        # Parse degree level
        if data.get("degree_level"):
            try:
                edu.degree_level = EducationLevel(data["degree_level"])
            except ValueError:
                warnings.append(f"Unknown degree_level: {data['degree_level']}")

        # Parse field of study
        if data.get("field_of_study"):
            try:
                edu.field_of_study = EducationField(data["field_of_study"])
            except ValueError:
                edu.field_of_study_detail = data["field_of_study"]

        # Parse dates
        if data.get("start_date"):
            try:
                edu.start_date = date.fromisoformat(data["start_date"])
            except ValueError:
                warnings.append(f"Invalid education start_date: {data['start_date']}")

        if data.get("end_date"):
            try:
                edu.end_date = date.fromisoformat(data["end_date"])
            except ValueError:
                warnings.append(f"Invalid education end_date: {data['end_date']}")

        return edu

    def _parse_experience(
        self,
        data: dict[str, Any],
        warnings: list[str],
    ) -> ParsedExperience | None:
        """Parse experience entry."""
        if not data.get("company_name") or not data.get("job_title"):
            return None

        from datetime import date

        from .schema import EmploymentType

        exp = ParsedExperience(
            company_name=data["company_name"],
            job_title=data["job_title"],
            company_city=data.get("company_city"),
            company_country=data.get("company_country"),
            department=data.get("department"),
            description=data.get("description"),
            responsibilities=data.get("responsibilities", []),
            achievements=data.get("achievements", []),
            technologies_used=data.get("technologies_used", []),
            is_current=data.get("is_current", False),
            confidence=data.get("confidence", 0.0),
        )

        # Parse employment type
        if data.get("employment_type"):
            try:
                exp.employment_type = EmploymentType(data["employment_type"])
            except ValueError:
                warnings.append(f"Unknown employment_type: {data['employment_type']}")

        # Parse dates
        if data.get("start_date"):
            try:
                exp.start_date = date.fromisoformat(data["start_date"])
            except ValueError:
                warnings.append(f"Invalid experience start_date: {data['start_date']}")

        if data.get("end_date"):
            try:
                exp.end_date = date.fromisoformat(data["end_date"])
            except ValueError:
                warnings.append(f"Invalid experience end_date: {data['end_date']}")

        # Calculate duration
        if exp.start_date:
            from datetime import date as date_type

            end = exp.end_date if exp.end_date else date_type.today()
            exp.duration_months = (end.year - exp.start_date.year) * 12 + (
                end.month - exp.start_date.month
            )

        return exp

    def _parse_skill(
        self,
        data: dict[str, Any],
        warnings: list[str],
    ) -> ParsedSkill | None:
        """Parse skill entry."""
        if not data.get("name"):
            return None

        skill = ParsedSkill(
            name=data["name"],
            category=data.get("category"),
            years_of_experience=data.get("years_of_experience"),
            confidence=data.get("confidence", 0.0),
        )

        # Parse skill level
        if data.get("level"):
            skill.level = normalize_skill_level(data["level"])
            if skill.level is None:
                warnings.append(f"Unknown skill level: {data['level']}")

        return skill

    def _parse_language(
        self,
        data: dict[str, Any],
        warnings: list[str],
    ) -> ParsedLanguage | None:
        """Parse language entry."""
        if not data.get("language_name"):
            return None

        lang = ParsedLanguage(
            language_name=data["language_name"],
            language_code=data.get("language_code") or get_language_code(data["language_name"]),
            is_native=data.get("is_native", False),
            certification_name=data.get("certification_name"),
            certification_score=data.get("certification_score"),
            confidence=data.get("confidence", 0.0),
        )

        # Parse proficiency
        if data.get("proficiency_level"):
            lang.proficiency_level = normalize_language_proficiency(data["proficiency_level"])

        if lang.is_native:
            from .schema import LanguageProficiency

            lang.proficiency_level = LanguageProficiency.NATIVE

        return lang

    def _parse_certification(
        self,
        data: dict[str, Any],
        warnings: list[str],
    ) -> ParsedCertification | None:
        """Parse certification entry."""
        if not data.get("certification_name"):
            return None

        from datetime import date

        cert = ParsedCertification(
            certification_name=data["certification_name"],
            issuing_organization=data.get("issuing_organization"),
            credential_id=data.get("credential_id"),
            credential_url=data.get("credential_url"),
            confidence=data.get("confidence", 0.0),
        )

        # Parse dates
        if data.get("issue_date"):
            try:
                cert.issue_date = date.fromisoformat(data["issue_date"])
            except ValueError:
                warnings.append(f"Invalid cert issue_date: {data['issue_date']}")

        if data.get("expiry_date"):
            try:
                cert.expiry_date = date.fromisoformat(data["expiry_date"])
            except ValueError:
                warnings.append(f"Invalid cert expiry_date: {data['expiry_date']}")

        return cert

    def _parse_driving_license(
        self,
        data: dict[str, Any],
        warnings: list[str],
    ) -> ParsedDrivingLicense | None:
        """Parse driving license entry."""
        if not data.get("license_category"):
            return None

        from datetime import date

        from .schema import DrivingLicenseCategory

        try:
            category = DrivingLicenseCategory(data["license_category"])
        except ValueError:
            warnings.append(f"Unknown license_category: {data['license_category']}")
            return None

        dl = ParsedDrivingLicense(
            license_category=category,
            issuing_country=data.get("issuing_country", "Greece"),
            license_number=data.get("license_number"),
            confidence=data.get("confidence", 0.0),
        )

        # Parse dates
        if data.get("issue_date"):
            try:
                dl.issue_date = date.fromisoformat(data["issue_date"])
            except ValueError:
                warnings.append(f"Invalid license issue_date: {data['issue_date']}")

        if data.get("expiry_date"):
            try:
                dl.expiry_date = date.fromisoformat(data["expiry_date"])
            except ValueError:
                warnings.append(f"Invalid license expiry_date: {data['expiry_date']}")

        return dl

    def _parse_software(
        self,
        data: dict[str, Any],
        warnings: list[str],
    ) -> ParsedSoftware | None:
        """Parse software entry."""
        if not data.get("name"):
            return None

        sw = ParsedSoftware(
            name=data["name"],
            vendor=data.get("vendor"),
            category=data.get("category"),
            version_used=data.get("version_used"),
            years_of_experience=data.get("years_of_experience"),
            confidence=data.get("confidence", 0.0),
        )

        # Parse proficiency level
        if data.get("proficiency_level"):
            sw.proficiency_level = normalize_skill_level(data["proficiency_level"])

        return sw

    def _parse_unmatched_data(
        self,
        data: dict[str, Any],
    ) -> ParsedUnmatchedData | None:
        """
        Parse unmatched CV data item.

        This handles data that the LLM could not map to existing fields,
        implementing the zero data loss policy.

        Args:
            data: Unmatched data item from LLM response

        Returns:
            ParsedUnmatchedData or None if invalid
        """
        # Both field_name and field_value are required
        if not data.get("field_name") or not data.get("field_value"):
            return None

        return ParsedUnmatchedData(
            suggested_section=data.get("suggested_section", "other"),
            field_name=data["field_name"],
            field_value=str(data["field_value"]),
            source_text=data.get("source_text"),
            extraction_confidence=data.get("extraction_confidence", 0.0),
            llm_reasoning=data.get("llm_reasoning"),
        )

    def _parse_training(
        self,
        data: dict[str, Any],
    ) -> ParsedTraining | None:
        """
        Parse training/seminar data.

        Args:
            data: Training data from LLM response

        Returns:
            ParsedTraining or None if invalid
        """
        # training_name is required
        if not data.get("training_name"):
            return None

        return ParsedTraining(
            training_name=data["training_name"],
            provider_name=data.get("provider_name"),
            provider_type=data.get("provider_type"),
            training_type=data.get("training_type", "seminar"),
            category=data.get("category"),
            duration_hours=data.get("duration_hours"),
            duration_days=data.get("duration_days"),
            completion_date=data.get("completion_date"),
            start_date=data.get("start_date"),
            description=data.get("description"),
            skills_gained=data.get("skills_gained", []),
            certificate_received=data.get("certificate_received", False),
            raw_text=data.get("raw_text"),
            confidence=data.get("confidence", 0.0),
        )

    def _reclassify_certifications_to_training(
        self,
        certifications: list[ParsedCertification],
        raw_cv_text: str | None = None,
    ) -> tuple[list[ParsedCertification], list[ParsedTraining]]:
        """
        Post-process certifications to detect and reclassify training/seminars.

        The LLM sometimes puts seminars (Σεμινάρια) in certifications instead of training.
        This function detects training-like items based on markers and reclassifies them.

        Markers for training:
        - Duration mentions: "Διάρκειας X ωρών" (Duration X hours)
        - Section context: "Σεμινάρια" section in raw CV text
        - Organizer type: "Επιμελητήριο", "Εργαστήριο" (professional bodies)
        - Topic patterns: legal updates, best practices, workshops

        Args:
            certifications: List of parsed certifications
            raw_cv_text: Original CV text for context detection

        Returns:
            Tuple of (filtered_certifications, detected_training)
        """
        # Patterns that indicate training/seminars
        training_patterns = [
            r"διάρκει(?:ας|α)",  # Duration mentions
            r"\d+\s*ωρ(?:ών|ες|ών)",  # X hours
            r"σεμιν[αά]ρι",  # Seminar
            r"workshop",
            r"βέλτιστ(?:ες|ων)\s*πρακτικ",  # Best practices
            r"αλλαγ(?:ές|ών)\s*στ(?:ην|ις|ον|ο)",  # Changes in (legal updates)
            r"πρόσφατ(?:ες|ων)\s*αλλαγ",  # Recent changes
            r"εκπαιδευτικ(?:ό|ά)\s*πρόγραμμα",  # Educational program
            r"επιμόρφωσ[ηι]",  # Continuing education
        ]

        # Organizations that typically provide training (not certifications)
        training_orgs = [
            "επιμελητήριο",
            "οικονομικό επιμελητήριο",
            "εργαστήριο",
            "ινστιτούτο.*διοίκησης",
            "κέντρο.*εκπαίδευσης",
            "τμήμα.*εκπαίδευσης",
        ]

        # Check if CV has explicit Σεμινάρια section
        has_seminars_section = False
        if raw_cv_text:
            has_seminars_section = bool(
                re.search(r"(?:^|\n)\s*σεμιν[αά]ρια\s*(?:\n|$)", raw_cv_text, re.IGNORECASE)
            )

        filtered_certs = []
        detected_training = []

        for cert in certifications:
            is_training = False
            training_type = "seminar"
            category = None

            cert_name_lower = (cert.certification_name or "").lower()
            org_lower = (cert.issuing_organization or "").lower()
            combined_text = f"{cert_name_lower} {org_lower}"

            # Check training patterns in certification name
            for pattern in training_patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    is_training = True
                    break

            # Check if organization is a typical training provider
            if not is_training:
                for org_pattern in training_orgs:
                    if re.search(org_pattern, org_lower, re.IGNORECASE):
                        is_training = True
                        break

            # If CV has Σεμινάρια section and cert matches items there, it's training
            if not is_training and has_seminars_section and raw_cv_text:
                # Check if cert name appears in Σεμινάρια section
                seminars_match = re.search(
                    r"σεμιν[αά]ρια\s*(.*?)(?:(?:^|\n)\s*[α-ωά-ώ]+\s*(?:\n|$)|$)",
                    raw_cv_text,
                    re.IGNORECASE | re.DOTALL,
                )
                if seminars_match:
                    seminars_section = seminars_match.group(1).lower()
                    # Check if cert name keywords appear in seminars section
                    cert_keywords = cert_name_lower.split()[:3]  # First 3 words
                    if any(kw in seminars_section for kw in cert_keywords if len(kw) > 3):
                        is_training = True

            if is_training:
                # Detect category based on content
                if any(
                    kw in cert_name_lower
                    for kw in ["νομοθεσία", "νομικ", "νόμ.", "ν."]
                ):
                    category = "legal"
                elif any(
                    kw in cert_name_lower
                    for kw in ["λογιστ", "κοστολόγ", "φορολογ", "οικονομικ"]
                ):
                    category = "accounting"
                elif any(
                    kw in cert_name_lower
                    for kw in ["ανθρώπινου δυναμικού", "hr", "διοίκηση προσωπικού"]
                ):
                    category = "hr"
                elif any(kw in cert_name_lower for kw in ["πληροφορικ", "it", "software"]):
                    category = "it"
                elif any(kw in cert_name_lower for kw in ["ασφάλεια", "safety"]):
                    category = "safety"
                elif any(kw in cert_name_lower for kw in ["διοίκηση", "management"]):
                    category = "management"

                # Extract duration if mentioned
                duration_hours = None
                duration_match = re.search(r"(\d+)\s*ωρ(?:ών|ες)", combined_text)
                if duration_match:
                    duration_hours = int(duration_match.group(1))

                # Create training record
                training = ParsedTraining(
                    training_name=cert.certification_name,
                    provider_name=cert.issuing_organization,
                    provider_type="professional_body" if "επιμελητήριο" in org_lower else "other",
                    training_type=training_type,
                    category=category,
                    duration_hours=duration_hours,
                    completion_date=cert.issue_date.isoformat() if cert.issue_date else None,
                    certificate_received=True,  # They listed it, so probably got attendance cert
                    raw_text=cert.raw_text,
                    confidence=cert.confidence,
                )
                detected_training.append(training)

                logger.info(
                    f"Reclassified certification to training: '{cert.certification_name}' "
                    f"(category: {category}, duration: {duration_hours}h)"
                )
            else:
                filtered_certs.append(cert)

        if detected_training:
            logger.info(
                f"Post-processing: Reclassified {len(detected_training)} certifications "
                f"to training/seminars"
            )

        return filtered_certs, detected_training


# Convenience function for simple usage
async def parse_cv(
    cv_text: str,
    correlation_id: str | None = None,
    region: str = "eu-north-1",
) -> ParsedCV:
    """
    Parse CV text into structured data.

    Args:
        cv_text: Raw CV text to parse
        correlation_id: Tracking ID for logging
        region: AWS region for Bedrock

    Returns:
        ParsedCV with extracted information
    """
    parser = CVParser(region=region)
    return await parser.parse(cv_text, correlation_id)
