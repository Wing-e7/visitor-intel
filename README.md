# visitor-intel

Know if the visitor on your B2B website matches your ICP — from their IP address and behavioral signals. No LLM required. No API key for basic usage. Sub-millisecond per visitor.

```python
import asyncio
from visitor_intel import (
    fetch_company_intel, classify_ai_source,
    enrich_company_url, company_signals_to_score,
    score_linkedin,
    load_client_profiles, compute_client_similarity,
    compute_icp_score, score_to_fit_tier, derive_channel,
)

async def main():
    # Load your existing client profiles once at startup
    client_profiles = await load_client_profiles([
        "https://stripe.com", "https://notion.so", "https://figma.com",
    ])

    # Signals from the visitor's browser
    company      = await fetch_company_intel("203.0.113.42")
    ai_referrer  = classify_ai_source("https://chatgpt.com/c/abc123")

    # Optional: visitor shared their company URL or LinkedIn via a form/chat
    company_signals  = await enrich_company_url("https://acmecorp.com")
    url_score        = company_signals_to_score(company_signals)
    li_score         = score_linkedin("https://linkedin.com/in/jane-doe", job_title="VP of Sales")
    similarity_score = compute_client_similarity(company_signals, client_profiles)

    score = compute_icp_score(
        company_identified=company["company_identified"],
        utm_source="linkedin",
        ai_referrer=ai_referrer,
        page_type="pricing",
        time_on_page_sec=90,
        scroll_depth_pct=80,
        cta_clicked=True,
        pages_visited=3,
        is_returning=False,
        company_url_score=url_score,
        linkedin_score=li_score,
        client_similarity_score=similarity_score,
    )
    print(score_to_fit_tier(score))  # "icp_fit"
    print(derive_channel("linkedin", None, None))  # "LinkedIn Ads"

asyncio.run(main())
```

---

## Why

Every B2B website has visitors that never convert. Most of them are unqualified — but you can't tell which until it's too late or until you pay Clearbit $500/mo.

This library gives you:

- **Company identification** from IP — is this a real business, or a residential/ISP connection?
- **ISP/cloud filtering** — 40+ ISP and cloud provider patterns stripped automatically
- **Company website enrichment** — pricing page, hiring signals, SaaS stack — from their URL, zero scraping APIs
- **LinkedIn scoring** — person vs. company URL, seniority detection, no scraping
- **Client-similarity ICP scoring** — define your ICP by your existing clients, not generic rules
- **AI referral detection** — did this visitor come from ChatGPT, Perplexity, Claude?
- **Rule-based composite scoring** — 9-signal score, 0–100, zero LLM cost
- **Channel normalization** — UTM + referrer → clean display name

---

## Install

```bash
pip install visitor-intel
```

Requires Python 3.9+. The only dependency is `httpx`.

---

## Usage

### 1. Identify the company from IP

```python
import asyncio
from visitor_intel import fetch_company_intel

async def main():
    result = await fetch_company_intel("203.0.113.42")
    print(result)
    # {
    #   "company_identified": True,
    #   "company_name": "Acme Corp",
    #   "company_domain": "",       # populated if you pass ipinfo_token
    #   "city": "San Francisco",
    #   "country": "US",
    # }

asyncio.run(main())
```

**With IPinfo (higher accuracy):**

```python
result = await fetch_company_intel("203.0.113.42", ipinfo_token="your_token_here")
# company_domain is now populated, company.type == "business" check applied
```

