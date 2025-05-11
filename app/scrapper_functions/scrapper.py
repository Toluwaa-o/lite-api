# Import the required libraries
from app.scrapper_functions.data.data import african_countries, african_demonyms
from app.scrapper_functions.functions.functions import get_wiki_link, find_country_of_origin, fetch_google_news, get_company_stats
import time

def information_scrapper(company: str) -> dict:
    """Scrapes and gathers detailed information about a company from multiple sources.

    This function collects various types of information about a company, including:
    - Company name and description from Wikipedia
    - Country of origin (if the company is based in an African country)
    - Competitors, funding details, and other company stats
    - Recent news articles from Google News

    It processes and returns this data as a dictionary.

    Args:
        company (str): The name of the company to gather information about.

    Returns:
        dict: A dictionary containing the following information:
            - "company": The name of the company.
            - "company_info_fixed": A dictionary of fixed company information (e.g., funding, competitors).
            - "company_info": A dictionary of general company information scraped from Wikipedia.
            - "description": A short description of the company.
            - "country": The country of origin (if available) for the company.
            - "articles": A list of recent news articles about the company.
            - "competitors": A dictionary of the company"s competitors.
            - "funding": A dictionary of the company"s funding information.

    Raises:
        Exception: If the company cannot be found in the list of African countries, or if any scraping process fails.
        
    """
    start = time.time()
    information = {}

    # Fetch company name, general information, and description from Wikipedia
    company_name, company_info, desc = get_wiki_link(company)

    # Find the country of origin from a list of African countries
    country = find_country_of_origin(company, african_countries, company_info, african_demonyms)
    
    # Raise an exception if no country is found in the list of African countries
    if not country:
        raise Exception("Could not find country of origin for this company among list of African countries.")

    # Get company stats like competitors, funding, etc.
    competitors, funding, company_information_dict = get_company_stats(company_name)

    # Fetch recent news articles related to the company
    articles = fetch_google_news(company_name, limit=10)

    # Store all gathered information in a dictionary
    information["company"] = company_name
    information["company_info_fixed"] = company_information_dict
    information["company_info"] = company_info
    information["description"] = desc
    information["country"] = country
    information["articles"] = articles
    information["competitors"] = competitors
    information["funding"] = funding
    
    # Print the time taken for scraping
    print(f"Time taken: {time.time() - start}")
    
    return information