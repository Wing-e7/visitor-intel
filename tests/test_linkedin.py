from visitor_intel.linkedin import parse_linkedin_url, score_linkedin


def test_parse_person_url():
    result = parse_linkedin_url("https://www.linkedin.com/in/john-doe")
    assert result == {"valid": True, "type": "person", "handle": "john-doe"}


def test_parse_company_url():
    result = parse_linkedin_url("https://linkedin.com/company/acmecorp")
    assert result == {"valid": True, "type": "company", "handle": "acmecorp"}


def test_parse_invalid_url():
    result = parse_linkedin_url("https://example.com/profile")
    assert result["valid"] is False


def test_parse_none():
    result = parse_linkedin_url(None)
    assert result["valid"] is False


def test_score_person_no_title():
    assert score_linkedin("https://linkedin.com/in/jane-smith") == 10


def test_score_person_decision_maker():
    assert score_linkedin("https://linkedin.com/in/jane-smith", job_title="VP of Sales") == 20
    assert score_linkedin("https://linkedin.com/in/jane-smith", job_title="CEO") == 20
    assert score_linkedin("https://linkedin.com/in/jane-smith", job_title="Co-Founder") == 20
    assert score_linkedin("https://linkedin.com/in/jane-smith", job_title="Head of Growth") == 20
    assert score_linkedin("https://linkedin.com/in/jane-smith", job_title="Director of Engineering") == 20


def test_score_person_non_decision_maker():
    assert score_linkedin("https://linkedin.com/in/jane-smith", job_title="Software Engineer") == 10
    assert score_linkedin("https://linkedin.com/in/jane-smith", job_title="Account Executive") == 10


def test_score_company_url():
    assert score_linkedin("https://linkedin.com/company/acme") == 5


def test_score_invalid_url():
    assert score_linkedin("not-a-linkedin-url") == 0
    assert score_linkedin(None) == 0
