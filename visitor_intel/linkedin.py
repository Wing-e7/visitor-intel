"""
LinkedIn URL scoring.

When a visitor shares their LinkedIn URL (via a form or chat), it is both
a strong intent signal and a source of seniority information.

No scraping — LinkedIn blocks it. We score based on URL structure
(person vs company) and an optional job title string the caller provides.
"""
import re
from typing import Optional

_PERSON_URL_RE = re.compile(r"linkedin\.com/in/([^/?&#]+)", re.IGNORECASE)
_COMPANY_URL_RE = re.compile(r"linkedin\.com/company/([^/?&#]+)", re.IGNORECASE)

# Job title keywords that indicate a decision-maker
_DECISION_MAKER_RE = re.compile(
    r"\b(?:ceo|cto|cmo|coo|cfo|cpo|"
    r"founder|co[- ]founder|"
    r"vp|vice\s+president|"
    r"director|head\s+of|"
    r"president|owner|partner|"
    r"managing\s+director|md\b|"
    r"general\s+manager|gm\b)\b",
    re.IGNORECASE,
)


def parse_linkedin_url(url: Optional[str]) -> dict:
    """
    Parse a LinkedIn URL and return its type and handle.

    Returns:
        {
            "valid": bool,
            "type": "person" | "company" | "unknown",
            "handle": str,
        }
    """
    if not url:
        return {"valid": False, "type": "unknown", "handle": ""}

    person_match = _PERSON_URL_RE.search(url)
    if person_match:
        return {"valid": True, "type": "person", "handle": person_match.group(1)}

    company_match = _COMPANY_URL_RE.search(url)
    if company_match:
        return {"valid": True, "type": "company", "handle": company_match.group(1)}

    return {"valid": False, "type": "unknown", "handle": ""}


def score_linkedin(
    linkedin_url: Optional[str],
    job_title: Optional[str] = None,
) -> int:
    """
    Score a LinkedIn URL presence (0–20).

    Points:
      +5   Company LinkedIn URL shared
      +10  Personal LinkedIn URL shared (any seniority)
      +20  Personal LinkedIn + decision-maker title (replaces the +10)

    The caller is responsible for obtaining job_title — e.g. from a form
    field, a prior conversation turn, or a CRM enrichment step.

    Args:
        linkedin_url: Raw LinkedIn URL string as provided by the visitor.
        job_title:    Optional job title string to check for seniority signals.

    Returns:
        Integer score contribution in [0, 20].
    """
    parsed = parse_linkedin_url(linkedin_url)
    if not parsed["valid"]:
        return 0

    if parsed["type"] == "company":
        return 5

    # Person URL
    if job_title and _DECISION_MAKER_RE.search(job_title):
        return 20

    return 10
