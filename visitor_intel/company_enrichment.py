"""
Company website enrichment.

Fetch a company's URL and extract ICP-relevant signals:
  - Has a publicly visible pricing page (high-intent signal)
  - Has careers/jobs page (team is growing)
  - Uses B2B SaaS tools (HubSpot, Salesforce, Zendesk…) — your ICP pays for software
  - Has a legible company description

No external dependencies beyond httpx. Uses stdlib html.parser.
"""
import logging
import re
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

_SAAS_TOOLS = re.compile(
    r"hubspot|salesforce|marketo|pardot|intercom|zendesk|"
    r"segment|amplitude|mixpanel|heap|fullstory|hotjar|"
    r"drift|qualified|clearbit|apollo|outreach|salesloft|"
    r"stripe|chargebee|recurly|paddle",
    re.IGNORECASE,
)

_PRICING_PATHS = re.compile(r"/pric(?:ing|es?)\b", re.IGNORECASE)
_CAREERS_PATHS = re.compile(r"/(?:careers?|jobs?|join|hiring|work-with-us)\b", re.IGNORECASE)


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.links: list[str] = []
        self.scripts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and attrs.get("name", "").lower() == "description":
            self.description = attrs.get("content", "")
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        elif tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


async def enrich_company_url(
    url: str,
    timeout: float = 5.0,
) -> dict:
    """
    Fetch a company website and extract ICP scoring signals.

    Returns a dict suitable for passing to company_signals_to_score().
    Returns an empty dict on any fetch/parse failure — callers should handle gracefully.

    Args:
        url:     Company website URL (e.g. "https://acmecorp.com").
        timeout: Request timeout in seconds.

    Returns:
        {
            "title": str,
            "description": str,
            "has_pricing_page": bool,
            "has_careers_page": bool,
            "saas_tools_detected": list[str],
            "domain": str,
        }
    """
    if not url:
        return {}

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; visitor-intel/0.1)"},
        ) as client:
            r = await client.get(url)
            html = r.text
    except Exception as exc:
        logger.warning("enrich_company_url fetch failed for %s: %s", url, exc)
        return {}

    parser = _PageParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    base = urlparse(url)
    domain = base.netloc

    # Resolve relative hrefs to absolute, check paths
    all_hrefs = [urljoin(url, h) for h in parser.links]
    all_paths = " ".join(urlparse(h).path for h in all_hrefs)
    all_scripts = " ".join(parser.scripts)

    has_pricing = bool(_PRICING_PATHS.search(all_paths))
    has_careers = bool(_CAREERS_PATHS.search(all_paths))

    tools: list[str] = []
    for match in _SAAS_TOOLS.finditer(all_scripts + " " + html[:8000]):
        name = match.group(0).lower()
        if name not in tools:
            tools.append(name)

    return {
        "title": parser.title.strip(),
        "description": parser.description.strip(),
        "has_pricing_page": has_pricing,
        "has_careers_page": has_careers,
        "saas_tools_detected": tools,
        "domain": domain,
    }


def company_signals_to_score(signals: dict) -> int:
    """
    Convert enrich_company_url() output to a point contribution (0–25).

    Points:
      +10  Pricing page detected  (they think about pricing = real B2B business)
      +5   Careers page detected  (actively hiring = growing team)
      +5   SaaS tools detected    (uses paid software = likely your ICP)
      +5   Description present    (legible company = real business)
    """
    if not signals:
        return 0

    score = 0
    if signals.get("has_pricing_page"):
        score += 10
    if signals.get("has_careers_page"):
        score += 5
    if signals.get("saas_tools_detected"):
        score += 5
    if signals.get("description"):
        score += 5
    return score
