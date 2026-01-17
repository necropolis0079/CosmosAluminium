"""
Pydantic schemas for parsed CV data.

These models match the PostgreSQL v4.0 schema defined in docs/03-DATABASE-SCHEMA.md.
They are used to validate and structure the output from Claude CV parsing.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any
from uuid import UUID


class EmploymentStatus(str, Enum):
    """Employment status values matching PostgreSQL enum."""

    EMPLOYED = "employed"
    UNEMPLOYED = "unemployed"
    SELF_EMPLOYED = "self_employed"
    STUDENT = "student"
    RETIRED = "retired"
    UNKNOWN = "unknown"


class AvailabilityStatus(str, Enum):
    """Availability status values."""

    IMMEDIATE = "immediate"
    ONE_WEEK = "one_week"
    TWO_WEEKS = "two_weeks"
    ONE_MONTH = "one_month"
    THREE_MONTHS = "three_months"
    NOT_AVAILABLE = "not_available"
    UNKNOWN = "unknown"


class MilitaryStatus(str, Enum):
    """Military status (Greece-specific)."""

    COMPLETED = "completed"
    EXEMPT = "exempt"
    PENDING = "pending"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class Gender(str, Enum):
    """Gender values."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"
    UNKNOWN = "unknown"


class MaritalStatus(str, Enum):
    """Marital status values."""

    SINGLE = "single"
    MARRIED = "married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"
    CIVIL_PARTNERSHIP = "civil_partnership"
    UNKNOWN = "unknown"


class EducationLevel(str, Enum):
    """Education level values."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    LYCEUM = "lyceum"
    VOCATIONAL = "vocational"
    IEK = "iek"
    TEI = "tei"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"
    POSTDOC = "postdoc"
    PROFESSIONAL_CERT = "professional_cert"
    OTHER = "other"


class EducationField(str, Enum):
    """Education field values."""

    ENGINEERING_MECHANICAL = "engineering_mechanical"
    ENGINEERING_ELECTRICAL = "engineering_electrical"
    ENGINEERING_CIVIL = "engineering_civil"
    ENGINEERING_CHEMICAL = "engineering_chemical"
    ENGINEERING_INDUSTRIAL = "engineering_industrial"
    ENGINEERING_COMPUTER = "engineering_computer"
    ENGINEERING_OTHER = "engineering_other"
    COMPUTER_SCIENCE = "computer_science"
    INFORMATION_TECHNOLOGY = "information_technology"
    BUSINESS_ADMINISTRATION = "business_administration"
    ECONOMICS = "economics"
    FINANCE = "finance"
    ACCOUNTING = "accounting"
    MARKETING = "marketing"
    HUMAN_RESOURCES = "human_resources"
    LAW = "law"
    CHEMISTRY = "chemistry"
    PHYSICS = "physics"
    MATHEMATICS = "mathematics"
    BIOLOGY = "biology"
    ENVIRONMENTAL_SCIENCE = "environmental_science"
    AGRICULTURE = "agriculture"
    MEDICINE = "medicine"
    NURSING = "nursing"
    PSYCHOLOGY = "psychology"
    SOCIOLOGY = "sociology"
    LANGUAGES = "languages"
    ARTS = "arts"
    ARCHITECTURE = "architecture"
    OTHER = "other"


class SkillLevel(str, Enum):
    """Skill proficiency level."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class LanguageProficiency(str, Enum):
    """Language proficiency (CEFR)."""

    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"
    NATIVE = "native"
    UNKNOWN = "unknown"


