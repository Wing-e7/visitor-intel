import pytest
from visitor_intel.scoring import compute_icp_score, score_to_fit_tier
from visitor_intel.channel import derive_channel
from visitor_intel.ip_enrichment import classify_ai_source, _sanitise_org


def test_perfect_icp_visitor():
    score = compute_icp_score(
        company_identified=True,
        utm_source="linkedin",
        ai_referrer=None,
        page_type="pricing",
        time_on_page_sec=90,
        scroll_depth_pct=80,
        cta_clicked=True,
        pages_visited=4,
        is_returning=True,
    )
    assert score == 100


def test_low_intent_visitor():
    score = compute_icp_score(
        company_identified=False,
        utm_source=None,
        ai_referrer=None,
        page_type="blog",
        time_on_page_sec=5,
        scroll_depth_pct=10,
        cta_clicked=False,
        pages_visited=1,
        is_returning=False,
    )
    assert score < 30


def test_ai_referral_bonus():
    without_ai = compute_icp_score(
        company_identified=False, utm_source=None, ai_referrer=None,
        page_type="product", time_on_page_sec=60, scroll_depth_pct=50,
        cta_clicked=False, pages_visited=1, is_returning=False,
    )
    with_ai = compute_icp_score(
        company_identified=False, utm_source=None, ai_referrer="chatgpt",
        page_type="product", time_on_page_sec=60, scroll_depth_pct=50,
        cta_clicked=False, pages_visited=1, is_returning=False,
    )
    assert with_ai == without_ai + 10


def test_score_to_fit_tier():
    assert score_to_fit_tier(70) == "icp_fit"
    assert score_to_fit_tier(80) == "icp_fit"
    assert score_to_fit_tier(69) == "potential"
    assert score_to_fit_tier(50) == "potential"
    assert score_to_fit_tier(49) == "low_fit"
    assert score_to_fit_tier(0) == "low_fit"


def test_classify_ai_source():
    assert classify_ai_source("https://chatgpt.com/c/abc") == "chatgpt"
    assert classify_ai_source("https://perplexity.ai/search?q=foo") == "perplexity"
    assert classify_ai_source("https://google.com") is None
    assert classify_ai_source(None) is None


def test_derive_channel_utm_priority():
    assert derive_channel("linkedin", None, None) == "LinkedIn Ads"
    assert derive_channel("google", None, None) == "Google Ads"
    assert derive_channel("facebook", None, None) == "Meta Ads"


def test_derive_channel_ai_referrer():
    assert derive_channel(None, "chatgpt", None) == "ChatGPT"
    assert derive_channel(None, "perplexity", None) == "Perplexity"


def test_derive_channel_organic():
    assert derive_channel(None, None, "https://google.com/search?q=test") == "Organic"


def test_derive_channel_direct():
    assert derive_channel(None, None, None) == "Direct"


def test_sanitise_org_isp():
    assert _sanitise_org("Airtel Broadband") == ""
    assert _sanitise_org("Jio Platforms") == ""
    assert _sanitise_org("Amazon AWS") == ""
    assert _sanitise_org("Acme Corp") == "Acme Corp"
    assert _sanitise_org("") == ""


def test_score_capped_at_100():
    score = compute_icp_score(
        company_identified=True, utm_source="linkedin", ai_referrer="chatgpt",
        page_type="pricing", time_on_page_sec=120, scroll_depth_pct=100,
        cta_clicked=True, pages_visited=10, is_returning=True,
    )
    assert score == 100
