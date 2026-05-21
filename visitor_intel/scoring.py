"""
Rule-based ICP fit scoring. Zero LLM calls — sub-millisecond per visitor.

Score breakdown (max 100):
  company_identified   +20   Business IP detected
  traffic_source       +5–15 LinkedIn/Google Ads > organic > direct > other
  ai_referral          +10   Arrived from ChatGPT, Perplexity, etc.
  page_type            +5–20 Pricing > product/features > docs > other
  time_on_page         +5–10 ≥30s or ≥60s
  scroll_depth         +10   ≥70% of page scrolled
  cta_clicked          +15   Clicked a primary CTA
  pages_visited        +10–15 2+ or 3+ pages this session
  is_returning         +10   Known repeat visitor
  company_url_score       +0–25 From company_signals_to_score() — pricing/careers/SaaS stack
  linkedin_score          +0–20 From score_linkedin() — person/company URL + seniority
  client_similarity_score +0–30 From compute_client_similarity() — how closely visitor's
                                 company matches your existing client profiles
"""
from typing import Optional


_TIER_THRESHOLDS = (70, 50)  # (icp_fit, potential) — below both → low_fit


def compute_icp_score(
    company_identified: bool,
    utm_source: Optional[str],
    ai_referrer: Optional[str],
    page_type: Optional[str],
    time_on_page_sec: Optional[int],
    scroll_depth_pct: Optional[int],
    cta_clicked: Optional[bool],
    pages_visited: int,
    is_returning: bool,
    company_url_score: int = 0,
    linkedin_score: int = 0,
    client_similarity_score: int = 0,
) -> int:
    """
    Compute an ICP fit score 0–100 from behavioral + source signals.

    All arguments are optional except pages_visited and is_returning.
    Missing/None values are treated as absence of the signal (no score added).

    Args:
        company_identified:  True if fetch_company_intel() returned a business IP.
        utm_source:          UTM source param from landing URL.
        ai_referrer:         classify_ai_source() output, or None.
        page_type:           First page the visitor landed on
                             ("pricing", "product", "features", "docs", "technical", …).
        time_on_page_sec:    Seconds the visitor spent on the current page.
        scroll_depth_pct:    Percentage of page scrolled (0–100).
        cta_clicked:         True if visitor clicked a primary call-to-action.
        pages_visited:       Number of pages visited this session.
        is_returning:        True if visitor has visited before.
        company_url_score:        Points from company_signals_to_score() after calling
                                  enrich_company_url(). Pass 0 if not available.
        linkedin_score:           Points from score_linkedin(). Pass 0 if not available.
        client_similarity_score:  Points from compute_client_similarity() — how closely
                                  the visitor's company matches your known client profiles.
                                  Pass 0 if no client profiles are loaded.

    Returns:
        Integer score in [0, 100].
    """
    score = 0

    if company_identified:
        score += 20

    src = (utm_source or "").lower()
    if "linkedin" in src or "google" in src or "adwords" in src:
        score += 15
    elif src in ("organic", "seo"):
        score += 10
    elif not src:
        score += 5
    else:
        score += 8

    if ai_referrer:
        score += 10

    page = (page_type or "").lower()
    if page == "pricing":
        score += 20
    elif page in ("product", "features"):
        score += 15
    elif page in ("docs", "technical"):
        score += 10
    else:
        score += 5

    if time_on_page_sec and time_on_page_sec >= 60:
        score += 10
    elif time_on_page_sec and time_on_page_sec >= 30:
        score += 5

    if scroll_depth_pct and scroll_depth_pct >= 70:
        score += 10

    if cta_clicked:
        score += 15

    if pages_visited >= 3:
        score += 15
    elif pages_visited >= 2:
        score += 10

    if is_returning:
        score += 10

    score += company_url_score
    score += linkedin_score
    score += client_similarity_score

    return min(score, 100)


def score_to_fit_tier(score: int) -> str:
    """
    Map a numeric ICP score to a named tier.

    Returns:
        "icp_fit"   score ≥ 70
        "potential" score ≥ 50
        "low_fit"   score < 50
    """
    high, mid = _TIER_THRESHOLDS
    if score >= high:
        return "icp_fit"
    if score >= mid:
        return "potential"
    return "low_fit"