class EmploymentType(str, Enum):
    """Employment type values."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    SEASONAL = "seasonal"
    FREELANCE = "freelance"


class DrivingLicenseCategory(str, Enum):
    """Driving license categories."""

    A = "A"
    A1 = "A1"
    A2 = "A2"
    AM = "AM"
    B = "B"
    B1 = "B1"
    BE = "BE"
    C = "C"
    C1 = "C1"
    CE = "CE"
    C1E = "C1E"
    D = "D"
    D1 = "D1"
    DE = "DE"
    D1E = "D1E"
    FORKLIFT = "forklift"
    CRANE = "crane"
    OTHER = "other"


@dataclass
class ParsedPersonal:
    """Personal information extracted from CV."""

    first_name: str
    last_name: str
    first_name_normalized: str | None = None
    last_name_normalized: str | None = None
    email: str | None = None
    email_secondary: str | None = None
    phone: str | None = None
    phone_secondary: str | None = None
    date_of_birth: date | None = None
    gender: Gender = Gender.UNKNOWN
    marital_status: MaritalStatus = MaritalStatus.UNKNOWN
    nationality: str | None = None
    address_street: str | None = None
    address_city: str | None = None
    address_region: str | None = None
    address_postal_code: str | None = None
    address_country: str = "Greece"
    employment_status: EmploymentStatus = EmploymentStatus.UNKNOWN
    availability_status: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    availability_date: date | None = None
    military_status: MilitaryStatus = MilitaryStatus.UNKNOWN
    willing_to_relocate: bool = False
    relocation_regions: list[str] = field(default_factory=list)
    expected_salary_min: float | None = None
    expected_salary_max: float | None = None
    salary_currency: str = "EUR"
    linkedin_url: str | None = None
    photo_url: str | None = None
    confidence: float = 0.0


@dataclass
class ParsedEducation:
    """Education entry extracted from CV."""

    institution_name: str
    institution_name_normalized: str | None = None
    institution_type: str | None = None
    institution_country: str | None = None
    institution_city: str | None = None
    degree_level: EducationLevel | None = None
    degree_title: str | None = None
    degree_title_normalized: str | None = None
    field_of_study: EducationField | None = None
    field_of_study_detail: str | None = None
    specialization: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    graduation_year: int | None = None
    grade_value: str | None = None
    grade_scale: str | None = None
    thesis_title: str | None = None
    honors: str | None = None
    raw_text: str | None = None
    confidence: float = 0.0


@dataclass
class ParsedExperience:
    """Work experience entry extracted from CV."""

    company_name: str
    job_title: str
    company_name_normalized: str | None = None
    job_title_normalized: str | None = None
    company_industry: str | None = None
    company_size: str | None = None
    company_country: str | None = None
    company_city: str | None = None
    role_id: UUID | None = None
    department: str | None = None
    employment_type: EmploymentType | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    duration_months: int | None = None
    description: str | None = None
    responsibilities: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)
    technologies_used: list[str] = field(default_factory=list)
    team_size: int | None = None
    reports_to: str | None = None
    raw_text: str | None = None
    confidence: float = 0.0


@dataclass
class ParsedSkill:
    """Skill entry extracted from CV."""

    name: str
    name_normalized: str | None = None
    skill_id: UUID | None = None
    canonical_id: str | None = None
    category: str | None = None
    level: SkillLevel | None = None
    years_of_experience: float | None = None
    last_used_year: int | None = None
    source_context: str | None = None
    confidence: float = 0.0


@dataclass
class ParsedLanguage:
    """Language entry extracted from CV."""

    language_code: str
    language_name: str
    proficiency_level: LanguageProficiency = LanguageProficiency.UNKNOWN
    reading_level: LanguageProficiency | None = None
    writing_level: LanguageProficiency | None = None
    speaking_level: LanguageProficiency | None = None
    listening_level: LanguageProficiency | None = None
    certification_name: str | None = None
    certification_score: str | None = None
    certification_date: date | None = None
    certification_expiry: date | None = None
    is_native: bool = False
    confidence: float = 0.0


@dataclass
class ParsedCertification:
    """Certification entry extracted from CV."""

    certification_name: str
    certification_name_normalized: str | None = None
    certification_id: UUID | None = None
    canonical_id: str | None = None
    issuing_organization: str | None = None
    issuing_organization_normalized: str | None = None
    credential_id: str | None = None
    credential_url: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    is_current: bool = True
    raw_text: str | None = None
    confidence: float = 0.0


@dataclass
class ParsedDrivingLicense:
    """Driving license entry extracted from CV."""

    license_category: DrivingLicenseCategory
    issue_date: date | None = None
    expiry_date: date | None = None
    issuing_country: str = "Greece"
    license_number: str | None = None
    confidence: float = 0.0


@dataclass
class ParsedSoftware:
    """Software/tool proficiency extracted from CV."""

    name: str
    software_id: UUID | None = None
    canonical_id: str | None = None
    vendor: str | None = None
    category: str | None = None
    proficiency_level: SkillLevel | None = None
    version_used: str | None = None
    years_of_experience: float | None = None
    last_used_year: int | None = None
    confidence: float = 0.0


@dataclass
class ParsedCV:
    """Complete parsed CV structure."""

    # Core data
    personal: ParsedPersonal
    education: list[ParsedEducation] = field(default_factory=list)
    experience: list[ParsedExperience] = field(default_factory=list)
    skills: list[ParsedSkill] = field(default_factory=list)
    languages: list[ParsedLanguage] = field(default_factory=list)
    certifications: list[ParsedCertification] = field(default_factory=list)
    driving_licenses: list[ParsedDrivingLicense] = field(default_factory=list)
    software: list[ParsedSoftware] = field(default_factory=list)

    # Metadata
    correlation_id: str | None = None
    source_file: str | None = None
    parsing_version: str = "1.0.0"
    model_used: str | None = None

    # Quality metrics
    overall_confidence: float = 0.0
    completeness_score: float = 0.0
    parsing_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Raw data
    raw_cv_text: str | None = None
    raw_json: dict[str, Any] | None = None

    def calculate_completeness(self) -> float:
        """
        Calculate completeness score based on filled fields.

        Returns:
            Score from 0.0 to 1.0
        """
        score = 0.0

        # Personal info (0.25 max)
        if self.personal.first_name and self.personal.last_name:
            score += 0.05
        if self.personal.email:
            score += 0.10
        if self.personal.phone:
            score += 0.05
        if self.personal.address_city:
            score += 0.05

        # Education (0.20 max)
        if self.education:
            score += min(0.20, len(self.education) * 0.10)

        # Experience (0.30 max)
        if self.experience:
            score += min(0.30, len(self.experience) * 0.10)

        # Skills (0.15 max)
        if self.skills:
            score += min(0.15, len(self.skills) * 0.03)

        # Languages (0.10 max)
        if self.languages:
            score += min(0.10, len(self.languages) * 0.05)

        self.completeness_score = min(score, 1.0)
        return self.completeness_score

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dict representation of parsed CV
        """
        from dataclasses import asdict

        def convert_value(obj: Any) -> Any:
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, date):
                return obj.isoformat()
            if isinstance(obj, UUID):
                return str(obj)
            return obj

        def process_dict(d: dict) -> dict:
            result = {}
            for key, value in d.items():
                if isinstance(value, dict):
                    result[key] = process_dict(value)
                elif isinstance(value, list):
                    result[key] = [
                        process_dict(v) if isinstance(v, dict) else convert_value(v)
                        for v in value
                    ]
                else:
                    result[key] = convert_value(value)
            return result

        return process_dict(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParsedCV":
        """
        Create ParsedCV from dictionary.

        Args:
            data: Dict with parsed CV data

        Returns:
            ParsedCV instance
        """
        # Parse personal info
        personal_data = data.get("personal", {})
        personal = ParsedPersonal(
            first_name=personal_data.get("first_name", ""),
            last_name=personal_data.get("last_name", ""),
            first_name_normalized=personal_data.get("first_name_normalized"),
            last_name_normalized=personal_data.get("last_name_normalized"),
            email=personal_data.get("email"),
            phone=personal_data.get("phone"),
            address_city=personal_data.get("address_city"),
            address_region=personal_data.get("address_region"),
            address_country=personal_data.get("address_country", "Greece"),
            confidence=personal_data.get("confidence", 0.0),
        )

        # Parse education
        education = []
        for edu_data in data.get("education", []):
            education.append(
                ParsedEducation(
                    institution_name=edu_data.get("institution_name", ""),
                    degree_level=EducationLevel(edu_data["degree_level"])
                    if edu_data.get("degree_level")
                    else None,
                    degree_title=edu_data.get("degree_title"),
                    field_of_study=EducationField(edu_data["field_of_study"])
                    if edu_data.get("field_of_study")
                    else None,
                    start_date=date.fromisoformat(edu_data["start_date"])
                    if edu_data.get("start_date")
                    else None,
                    end_date=date.fromisoformat(edu_data["end_date"])
                    if edu_data.get("end_date")
                    else None,
                    is_current=edu_data.get("is_current", False),
                    graduation_year=edu_data.get("graduation_year"),
                    confidence=edu_data.get("confidence", 0.0),
                )
            )

        # Parse experience
        experience = []
        for exp_data in data.get("experience", []):
            experience.append(
                ParsedExperience(
                    company_name=exp_data.get("company_name", ""),
                    job_title=exp_data.get("job_title", ""),
                    company_city=exp_data.get("company_city"),
                    employment_type=EmploymentType(exp_data["employment_type"])
                    if exp_data.get("employment_type")
                    else None,
                    start_date=date.fromisoformat(exp_data["start_date"])
                    if exp_data.get("start_date")
                    else None,
                    end_date=date.fromisoformat(exp_data["end_date"])
                    if exp_data.get("end_date")
                    else None,
                    is_current=exp_data.get("is_current", False),
                    description=exp_data.get("description"),
                    responsibilities=exp_data.get("responsibilities", []),
                    achievements=exp_data.get("achievements", []),
                    technologies_used=exp_data.get("technologies_used", []),
                    confidence=exp_data.get("confidence", 0.0),
                )
            )

        # Parse skills
        skills = []
        for skill_data in data.get("skills", []):
            skills.append(
                ParsedSkill(
                    name=skill_data.get("name", ""),
                    canonical_id=skill_data.get("canonical_id"),
                    level=SkillLevel(skill_data["level"])
                    if skill_data.get("level")
                    else None,
                    years_of_experience=skill_data.get("years_of_experience"),
                    confidence=skill_data.get("confidence", 0.0),
                )
            )

        # Parse languages
        languages = []
        for lang_data in data.get("languages", []):
            languages.append(
                ParsedLanguage(
                    language_code=lang_data.get("language_code", ""),
                    language_name=lang_data.get("language_name", ""),
                    proficiency_level=LanguageProficiency(lang_data["proficiency_level"])
                    if lang_data.get("proficiency_level")
                    else LanguageProficiency.UNKNOWN,
                    is_native=lang_data.get("is_native", False),
                    certification_name=lang_data.get("certification_name"),
                    confidence=lang_data.get("confidence", 0.0),
                )
            )

        # Parse certifications
        certifications = []
        for cert_data in data.get("certifications", []):
            certifications.append(
                ParsedCertification(
                    certification_name=cert_data.get("certification_name", ""),
                    issuing_organization=cert_data.get("issuing_organization"),
                    issue_date=date.fromisoformat(cert_data["issue_date"])
                    if cert_data.get("issue_date")
                    else None,
                    expiry_date=date.fromisoformat(cert_data["expiry_date"])
                    if cert_data.get("expiry_date")
                    else None,
                    credential_id=cert_data.get("credential_id"),
                    confidence=cert_data.get("confidence", 0.0),
                )
            )

        # Parse driving licenses
        driving_licenses = []
        for dl_data in data.get("driving_licenses", []):
            driving_licenses.append(
                ParsedDrivingLicense(
                    license_category=DrivingLicenseCategory(dl_data["license_category"])
                    if dl_data.get("license_category")
                    else DrivingLicenseCategory.B,
                    issue_date=date.fromisoformat(dl_data["issue_date"])
                    if dl_data.get("issue_date")
                    else None,
                    confidence=dl_data.get("confidence", 0.0),
                )
            )

        return cls(
            personal=personal,
            education=education,
            experience=experience,
            skills=skills,
            languages=languages,
            certifications=certifications,
            driving_licenses=driving_licenses,
            correlation_id=data.get("correlation_id"),
            parsing_version=data.get("parsing_version", "1.0.0"),
            overall_confidence=data.get("overall_confidence", 0.0),
        )


# Greek to English mapping utilities
GREEK_SKILL_LEVELS = {
    "αρχάριος": SkillLevel.BEGINNER,
    "αρχαριος": SkillLevel.BEGINNER,
    "βασικό": SkillLevel.BEGINNER,
    "βασικο": SkillLevel.BEGINNER,
    "μέτριο": SkillLevel.INTERMEDIATE,
    "μετριο": SkillLevel.INTERMEDIATE,
    "καλό": SkillLevel.INTERMEDIATE,
    "καλο": SkillLevel.INTERMEDIATE,
    "πολύ καλό": SkillLevel.ADVANCED,
    "πολυ καλο": SkillLevel.ADVANCED,
    "προχωρημένο": SkillLevel.ADVANCED,
    "προχωρημενο": SkillLevel.ADVANCED,
    "άριστο": SkillLevel.EXPERT,
    "αριστο": SkillLevel.EXPERT,
    "άριστη": SkillLevel.EXPERT,
    "αριστη": SkillLevel.EXPERT,
    "εξαιρετικό": SkillLevel.EXPERT,
    "εξαιρετικο": SkillLevel.EXPERT,
}

GREEK_LANGUAGE_LEVELS = {
    "βασικό": LanguageProficiency.A2,
    "βασικο": LanguageProficiency.A2,
    "μέτριο": LanguageProficiency.B1,
    "μετριο": LanguageProficiency.B1,
    "καλό": LanguageProficiency.B2,
    "καλο": LanguageProficiency.B2,
    "πολύ καλό": LanguageProficiency.C1,
    "πολυ καλο": LanguageProficiency.C1,
    "πολύ καλή": LanguageProficiency.C1,
    "πολυ καλη": LanguageProficiency.C1,
    "άριστο": LanguageProficiency.C2,
    "αριστο": LanguageProficiency.C2,
    "άριστη": LanguageProficiency.C2,
    "αριστη": LanguageProficiency.C2,
    "μητρική": LanguageProficiency.NATIVE,
    "μητρικη": LanguageProficiency.NATIVE,
}

# Language code mapping
LANGUAGE_CODES = {
    "ελληνικά": "el",
    "ελληνικα": "el",
    "greek": "el",
    "αγγλικά": "en",
    "αγγλικα": "en",
    "english": "en",
    "γερμανικά": "de",
    "γερμανικα": "de",
    "german": "de",
    "γαλλικά": "fr",
    "γαλλικα": "fr",
    "french": "fr",
    "ιταλικά": "it",
    "ιταλικα": "it",
    "italian": "it",
    "ισπανικά": "es",
    "ισπανικα": "es",
    "spanish": "es",
    "ρωσικά": "ru",
    "ρωσικα": "ru",
    "russian": "ru",
    "τουρκικά": "tr",
    "τουρκικα": "tr",
    "turkish": "tr",
    "αλβανικά": "sq",
    "αλβανικα": "sq",
    "albanian": "sq",
    "βουλγαρικά": "bg",
    "βουλγαρικα": "bg",
    "bulgarian": "bg",
}


def normalize_skill_level(level_str: str) -> SkillLevel | None:
    """
    Normalize skill level string (Greek or English) to enum.

    Args:
        level_str: Skill level as string

    Returns:
        SkillLevel enum or None
    """
    level_lower = level_str.lower().strip()

    # Check Greek mappings
    if level_lower in GREEK_SKILL_LEVELS:
        return GREEK_SKILL_LEVELS[level_lower]

    # Check English values
    try:
        return SkillLevel(level_lower)
    except ValueError:
        pass

    # Fuzzy matching
    if "begin" in level_lower or "basic" in level_lower:
        return SkillLevel.BEGINNER
    if "inter" in level_lower or "medium" in level_lower:
        return SkillLevel.INTERMEDIATE
    if "advanc" in level_lower or "good" in level_lower:
        return SkillLevel.ADVANCED
    if "expert" in level_lower or "excell" in level_lower:
        return SkillLevel.EXPERT

    return None


def normalize_language_proficiency(prof_str: str) -> LanguageProficiency:
    """
    Normalize language proficiency string to CEFR level.

    Args:
        prof_str: Proficiency as string

    Returns:
        LanguageProficiency enum
    """
    prof_lower = prof_str.lower().strip()

    # Check Greek mappings
    if prof_lower in GREEK_LANGUAGE_LEVELS:
        return GREEK_LANGUAGE_LEVELS[prof_lower]

    # Check CEFR levels
    try:
        return LanguageProficiency(prof_str.upper())
    except ValueError:
        pass

    # Check "native" variants
    if "native" in prof_lower or "μητρικ" in prof_lower:
        return LanguageProficiency.NATIVE

    return LanguageProficiency.UNKNOWN


def get_language_code(language_name: str) -> str:
    """
    Get ISO 639-1 language code from name.

    Args:
        language_name: Language name in Greek or English

    Returns:
        2-letter language code
    """
    name_lower = language_name.lower().strip()
    return LANGUAGE_CODES.get(name_lower, name_lower[:2])
