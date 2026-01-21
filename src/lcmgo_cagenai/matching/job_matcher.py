"""
Job Matcher - Intelligent candidate matching with relaxed criteria

Finds candidates matching the MOST criteria when no exact match exists,
and provides evidence-based ranking with explanations.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Any
from enum import Enum

from lcmgo_cagenai.llm.provider import LLMRequest, ModelType


def _json_serializer(obj):
    """Custom JSON serializer for UUID and Decimal types."""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

logger = logging.getLogger(__name__)


class MatchLevel(Enum):
    """Candidate match level"""
    HIGH = "Υψηλή"      # 70%+
    MEDIUM = "Μέτρια"   # 40-70%
    LOW = "Χαμηλή"      # <40%


@dataclass
class RequirementMatch:
    """Single requirement match result"""
    requirement_type: str       # role, experience, software, language, certification
    requirement_value: str      # What was requested
    candidate_value: Optional[str]  # What candidate has
    matched: bool
    source: Optional[str] = None  # CV section reference
    alternative: Optional[str] = None  # Suggested alternative if not matched
    gap_severity: str = "minor"  # minor, major


@dataclass
class CandidateMatch:
    """Complete match result for a single candidate"""
    candidate_id: str
    name: str
    email: str
    phone: Optional[str]
    city: Optional[str]
    total_experience_years: float
    match_level: MatchLevel
    match_percentage: float
    matched_requirements: list[RequirementMatch] = field(default_factory=list)
    missing_requirements: list[RequirementMatch] = field(default_factory=list)
    comment: str = ""
    recommendation: str = "consider"  # interview, consider, skip
    raw_data: dict = field(default_factory=dict)


@dataclass
class JobRequirements:
    """Extracted job requirements"""
    role: Optional[str] = None
    experience_years: Optional[float] = None
    software: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    location: Optional[str] = None

    # Priority weights
    weights: dict = field(default_factory=lambda: {
        "role": 0.25,
        "experience": 0.35,
        "software": 0.20,
        "language": 0.10,
        "certification": 0.10
    })


@dataclass
class MatchResult:
    """Complete job matching result"""
    query: str
    requirements: JobRequirements
    candidates: list[CandidateMatch]
    total_found: int
    summary: str = ""
    recommendations: list[str] = field(default_factory=list)


class JobMatcher:
    """
    Intelligent job matcher that finds best candidates even with partial matches.

    Two-phase approach:
    1. Extract requirements from natural language query (Claude Haiku)
    2. Find candidates with relaxed SQL + analyze with Claude Sonnet
    """

    def __init__(self, db_connection, llm_provider):
        """
        Initialize JobMatcher.

        Args:
            db_connection: PostgreSQL connection (pg8000)
            llm_provider: BedrockProvider instance
        """
        self.db = db_connection
        self.llm = llm_provider

    def extract_requirements(self, query: str) -> JobRequirements:
        """
        Extract structured requirements from natural language query.

        Uses Claude Haiku for fast, cheap extraction.
        """
        prompt = f"""Analyze this job search query and extract structured requirements.

Query: "{query}"

Return ONLY valid JSON (no markdown, no explanation):
{{
  "role": "accountant|engineer|manager|null if not specified",
  "experience_years": 5,
  "software": ["Excel", "SAP"],
  "languages": ["en", "el"],
  "certifications": [],
  "skills": [],
  "location": "city or null"
}}

