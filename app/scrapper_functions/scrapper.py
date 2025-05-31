# Import the required libraries
from app.scrapper_functions.data.data import african_countries, african_demonyms
from app.scrapper_functions.functions.functions import get_wiki_link, find_country_of_origin, fetch_google_news, get_company_stats
import time


def information_scrapper(company: str) -> dict:
    """
    Scrapes and gathers detailed information about a company from multiple sources.

    Collects:
    - Company name and description from Wikipedia
    - Country of origin (restricted to African countries)
    - Competitors, funding, and company stats
    - (Optional) Recent news articles

    Args:
        company (str): The name of the company to gather information about.

    Returns:
        dict: A dictionary with keys:
            - "company": str
            - "company_info_fixed": dict
            - "company_info": dict
            - "description": str
            - "country": str (African only)
            - "competitors": dict
            - "funding": dict

    Raises:
        Exception: If the company is not identified as African or if critical steps fail.
    """
    start = time.time()
    information = {}

    # Get Wikipedia-based info
    company_name, company_info, desc = get_wiki_link(company)

    # Determine African country of origin
    country = find_country_of_origin(
        company,
        african_countries,
        company_info if company_info else {},
        african_demonyms
    )

    if not country:
        raise Exception(
            f"Could not find country of origin for '{company}' among African countries.")

    # Company stats (fallback to raw name if Wikipedia doesn't return one)
    name_for_stats = company_name if company_name else company
    competitors, funding, company_information_dict = get_company_stats(
        name_for_stats)

    # Compose response dictionary
    information["company"] = name_for_stats
    information["company_info_fixed"] = company_information_dict
    information["company_info"] = company_info if company_info else {}
    information["description"] = desc if desc else ''
    information["country"] = country
    information["competitors"] = competitors
    information["funding"] = funding
    # information["articles"] = fetch_google_news(name_for_stats, limit=10)

    print(f"Time taken: {time.time() - start:.2f} seconds")

    return information
