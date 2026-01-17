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
    get_language_code,
    normalize_language_proficiency,
    normalize_skill_level,
)

logger = logging.getLogger(__name__)

# Prompt template location
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts" / "cv_parsing"
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
    MAX_TOKENS = 8000

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
        else:
            path = PROMPTS_DIR / f"{self.prompt_version}.txt"

        if path.exists():
            return path.read_text(encoding="utf-8")

        # Fallback to embedded prompt
        logger.warning(f"Prompt file not found: {path}, using embedded prompt")
        return self._get_embedded_prompt()

    def _get_embedded_prompt(self) -> str:
        """Get embedded fallback prompt."""
        return """You are an expert HR document parser specializing in Greek and English CVs.

TASK: Parse the provided CV text and extract structured information.

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
  "overall_confidence": 0.0-1.0
}

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

        # Call Claude with retries
        raw_json = None
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = await self.provider.complete(
                    LLMRequest(
                        prompt=prompt,
                        model=self.MODEL,
                        max_tokens=self.MAX_TOKENS,
                        temperature=0.0,
                    )
                )

                # Extract JSON from response
                raw_json = self._extract_json(response.content)

                if raw_json:
                    logger.info(
                        f"CV parsed successfully: "
                        f"tokens_in={response.input_tokens}, "
                        f"tokens_out={response.output_tokens}, "
                        f"latency={response.latency_ms:.0f}ms"
                    )
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
        # Try direct parse first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Extract from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object
        brace_match = re.search(r"\{[\s\S]*\}", response_text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

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

        return ParsedCV(
            personal=personal,
            education=education,
            experience=experience,
            skills=skills,
            languages=languages,
            certifications=certifications,
            driving_licenses=driving_licenses,
            software=software,
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
