import pytest
from visitor_intel.icp_profile import (
    _signals_to_profile,
    _profile_similarity,
    compute_client_similarity,
)


def _make_signals(**kwargs):
    base = {
        "domain": "example.com",
        "title": "Acme — B2B SaaS platform",
        "description": "We help enterprise teams manage workflows.",
        "has_pricing_page": True,
        "has_careers_page": True,
        "saas_tools_detected": ["hubspot", "segment"],
    }
    base.update(kwargs)
    return base


def test_profile_b2b_detection():
    p = _signals_to_profile(_make_signals(
        description="We help enterprise teams manage business workflows and integrations."
    ))
    assert p.is_b2b is True


def test_profile_b2c_detection():
    p = _signals_to_profile(_make_signals(
        description="Shop online and buy personal lifestyle products for your family at home."
    ))
    assert p.is_b2b is False


def test_profile_industry_tags():
    p = _signals_to_profile(_make_signals(
        title="SaaS analytics platform",
        description="Marketing analytics software for teams.",
    ))
    assert "saas" in p.industry_tags or "marketing" in p.industry_tags


def test_profile_size_tier_startup():
    p = _signals_to_profile(_make_signals(has_careers_page=False))
    assert p.size_tier == "startup"


def test_profile_size_tier_smb():
    p = _signals_to_profile(_make_signals(has_careers_page=True))
    assert p.size_tier == "smb"


def test_identical_profiles_max_similarity():
    signals = _make_signals()
    a = _signals_to_profile(signals)
    score = _profile_similarity(a, a)
    assert score == pytest.approx(1.0, abs=0.01)


def test_completely_different_profiles_low_similarity():
    a = _signals_to_profile(_make_signals(
        description="B2B enterprise SaaS workflow integration platform.",
        saas_tools_detected=["salesforce", "hubspot"],
        has_careers_page=True,
    ))
    b = _signals_to_profile(_make_signals(
        title="Family home goods shop",
        description="Buy personal lifestyle products online for your family.",
        saas_tools_detected=[],
        has_careers_page=False,
    ))
    score = _profile_similarity(a, b)
    assert score < 0.4


def test_compute_client_similarity_no_profiles():
    assert compute_client_similarity(_make_signals(), []) == 0


def test_compute_client_similarity_empty_signals():
    from visitor_intel.icp_profile import _signals_to_profile
    profile = _signals_to_profile(_make_signals())
    assert compute_client_similarity({}, [profile]) == 0


def test_compute_client_similarity_identical():
    signals = _make_signals()
    from visitor_intel.icp_profile import _signals_to_profile
    profile = _signals_to_profile(signals)
    score = compute_client_similarity(signals, [profile])
    assert score == 30  # max contribution


def test_similarity_feeds_into_icp_score():
    from visitor_intel.scoring import compute_icp_score

    base = compute_icp_score(
        company_identified=False, utm_source=None, ai_referrer=None,
        page_type="other", time_on_page_sec=0, scroll_depth_pct=0,
        cta_clicked=False, pages_visited=1, is_returning=False,
    )
    with_similarity = compute_icp_score(
        company_identified=False, utm_source=None, ai_referrer=None,
        page_type="other", time_on_page_sec=0, scroll_depth_pct=0,
        cta_clicked=False, pages_visited=1, is_returning=False,
        client_similarity_score=30,
    )
    assert with_similarity == min(base + 30, 100)