IMPORTANT:
- Use null for unspecified fields
- For languages, use ISO codes: en=English, el=Greek, de=German, fr=French
- For software, preserve original names (SAP, Excel, ERP, etc.)
- Extract numbers from text like "πάνω από 5 χρόνια" → 5
- Greek "λογιστής" → "accountant", "μηχανικός" → "engineer"
"""

        try:
            # Create LLM request
            request = LLMRequest(
                prompt=prompt,
                model=ModelType.CLAUDE_HAIKU,
                max_tokens=500,
                temperature=0.0
            )

            # Run async complete
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(self.llm.complete(request))

            # Parse JSON response
            json_str = response.content.strip()
            # Remove markdown code blocks if present
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]

            data = json.loads(json_str)

            return JobRequirements(
                role=data.get("role"),
                experience_years=data.get("experience_years"),
                software=data.get("software", []) or [],
                languages=data.get("languages", []) or [],
                certifications=data.get("certifications", []) or [],
                skills=data.get("skills", []) or [],
                location=data.get("location")
            )

        except Exception as e:
            logger.error(f"Failed to extract requirements: {e}")
            # Return empty requirements on failure
            return JobRequirements()

    def find_candidates_relaxed(
        self,
        requirements: JobRequirements,
        limit: int = 10
    ) -> list[dict]:
        """
        Find candidates using relaxed SQL matching.

        Uses the match_candidates_relaxed PostgreSQL function.
        """
        cursor = self.db.cursor()

        try:
            # Prepare parameters
            software_array = requirements.software if requirements.software else None
            languages_array = requirements.languages if requirements.languages else None
            certs_array = requirements.certifications if requirements.certifications else None

            # Call the PostgreSQL function
            cursor.execute("""
                SELECT * FROM match_candidates_relaxed(
                    %s, %s, %s, %s, %s, %s
                )
            """, (
                requirements.role,
                requirements.experience_years,
                software_array,
                languages_array,
                certs_array,
                limit
            ))

            columns = [desc[0] for desc in cursor.description]
            results = []

            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

            return results

        except Exception as e:
            logger.error(f"Relaxed search failed: {e}")
            return []
        finally:
            cursor.close()

    def get_candidate_profile(self, candidate_id: str) -> dict:
        """
        Get complete candidate profile for LLM analysis.

        Uses the get_candidate_full_profile PostgreSQL function.
        """
        cursor = self.db.cursor()

        try:
            cursor.execute(
                "SELECT get_candidate_full_profile(%s)",
                (candidate_id,)
            )
            result = cursor.fetchone()

            if result and result[0]:
                return result[0] if isinstance(result[0], dict) else json.loads(result[0])
            return {}

        except Exception as e:
            logger.error(f"Failed to get candidate profile: {e}")
            return {}
        finally:
            cursor.close()

    # Domain knowledge for Greek market software/certification equivalencies
    DOMAIN_KNOWLEDGE = """
IMPORTANT DOMAIN KNOWLEDGE - Software Equivalencies:

ERP Systems (all are equivalent for "ERP" requirement):
- Greek: SoftOne, Singular (SingularLogic), Galaxy (Entersoft), Atlantis, Pylon (Epsilon), Pegasus, PRISMA Win
- International: SAP, Oracle, Microsoft Dynamics, Navision, NetSuite, Odoo, Sage

Office/Computer Skills (equivalent for "Office" or "Microsoft Office" requirement):
- Microsoft Office, MS Office, Office 365, Excel, Word, PowerPoint, Outlook
- Google Workspace (G Suite)
- ECDL/ICDL certification = PROVES Office proficiency
- MOS (Microsoft Office Specialist) = PROVES Office proficiency

Accounting Software:
- SoftOne, Singular, Galaxy, Epsilon, PRISMA Win are Greek accounting/ERP systems
- QuickBooks, Xero, MYOB are international

Certification Inferences:
- ECDL = Microsoft Office proficiency (Excel, Word, PowerPoint, Outlook)
- ICDL = Microsoft Office proficiency
- MOS = Microsoft Office proficiency
- CPA/ACCA/ΟΕΕ/ΣΟΕΛ = Professional accounting qualification
"""

    def analyze_candidate(
        self,
        candidate_data: dict,
        requirements: JobRequirements,
        sql_match_data: dict
    ) -> CandidateMatch:
        """
        Analyze a single candidate against requirements using Claude Sonnet.

        Returns detailed match analysis with evidence.
        """
        prompt = f"""Analyze this candidate against job requirements. Respond in Greek.

{self.DOMAIN_KNOWLEDGE}

