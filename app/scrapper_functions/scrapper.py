# Import the required libraries
import pandas as pd
from app.scrapper_functions.data.data import african_countries, macro_indicator_dict, country_codes, country_region_codes
from app.scrapper_functions.functions.functions import get_wiki_link, get_stats, find_country_of_origin, get_macro_data, fetch_google_news


def information_scrapper(company: str):
    """
    Gathers comprehensive information about a given company, including its Wikipedia data, country of origin, 
    macroeconomic indicators, and recent news articles.

    The function performs the following steps:
    1. Scrapes the company's Wikipedia page to extract the company name, description, and other details.
    2. Identifies the country where the company is based and checks if it's located in Africa.
    3. Fetches relevant macroeconomic data for the country's economy from the World Bank API.
    4. Retrieves recent news articles related to the company from Google News RSS.
    5. Returns a dictionary containing:
       - Company name
       - Description
       - Country of origin
       - Macroeconomic details for the country
       - News articles related to the company

    Args:
        company (str): The name of the company to analyze.

    Returns:
        dict: A dictionary containing the following keys:
            - 'company': The company's name as found on Wikipedia.
            - 'company_info': The company's information as found on Wikioedia
            - 'description': A brief description of the company from Wikipedia.
            - 'country': The identified country where the company was founded.
            - 'macro_details': Macroeconomic data categorized by the World Bank.
            - 'articles': A list of recent news articles related to the company with sentiment scores.

    Raises:
        Exception: 
            - If the company does not appear to be based in Africa.
            - If any scraping or fetching operation fails.
    """
    
    information = {}
    
    company_name, company_info, desc = get_wiki_link(company)
    
    country = find_country_of_origin(company, african_countries, company_info)
    
    if not country:
        raise Exception("Could not found country of origin for this company among list of African countries.")

    macro_data_dict = get_macro_data(10, country, country_codes, macro_indicator_dict, country_region_codes)
    
    macro_ds = pd.DataFrame(macro_data_dict).sort_values(by='date')
    
    macro_ds = macro_ds.fillna(0)

    macro_details = get_stats(macro_ds, country, country_region_codes, macro_indicator_dict)
    
    articles = fetch_google_news(company_name, limit=20)

    information['company'] = company_name
    information['company_information'] = company_info
    information['description'] = desc
    information['country'] = country
    information['macro_details'] = macro_details
    information['articles'] = articles
    
    return information
