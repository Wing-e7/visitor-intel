"""
Client-similarity ICP scoring.

Instead of generic rules, define your ICP by providing URLs of your existing
clients. The model extracts their company fingerprint, then scores new visitors
by how closely their company matches.

Usage:
    client_profiles = await load_client_profiles([
        "https://stripe.com",
        "https://notion.so",
        "https://figma.com",
    ])

    visitor_signals = await enrich_company_url("https://newvisitor.com")
    similarity_score = compute_client_similarity(visitor_signals, client_profiles)
    # Pass as client_similarity_score= to compute_icp_score()
"""
import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from .company_enrichment import enrich_company_url

logger = logging.getLogger(__name__)

# --- Industry detection -------------------------------------------------------

_INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "saas":       ["software", "platform", "api", "developer", "cloud", "saas", "app", "tool", "dashboard"],
    "fintech":    ["payment", "finance", "banking", "invoice", "billing", "accounting", "fintech", "transaction"],
    "healthcare": ["health", "medical", "clinical", "patient", "hospital", "pharma", "biotech"],
    "ecommerce":  ["shop", "store", "product", "cart", "checkout", "marketplace", "retail", "d2c"],
    "marketing":  ["marketing", "advertising", "campaign", "email", "analytics", "seo", "media"],
    "hr":         ["hiring", "talent", "recruiting", "hr", "people", "workforce", "employee", "payroll"],
    "security":   ["security", "compliance", "risk", "privacy", "audit", "cybersecurity", "identity"],
    "legal":      ["legal", "contract", "regulation", "law", "attorney", "counsel"],
    "logistics":  ["logistics", "supply chain", "shipping", "freight", "warehouse", "fulfilment"],
    "edtech":     ["education", "learning", "training", "course", "lms", "curriculum", "upskill"],
}

_B2B_RE = re.compile(
    r"\b(enterprise|business|team|company|organization|workflow|integration|api|b2b|saas|clients?|customers?|revenue|pipeline|leads?)\b",
    re.IGNORECASE,
)
_B2C_RE = re.compile(
    r"\b(personal|individual|family|consumer|lifestyle|home|shop|buy|order|subscribe|free\s+trial|your\s+account)\b",
    re.IGNORECASE,
)


def _extract_industry_tags(text: str) -> frozenset:
    text_lower = text.lower()
    return frozenset(
        tag
        for tag, keywords in _INDUSTRY_KEYWORDS.items()
        if any(kw in text_lower for kw in keywords)
    )


def _detect_b2b(text: str) -> bool:
    return len(_B2B_RE.findall(text)) >= len(_B2C_RE.findall(text))


def _infer_size_tier(signals: dict) -> str:
    """Infer company size from available signals.

    startup  — no careers page (very small or pre-scale)
    smb      — has careers page (actively hiring, structured team)
    """
    return "smb" if signals.get("has_careers_page") else "startup"


# --- Profile dataclass --------------------------------------------------------

@dataclass(frozen=True)
class CompanyProfile:
    """Extracted fingerprint of a company, derived from its public website."""
    domain: str
    title: str
    description: str
    has_pricing_page: bool
    has_careers_page: bool
    saas_tools: frozenset        # set of lowercase tool names
    industry_tags: frozenset     # set of industry category strings
    size_tier: str               # "startup" | "smb" | "unknown"
    is_b2b: bool


def _signals_to_profile(signals: dict) -> CompanyProfile:
    text = f"{signals.get('title', '')} {signals.get('description', '')}"
    return CompanyProfile(
        domain=signals.get("domain", ""),
        title=signals.get("title", ""),
        description=signals.get("description", ""),
        has_pricing_page=signals.get("has_pricing_page", False),
        has_careers_page=signals.get("has_careers_page", False),
        saas_tools=frozenset(signals.get("saas_tools_detected", [])),
        industry_tags=_extract_industry_tags(text),
        size_tier=_infer_size_tier(signals),
        is_b2b=_detect_b2b(text),
    )


# --- Similarity computation ---------------------------------------------------

def _jaccard(a: frozenset, b: frozenset) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _profile_similarity(visitor: CompanyProfile, client: CompanyProfile) -> float:
    """Weighted similarity between two profiles. Returns 0.0–1.0."""
    tech_sim     = _jaccard(visitor.saas_tools, client.saas_tools)
    industry_sim = _jaccard(visitor.industry_tags, client.industry_tags)
    size_sim     = 1.0 if visitor.size_tier == client.size_tier else 0.3
    b2b_sim      = 1.0 if visitor.is_b2b == client.is_b2b else 0.0

    return (
        0.40 * tech_sim +
        0.35 * industry_sim +
        0.15 * size_sim +
        0.10 * b2b_sim
    )


# --- Public API ---------------------------------------------------------------

async def profile_company(url: str) -> Optional[CompanyProfile]:
    """
    Fetch a company URL and return its CompanyProfile.

    Returns None on fetch failure — callers should handle gracefully.
    """
    signals = await enrich_company_url(url)
    if not signals:
        return None
    return _signals_to_profile(signals)


async def load_client_profiles(urls: list[str]) -> list[CompanyProfile]:
    """
    Fetch and profile a list of client URLs in parallel.

    Call this once at startup and cache the result.
    Failed URLs are silently skipped.

    Args:
        urls: List of client company website URLs.

    Returns:
        List of CompanyProfile — one per successfully fetched URL.
    """
    results = await asyncio.gather(
        *[profile_company(url) for url in urls],
        return_exceptions=True,
    )
    profiles = [r for r in results if isinstance(r, CompanyProfile)]
    logger.info("Loaded %d/%d client profiles", len(profiles), len(urls))
    return profiles


def compute_client_similarity(
    visitor_signals: dict,
    client_profiles: list[CompanyProfile],
) -> int:
    """
    Score a visitor's company by similarity to your existing client profiles.

    Returns a point contribution of 0–30, suitable for passing as
    client_similarity_score= to compute_icp_score().

    Similarity is computed as a weighted average across all client profiles:
      40% tech stack overlap (Jaccard)
      35% industry tag overlap (Jaccard)
      15% company size tier match
      10% B2B / B2C orientation match

    Args:
        visitor_signals: Output of enrich_company_url() for the visitor's company.
        client_profiles: Output of load_client_profiles() — your known clients.

    Returns:
        Integer in [0, 30]. Returns 0 if no client profiles are loaded.
    """
    if not client_profiles or not visitor_signals:
        return 0

    visitor = _signals_to_profile(visitor_signals)
    scores = [_profile_similarity(visitor, cp) for cp in client_profiles]
    avg = sum(scores) / len(scores)
    return round(avg * 30)