Free tier: ip-api.com, 1000 requests/day, no sign-up. Upgrade path: pass your [IPinfo token](https://ipinfo.io/signup) for business-type filtering and domain resolution.

---

### 2. Detect AI referrals

```python
from visitor_intel import classify_ai_source

source = classify_ai_source("https://chatgpt.com/c/abc123")
# "chatgpt"

source = classify_ai_source("https://perplexity.ai/search?q=b2b+sales+tools")
# "perplexity"

source = classify_ai_source("https://google.com")
# None
```

Supported: ChatGPT, Perplexity, Claude, Copilot, Gemini, You.com, Phind.

---

### 3. Enrich from company URL

When a visitor shares their company website (via a form or chat), fetch ICP signals from it — no API key or scraping service required.

```python
from visitor_intel import enrich_company_url, company_signals_to_score

signals = await enrich_company_url("https://acmecorp.com")
# {
#   "title": "Acme Corp — B2B Workflow Automation",
#   "description": "The platform for modern revenue teams.",
#   "has_pricing_page": True,
#   "has_careers_page": True,
#   "saas_tools_detected": ["hubspot", "intercom", "stripe"],
#   "domain": "acmecorp.com",
# }

score = company_signals_to_score(signals)  # 0–25
```

Points from `company_signals_to_score`:

| Signal | Points |
|--------|--------|
| Pricing page found | +10 |
| Careers page found (growing team) | +5 |
| SaaS tools detected in stack | +5 |
| Company description present | +5 |

---

### 4. Score a LinkedIn URL

When a visitor shares their LinkedIn profile (via a form or chat), extract intent and seniority signals without scraping.

```python
from visitor_intel import parse_linkedin_url, score_linkedin

# Parse the URL type and handle
parsed = parse_linkedin_url("https://linkedin.com/in/jane-doe")
# {"valid": True, "type": "person", "handle": "jane-doe"}

parsed = parse_linkedin_url("https://linkedin.com/company/acmecorp")
# {"valid": True, "type": "company", "handle": "acmecorp"}

# Score it (0–20)
score = score_linkedin("https://linkedin.com/in/jane-doe", job_title="VP of Sales")
# 20 — decision-maker title detected

score = score_linkedin("https://linkedin.com/in/jane-doe")
# 10 — personal URL, no title info

score = score_linkedin("https://linkedin.com/company/acmecorp")
# 5 — company page URL

score = score_linkedin(None)
# 0 — no URL
```

Decision-maker titles detected: CEO, CTO, CMO, COO, CFO, CPO, Founder, Co-Founder, VP, Vice President, Director, Head of, President, Owner, Partner, Managing Director, GM.

---

### 5. Client-similarity scoring

Instead of generic scoring rules, define your ICP by the companies you've already won. The library fingerprints each client (tech stack, industry, size tier, B2B orientation) and scores new visitors by similarity.

```python
from visitor_intel import (
    load_client_profiles, compute_client_similarity,
    enrich_company_url,
)

# --- At startup (call once, cache the result) ---
client_profiles = await load_client_profiles([
    "https://stripe.com",
    "https://notion.so",
    "https://figma.com",
])

# --- Per visitor (when you have their company URL) ---
visitor_signals = await enrich_company_url("https://newvisitor.com")
similarity_score = compute_client_similarity(visitor_signals, client_profiles)
# Returns 0–30, pass as client_similarity_score= to compute_icp_score()
```

Similarity weights:

| Dimension | Weight |
|-----------|--------|
| Tech stack overlap (Jaccard) | 40% |
| Industry tag overlap (Jaccard) | 35% |
| Company size tier match | 15% |
| B2B / B2C orientation match | 10% |

Industries detected: SaaS, fintech, healthcare, e-commerce, marketing, HR, security, legal, logistics, edtech.

You can also inspect a single company's profile:

```python
from visitor_intel import profile_company, CompanyProfile

profile = await profile_company("https://acmecorp.com")
# CompanyProfile(
#   domain="acmecorp.com",
#   has_pricing_page=True,
#   has_careers_page=True,
#   saas_tools=frozenset({"hubspot", "stripe"}),
#   industry_tags=frozenset({"saas", "marketing"}),
#   size_tier="smb",
#   is_b2b=True,
# )
```

---

### 6. Score the visitor

```python
from visitor_intel import compute_icp_score, score_to_fit_tier

score = compute_icp_score(
    company_identified=True,          # from fetch_company_intel()
    utm_source="linkedin",            # from URL params
    ai_referrer="chatgpt",            # from classify_ai_source()
    page_type="pricing",              # which page they landed on
    time_on_page_sec=90,              # seconds on page
    scroll_depth_pct=80,              # % of page scrolled
    cta_clicked=True,                 # clicked your primary CTA
    pages_visited=3,                  # pages this session
    is_returning=True,                # repeat visitor
    company_url_score=url_score,      # from company_signals_to_score()
    linkedin_score=li_score,          # from score_linkedin()
    client_similarity_score=sim_score,# from compute_client_similarity()
)

tier = score_to_fit_tier(score)
# "icp_fit"   → score ≥ 70
# "potential" → score ≥ 50
# "low_fit"   → score < 50
```

All signals are optional. Missing/None values score zero for that signal.

---

### 7. Normalize the channel

```python
from visitor_intel import derive_channel

derive_channel("linkedin", None, None)
# "LinkedIn Ads"

derive_channel(None, "chatgpt", None)
# "ChatGPT"

derive_channel(None, None, "https://google.com/search?q=visitor+intelligence")
# "Organic"

derive_channel(None, None, None)
# "Direct"
```

---

## Score breakdown

| Signal | Points | Condition |
|--------|--------|-----------|
| Company identified | +20 | Business IP detected |
| Traffic source | +15 | LinkedIn / Google Ads |
| | +10 | Organic / SEO |
| | +8 | Other UTM |
| | +5 | Direct (no UTM) |
| AI referral | +10 | ChatGPT / Perplexity / Claude / etc. |
| Page type | +20 | Pricing |
| | +15 | Product / Features |
| | +10 | Docs / Technical |
| | +5 | Other |
| Time on page | +10 | ≥60 seconds |
| | +5 | ≥30 seconds |
| Scroll depth | +10 | ≥70% scrolled |
| CTA clicked | +15 | Primary CTA clicked |
| Pages visited | +15 | 3+ pages this session |
| | +10 | 2 pages this session |
| Returning visitor | +10 | Known repeat visitor |
| **Company URL** | **+10** | **Pricing page found on their site** |
| | **+5** | **Careers page found (growing team)** |
| | **+5** | **B2B SaaS tools detected in their stack** |
| | **+5** | **Company description present** |
| **LinkedIn** | **+20** | **Personal URL + decision-maker title** |
| | **+10** | **Personal URL (any title)** |
| | **+5** | **Company page URL** |
| **Client similarity** | **+0–30** | **Weighted fingerprint match against your known clients** |

Maximum: 100 (capped). Company URL, LinkedIn, and client similarity signals are optional — pass 0 if not available.

---

## Running the example

```bash
git clone https://github.com/Wing-e7/visitor-intel
cd visitor-intel
pip install -e ".[dev]"
python examples/quickstart.py
```

---

## Running tests

```bash
pytest tests/ -v
```

No network calls required — all tests are synchronous unit tests against the scoring and normalization logic.

---

## Architecture

```
visitor-intel/
  visitor_intel/
    ip_enrichment.py      # fetch_ip_intel, fetch_company_intel, classify_ai_source
    company_enrichment.py # enrich_company_url, company_signals_to_score
    linkedin.py           # parse_linkedin_url, score_linkedin
    icp_profile.py        # CompanyProfile, profile_company, load_client_profiles, compute_client_similarity
    scoring.py            # compute_icp_score, score_to_fit_tier
    channel.py            # derive_channel
  examples/
    quickstart.py
  tests/
    test_scoring.py
    test_company_enrichment.py
    test_linkedin.py
    test_icp_profile.py
```

No framework. No ORM. No config files. Plain async Python + httpx.

---

## What it doesn't do

- No LLM calls (zero marginal cost per visitor)
- No enrichment beyond what IP + behavioral signals give you
- No storage (bring your own DB)
- No real-time webhook delivery (wire it into your own stack)

For the full experience — AI-powered visitor scoring, voice conversation, and CRM handoff — see [Percepto AI](https://www.perceptoai.com).

---

## Contributing

PRs welcome. Open an issue first for anything beyond a small fix.

---

## License

MIT © [Percepto AI](https://perceptoai.com)