REQUIREMENTS:
- Role: {requirements.role or 'Not specified'}
- Experience: {requirements.experience_years or 'Not specified'} years minimum
- Software: {', '.join(requirements.software) if requirements.software else 'Not specified'}
- Languages: {', '.join(requirements.languages) if requirements.languages else 'Not specified'}
- Certifications: {', '.join(requirements.certifications) if requirements.certifications else 'Not specified'}

CANDIDATE DATA:
{json.dumps(candidate_data, ensure_ascii=False, indent=2, default=_json_serializer)}

SQL PRE-MATCH DATA:
{json.dumps(sql_match_data, ensure_ascii=False, indent=2, default=_json_serializer)}

RESPOND WITH VALID JSON ONLY. No markdown, no explanation. Ensure all strings are properly quoted and closed.

{{
  "match_level": "Υψηλή|Μέτρια|Χαμηλή",
  "match_percentage": 75,
  "matched": [{{"requirement": "...", "value": "...", "source": "..."}}],
  "missing": [{{"requirement": "...", "alternative": "...", "severity": "minor|major"}}],
  "comment": "Brief comment (max 100 chars)",
  "recommendation": "interview|consider|skip"
}}

CRITICAL MATCHING RULES:
1. If requirement is "ERP" and candidate has SoftOne/Singular/Galaxy/SAP → MATCHED (not missing!)
2. If requirement is "Office" and candidate has ECDL/ICDL/MOS → MATCHED (certification proves proficiency)
3. If requirement is "Excel" and candidate has ECDL → MATCHED
4. Greek ERP systems (SoftOne, Singular, Galaxy) ARE enterprise ERP systems
5. Υψηλή: 70%+ match, Μέτρια: 40-70%, Χαμηλή: <40%
6. Keep arrays short (max 3 items each)
7. Keep comment brief (under 100 characters)
"""

        try:
            # Create LLM request - use Haiku for speed (Sonnet is too slow per-candidate)
            request = LLMRequest(
                prompt=prompt,
                model=ModelType.CLAUDE_HAIKU,
                max_tokens=800,
                temperature=0.1
            )

            # Run async complete
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(self.llm.complete(request))

            # Parse JSON response
            json_str = response.content.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]

            data = json.loads(json_str)

            # Build match result
            match_level = MatchLevel.MEDIUM
            if data.get("match_level") == "Υψηλή":
                match_level = MatchLevel.HIGH
            elif data.get("match_level") == "Χαμηλή":
                match_level = MatchLevel.LOW

            matched_reqs = [
                RequirementMatch(
                    requirement_type="general",
                    requirement_value=m.get("requirement", ""),
                    candidate_value=m.get("value", ""),
                    matched=True,
                    source=m.get("source")
                )
                for m in data.get("matched", [])
            ]

            missing_reqs = [
                RequirementMatch(
                    requirement_type="general",
                    requirement_value=m.get("requirement", ""),
                    candidate_value=None,
                    matched=False,
                    alternative=m.get("alternative"),
                    gap_severity=m.get("severity", "minor")
                )
                for m in data.get("missing", [])
            ]

            return CandidateMatch(
                candidate_id=str(candidate_data.get("id", "")),
                name=candidate_data.get("name", "Unknown"),
                email=candidate_data.get("email", ""),
                phone=candidate_data.get("phone"),
                city=candidate_data.get("city"),
                total_experience_years=float(candidate_data.get("total_experience_years", 0)),
                match_level=match_level,
                match_percentage=float(data.get("match_percentage", 0)),
                matched_requirements=matched_reqs,
                missing_requirements=missing_reqs,
                comment=data.get("comment", ""),
                recommendation=data.get("recommendation", "consider"),
                raw_data=candidate_data
            )

        except Exception as e:
            logger.error(f"Failed to analyze candidate: {e}")
            # Return basic match from SQL data
            return CandidateMatch(
                candidate_id=str(sql_match_data.get("candidate_id", "")),
                name=f"{sql_match_data.get('first_name', '')} {sql_match_data.get('last_name', '')}",
                email=sql_match_data.get("email", ""),
                phone=sql_match_data.get("phone"),
                city=sql_match_data.get("address_city"),
                total_experience_years=float(sql_match_data.get("total_experience_years", 0)),
                match_level=MatchLevel.MEDIUM,
                match_percentage=float(sql_match_data.get("match_score", 0)) * 100,
                comment="Analysis unavailable",
                recommendation="consider"
            )

    def match(self, query: str, limit: int = 10) -> MatchResult:
        """
        Main entry point: find best matching candidates for a query.

        Args:
            query: Natural language job search query
            limit: Maximum candidates to return

        Returns:
            MatchResult with ranked candidates and analysis
        """
        logger.info(f"Job matching for query: {query}")

        # Step 1: Extract requirements
        requirements = self.extract_requirements(query)
        logger.info(f"Extracted requirements: role={requirements.role}, exp={requirements.experience_years}")

        # Step 2: Find candidates with relaxed SQL
        sql_matches = self.find_candidates_relaxed(requirements, limit)
        logger.info(f"Found {len(sql_matches)} candidates with relaxed matching")

        if not sql_matches:
            return MatchResult(
                query=query,
                requirements=requirements,
                candidates=[],
                total_found=0,
                summary="Δεν βρέθηκαν υποψήφιοι που να ταιριάζουν με κανένα κριτήριο.",
                recommendations=["Δοκιμάστε λιγότερα κριτήρια ή πιο γενική αναζήτηση."]
            )

        # Step 3: Analyze each candidate with LLM (limit to top 5 for speed)
        candidates = []
        max_llm_analysis = min(5, len(sql_matches))  # Limit LLM analysis to 5 for latency
        for i, sql_match in enumerate(sql_matches):
            # Get full profile
            profile = self.get_candidate_profile(str(sql_match.get("candidate_id")))

            if profile and i < max_llm_analysis:
                # Analyze with LLM (only for top candidates)
                candidate_match = self.analyze_candidate(profile, requirements, sql_match)
                candidates.append(candidate_match)
            else:
                # Fallback to SQL data only (for candidates beyond top 5 or missing profile)
                candidates.append(CandidateMatch(
                    candidate_id=str(sql_match.get("candidate_id", "")),
                    name=f"{sql_match.get('first_name', '')} {sql_match.get('last_name', '')}",
                    email=sql_match.get("email", ""),
                    phone=sql_match.get("phone"),
                    city=sql_match.get("address_city"),
                    total_experience_years=float(sql_match.get("total_experience_years", 0)),
                    match_level=self._score_to_level(float(sql_match.get("match_score", 0))),
                    match_percentage=float(sql_match.get("match_score", 0)) * 100,
                    comment="",
                    recommendation="consider"
                ))

        # Sort by match percentage
        candidates.sort(key=lambda c: c.match_percentage, reverse=True)

        # Generate summary
        high_count = sum(1 for c in candidates if c.match_level == MatchLevel.HIGH)
        medium_count = sum(1 for c in candidates if c.match_level == MatchLevel.MEDIUM)

        summary = f"Βρέθηκαν {len(candidates)} υποψήφιοι: {high_count} με υψηλή, {medium_count} με μέτρια καταλληλότητα."

        recommendations = []
        if high_count == 0:
            recommendations.append("Κανένας υποψήφιος δεν καλύπτει πλήρως τα κριτήρια.")
        if high_count > 0:
            recommendations.append(f"Προτείνεται συνέντευξη με τους {min(high_count, 3)} καλύτερους.")

        return MatchResult(
            query=query,
            requirements=requirements,
            candidates=candidates,
            total_found=len(candidates),
            summary=summary,
            recommendations=recommendations
        )

    def _score_to_level(self, score: float) -> MatchLevel:
        """Convert numeric score (0-1) to match level."""
        if score >= 0.7:
            return MatchLevel.HIGH
        elif score >= 0.4:
            return MatchLevel.MEDIUM
        return MatchLevel.LOW
