from visitor_intel.company_enrichment import company_signals_to_score


def test_full_signals():
    signals = {
        "has_pricing_page": True,
        "has_careers_page": True,
        "saas_tools_detected": ["hubspot"],
        "description": "We make great software.",
        "domain": "acme.com",
    }
    assert company_signals_to_score(signals) == 25


def test_pricing_only():
    signals = {
        "has_pricing_page": True,
        "has_careers_page": False,
        "saas_tools_detected": [],
        "description": "",
        "domain": "acme.com",
    }
    assert company_signals_to_score(signals) == 10


def test_empty_signals():
    assert company_signals_to_score({}) == 0


def test_no_saas_tools():
    signals = {
        "has_pricing_page": True,
        "has_careers_page": True,
        "saas_tools_detected": [],
        "description": "Company description here.",
        "domain": "acme.com",
    }
    assert company_signals_to_score(signals) == 20


def test_score_feeds_into_icp_score():
    from visitor_intel.scoring import compute_icp_score

    base = compute_icp_score(
        company_identified=False, utm_source=None, ai_referrer=None,
        page_type="other", time_on_page_sec=0, scroll_depth_pct=0,
        cta_clicked=False, pages_visited=1, is_returning=False,
    )
    enriched = compute_icp_score(
        company_identified=False, utm_source=None, ai_referrer=None,
        page_type="other", time_on_page_sec=0, scroll_depth_pct=0,
        cta_clicked=False, pages_visited=1, is_returning=False,
        company_url_score=25,
        linkedin_score=20,
    )
    assert enriched == min(base + 45, 100)
