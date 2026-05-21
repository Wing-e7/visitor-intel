"""
IP enrichment utilities.

- fetch_ip_intel:     Resolve IP → company/geo data via ip-api.com (free, 1000 req/day)
- fetch_company_intel: Identify if a visitor is from a real business (not ISP/cloud/VPN)
- classify_ai_source: Detect ChatGPT / Perplexity / Claude referrals
"""
import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Matches ISP, telco, cloud providers, and ASN strings that are NOT real companies.
_ISP_RE = re.compile(
    r"airtel|jio|comcast|at&t|\batt\b|verizon|vodafone|bsnl|"
    r"tata\s+telecom|spectrum|xfinity|charter|"
    r"t-mobile|sprint|bt\s+group|deutsche\s+telekom|orange|telefonica|"
    r"reliance|tele2|telia|bouygues|swisscom|telus|bell\s+canada|rogers|"
    r"shaw|cogeco|videotron|wind|three|o2|sky\s+broadband|virgin\s+media|"
    r"talktalk|plusnet|ee\s+limited|kpn|proximus|base\s+company|entel|claro|"
    r"oi\s+telecom|tim\s+brasil|cloudflare|amazon|digitalocean|linode|"
    r"vultr|hetzner|ovh|leaseweb|fastly|akamai|cloudfront|"
    r"telecom|broadband|wireless|fiber|fibre|cable|\bisp\b|"
    r"as\d{4,}",
    re.IGNORECASE,
)

_AI_REFERRER_MAP = {
    "chatgpt.com": "chatgpt",
    "chat.openai.com": "chatgpt",
    "perplexity.ai": "perplexity",
    "claude.ai": "claude",
    "copilot.microsoft.com": "copilot",
    "gemini.google.com": "gemini",
    "bard.google.com": "gemini",
    "you.com": "you",
    "phind.com": "phind",
    "bing.com": "copilot",
}

_IP_API_URL = "http://ip-api.com/json"
_IP_API_FIELDS = "status,country,countryCode,city,isp,org,as,query"


def _sanitise_org(org: str, isp: str = "") -> str:
    """Return empty string if org looks like an ISP, cloud provider, or ASN."""
    if not org:
        return ""
    if _ISP_RE.search(org):
        return ""
    if isp and org.lower().strip() == isp.lower().strip():
        return ""
    return org


async def fetch_ip_intel(
    ip: str,
    api_url: str = _IP_API_URL,
    timeout: float = 2.0,
) -> dict:
    """
    Resolve an IP address to company/geo data using ip-api.com.

    Free tier: 1000 requests/day, no API key required.
    Returns an empty dict on failure — callers should handle gracefully.

    Args:
        ip:      IPv4 or IPv6 address string.
        api_url: Base URL for the IP lookup API. Defaults to ip-api.com.
                 Must support ?fields= query param in ip-api.com format.
        timeout: Request timeout in seconds.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(
                f"{api_url}/{ip}",
                params={"fields": _IP_API_FIELDS},
            )
            return r.json()
    except Exception as exc:
        logger.warning("IP lookup failed for %s: %s", ip, exc)
        return {}


async def fetch_company_intel(
    ip: str,
    ipinfo_token: str = "",
    timeout: float = 2.0,
) -> dict:
    """
    Identify whether a visitor is from a real business vs. ISP/VPN/cloud.

    Two modes:
      - With ipinfo_token: calls IPinfo.io (company.type == 'business' check).
        Higher accuracy; requires a paid/free IPinfo account.
      - Without token: falls back to ip-api.com org field + ISP filtering.
        No API key needed; works for most B2B use cases.

    Returns:
        {
            "company_identified": bool,
            "company_name": str,       # empty string if ISP/residential
            "company_domain": str,     # only available via IPinfo
            "city": str,
            "country": str,            # two-letter ISO code
        }
    """
    if ipinfo_token:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(
                    f"https://ipinfo.io/{ip}",
                    params={"token": ipinfo_token},
                )
                data = r.json()
            company = data.get("company") or {}
            ctype = company.get("type", "")
            cname = company.get("name", "")
            cdomain = company.get("domain", "")
            identified = ctype == "business" and bool(cname)
            return {
                "company_identified": identified,
                "company_name": cname if identified else "",
                "company_domain": cdomain if identified else "",
                "city": data.get("city", ""),
                "country": data.get("country", ""),
            }
        except Exception as exc:
            logger.warning("IPinfo lookup failed: %s", exc)

    ip_data = await fetch_ip_intel(ip)
    org = _sanitise_org(ip_data.get("org", ""), ip_data.get("isp", ""))
    return {
        "company_identified": bool(org),
        "company_name": org,
        "company_domain": "",
        "city": ip_data.get("city", ""),
        "country": ip_data.get("country", ""),
    }


def classify_ai_source(referrer: Optional[str]) -> Optional[str]:
    """
    Detect if a visitor arrived from an AI platform (ChatGPT, Perplexity, etc.).

    Returns a lowercase platform key ("chatgpt", "perplexity", "claude", …)
    or None if the referrer is not an AI source.

    Example:
        >>> classify_ai_source("https://chatgpt.com/c/abc123")
        'chatgpt'
        >>> classify_ai_source("https://google.com")
        None
    """
    if not referrer:
        return None
    ref = referrer.lower()
    for domain, platform in _AI_REFERRER_MAP.items():
        if domain in ref:
            return platform
    return None
