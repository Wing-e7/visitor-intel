"""
visitor-intel quickstart

Identify your ICP visitors in under 5 lines.

Run:
    pip install visitor-intel
    python examples/quickstart.py
"""
import asyncio
from visitor_intel import (
    fetch_company_intel,
    classify_ai_source,
    compute_icp_score,
    score_to_fit_tier,
    derive_channel,
    enrich_company_url,
    company_signals_to_score,
    score_linkedin,
    load_client_profiles,
    compute_client_similarity,
)


async def score_a_visitor():
    # --- Step 0: Load your client profiles ONCE at startup ---
    # These are URLs of companies you've already won as clients.
    # The model learns what your ICP looks like from them.
    YOUR_CLIENTS = [
        "https://stripe.com",
        "https://notion.so",
        "https://figma.com",
    ]
    client_profiles = await load_client_profiles(YOUR_CLIENTS)
    print(f"Loaded {len(client_profiles)} client profiles\n")

    # --- Signals you collect from your landing page ---
    ip = "8.8.8.8"                     # visitor IP
    referrer = "https://chatgpt.com/"  # HTTP Referer header
    utm_source = None                   # UTM params from URL
    page_type = "pricing"              # which page they landed on
    time_on_page_sec = 75              # tracked by frontend
    scroll_depth_pct = 80              # tracked by frontend
    cta_clicked = True                 # did they click "Book a demo"?
    pages_visited = 3                  # this session
    is_returning = False               # first visit?

    # --- Enrichment signals (from a form or chat) ---
    visitor_company_url = "https://stripe.com"           # visitor shared their company URL
    visitor_linkedin_url = "https://linkedin.com/in/johnsmith"  # visitor shared their LinkedIn
    visitor_job_title = "VP of Sales"                    # from the same form

    # --- Step 1: Identify company from IP ---
    company = await fetch_company_intel(ip)
    print(f"IP company: {company['company_name'] or 'unknown'} ({company['country']})")

    # --- Step 2: Detect AI referral ---
    ai_referrer = classify_ai_source(referrer)
    print(f"AI source: {ai_referrer or 'none'}")

    # --- Step 3 (optional): Enrich from company URL ---
    company_signals = await enrich_company_url(visitor_company_url)
    url_score = company_signals_to_score(company_signals)
    print(f"Company URL signals: pricing={company_signals.get('has_pricing_page')}, "
          f"careers={company_signals.get('has_careers_page')}, "
          f"saas_tools={company_signals.get('saas_tools_detected', [])}")

    # --- Step 4 (optional): Score LinkedIn ---
    li_score = score_linkedin(visitor_linkedin_url, job_title=visitor_job_title)
    print(f"LinkedIn score: {li_score}")

    # --- Step 5 (optional): Compare visitor's company to your client profiles ---
    similarity_score = compute_client_similarity(company_signals, client_profiles)
    print(f"Client similarity score: {similarity_score}/30")

    # --- Step 6: Final ICP score ---
    score = compute_icp_score(
        company_identified=company["company_identified"],
        utm_source=utm_source,
        ai_referrer=ai_referrer,
        page_type=page_type,
        time_on_page_sec=time_on_page_sec,
        scroll_depth_pct=scroll_depth_pct,
        cta_clicked=cta_clicked,
        pages_visited=pages_visited,
        is_returning=is_returning,
        company_url_score=url_score,
        linkedin_score=li_score,
        client_similarity_score=similarity_score,
    )
    tier = score_to_fit_tier(score)
    channel = derive_channel(utm_source, ai_referrer, referrer)

    print(f"\nScore: {score}/100 → {tier}")
    print(f"Channel: {channel}")
    print()
    if tier == "icp_fit":
        print("Action: Hot visitor. Route to sales immediately.")
    elif tier == "potential":
        print("Action: Warm visitor. Trigger nurture sequence.")
    else:
        print("Action: Low fit. Deprioritise.")


if __name__ == "__main__":
    asyncio.run(score_a_visitor())
