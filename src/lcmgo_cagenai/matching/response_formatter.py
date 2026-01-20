"""
Response Formatter - Formats job matching results for display

Generates user-friendly Greek responses with:
- Star ratings
- Checkmarks and X marks
- Evidence-based explanations
- CV source references
"""

from .job_matcher import MatchResult, CandidateMatch, MatchLevel


class ResponseFormatter:
    """Formats MatchResult into user-friendly Greek response."""

    @staticmethod
    def format_match_result(result: MatchResult) -> str:
        """
        Format complete match result as Greek text.

        Returns formatted string ready for display.
        """
        if not result.candidates:
            return ResponseFormatter._format_no_results(result)

        lines = [
            "**Ανάλυση Αναζήτησης**",
            "",
            f"Βρέθηκαν **{result.total_found} υποψήφιοι** που ταιριάζουν με τα περισσότερα κριτήρια:",
            "",
            "---",
            ""
        ]

        # Format each candidate
        for i, candidate in enumerate(result.candidates, 1):
            lines.extend(ResponseFormatter._format_candidate(i, candidate))
            lines.append("")
            lines.append("---")
            lines.append("")

        # Add summary
        lines.extend(ResponseFormatter._format_summary(result))

        return "\n".join(lines)

    @staticmethod
    def _format_candidate(rank: int, candidate: CandidateMatch) -> list[str]:
        """Format a single candidate."""
        stars = ResponseFormatter._get_stars(candidate.match_level)

        lines = [
            f"### {rank}. {candidate.name}",
            f"**Καταλληλότητα: {candidate.match_level.value}** {stars}",
            ""
        ]

        # Contact info
        if candidate.email or candidate.phone:
            contact = []
            if candidate.email:
                contact.append(candidate.email)
            if candidate.phone:
                contact.append(candidate.phone)
            if candidate.city:
                contact.append(candidate.city)
            lines.append(f"*{' | '.join(contact)}*")
            lines.append("")

        # Experience
        if candidate.total_experience_years > 0:
            lines.append(f"**Συνολική εμπειρία:** {candidate.total_experience_years:.1f} χρόνια")
            lines.append("")

        # What they HAVE
        if candidate.matched_requirements:
            lines.append("**Καλύπτει:**")
            for req in candidate.matched_requirements:
                source = f" *(Πηγή: {req.source})*" if req.source else ""
                lines.append(f"- {req.requirement_value}: {req.candidate_value}{source}")
            lines.append("")

        # What they're MISSING
        if candidate.missing_requirements:
            lines.append("**Δεν καλύπτει:**")
            for req in candidate.missing_requirements:
                alt = f" ({req.alternative})" if req.alternative else ""
                severity_icon = "" if req.gap_severity == "major" else ""
                lines.append(f"- {req.requirement_value}{alt}{severity_icon}")
            lines.append("")

        # Comment
        if candidate.comment:
            lines.append(f"**Σχόλιο:** {candidate.comment}")
            lines.append("")

        # Recommendation
        rec_text = {
            "interview": "Προτείνεται για συνέντευξη",
            "consider": "Αξίζει να εξεταστεί",
            "skip": "Δεν ταιριάζει"
        }.get(candidate.recommendation, "")

        if rec_text:
            lines.append(f"**Πρόταση:** {rec_text}")

        return lines

    @staticmethod
    def _format_summary(result: MatchResult) -> list[str]:
        """Format summary section."""
        lines = [
            "**Σύνοψη:**",
            ""
        ]

        # Count by level
        high = sum(1 for c in result.candidates if c.match_level == MatchLevel.HIGH)
        medium = sum(1 for c in result.candidates if c.match_level == MatchLevel.MEDIUM)
        low = sum(1 for c in result.candidates if c.match_level == MatchLevel.LOW)

        if high > 0:
            lines.append(f"- **{high}** υποψήφιοι με υψηλή καταλληλότητα")
        if medium > 0:
            lines.append(f"- **{medium}** υποψήφιοι με μέτρια καταλληλότητα")
        if low > 0:
            lines.append(f"- **{low}** υποψήφιοι με χαμηλή καταλληλότητα")

        lines.append("")

        # Recommendations
        if result.recommendations:
            lines.append("**Προτεινόμενες ενέργειες:**")
            for rec in result.recommendations:
                lines.append(f"- {rec}")

        return lines

    @staticmethod
    def _format_no_results(result: MatchResult) -> str:
        """Format response when no candidates found."""
        lines = [
            "**Ανάλυση Αναζήτησης**",
            "",
            "Δεν βρέθηκαν υποψήφιοι που να ταιριάζουν με τα κριτήρια.",
            "",
            "**Κριτήρια που αναζητήθηκαν:**"
        ]

        if result.requirements.role:
            lines.append(f"- Ρόλος: {result.requirements.role}")
        if result.requirements.experience_years:
            lines.append(f"- Εμπειρία: {result.requirements.experience_years}+ χρόνια")
        if result.requirements.software:
            lines.append(f"- Software: {', '.join(result.requirements.software)}")
        if result.requirements.languages:
            lang_names = {
                "en": "Αγγλικά",
                "el": "Ελληνικά",
                "de": "Γερμανικά",
                "fr": "Γαλλικά"
            }
            langs = [lang_names.get(l, l) for l in result.requirements.languages]
            lines.append(f"- Γλώσσες: {', '.join(langs)}")

        lines.extend([
            "",
            "**Προτάσεις:**",
            "- Δοκιμάστε με λιγότερα κριτήρια",
            "- Χρησιμοποιήστε πιο γενικούς όρους",
            "- Μειώστε τα έτη εμπειρίας που απαιτούνται"
        ])

        return "\n".join(lines)

    @staticmethod
    def _get_stars(level: MatchLevel) -> str:
        """Get star rating for match level."""
        if level == MatchLevel.HIGH:
            return ""
        elif level == MatchLevel.MEDIUM:
            return ""
        return ""

    @staticmethod
    def format_as_json(result: MatchResult) -> dict:
        """
        Format match result as JSON for API response.

        Returns dict suitable for JSON serialization.
        """
        return {
            "query": result.query,
            "total_found": result.total_found,
            "summary": result.summary,
            "requirements": {
                "role": result.requirements.role,
                "experience_years": result.requirements.experience_years,
                "software": result.requirements.software,
                "languages": result.requirements.languages,
                "certifications": result.requirements.certifications
            },
            "candidates": [
                {
                    "rank": i + 1,
                    "id": str(c.candidate_id),  # Convert UUID to string
                    "name": c.name,
                    "email": c.email,
                    "phone": c.phone,
                    "city": c.city,
                    "total_experience_years": float(c.total_experience_years) if c.total_experience_years else 0,
                    "match_level": c.match_level.value,
                    "match_percentage": float(c.match_percentage) if c.match_percentage else 0,
                    "matched": [
                        {
                            "requirement": r.requirement_value,
                            "value": r.candidate_value,
                            "source": r.source
                        }
                        for r in c.matched_requirements
                    ],
                    "missing": [
                        {
                            "requirement": r.requirement_value,
                            "alternative": r.alternative,
                            "severity": r.gap_severity
                        }
                        for r in c.missing_requirements
                    ],
                    "comment": c.comment,
                    "recommendation": c.recommendation
                }
                for i, c in enumerate(result.candidates)
            ],
            "recommendations": result.recommendations
        }
