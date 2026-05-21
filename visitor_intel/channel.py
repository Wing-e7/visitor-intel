"""Normalise UTM / referrer signals into a human-readable channel name."""
from typing import Optional


_ORGANIC_DOMAINS = ("google.", "bing.", "yahoo.", "duckduckgo.", "ecosia.")


def derive_channel(
    utm_source: Optional[str],
    ai_referrer: Optional[str],
    referrer: Optional[str],
) -> str:
    """
    Return a display-friendly channel name from UTM/referrer data.

    Priority: utm_source → ai_referrer → organic search → Direct

    Examples:
        >>> derive_channel("linkedin", None, None)
        'LinkedIn Ads'
        >>> derive_channel(None, "chatgpt", None)
        'ChatGPT'
        >>> derive_channel(None, None, "https://google.com/search?q=percepto")
        'Organic'
        >>> derive_channel(None, None, None)
        'Direct'
    """
    if utm_source:
        src = utm_source.lower()
        if "linkedin" in src:
            return "LinkedIn Ads"
        if "google" in src or "adwords" in src:
            return "Google Ads"
        if "facebook" in src or "meta" in src:
            return "Meta Ads"
        if "twitter" in src or "x.com" in src:
            return "X (Twitter)"
        return utm_source.title()

    if ai_referrer:
        return ai_referrer.title().replace("Chatgpt", "ChatGPT")

    if referrer:
        ref = referrer.lower()
        if any(d in ref for d in _ORGANIC_DOMAINS):
            return "Organic"

    return "Direct"
