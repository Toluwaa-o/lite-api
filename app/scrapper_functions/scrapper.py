# Import the required libraries
from app.scrapper_functions.data.data import african_countries, african_demonyms
from app.scrapper_functions.functions.functions import get_wiki_link, find_country_of_origin, get_company_stats
import time
import undetected_chromedriver as uc
import os


def create_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )

    if os.getenv("ENV") == "PRODUCTION":
        chrome_path = os.getenv("GOOGLE_CHROME_BIN")
        if not chrome_path:
            raise ValueError("GOOGLE_CHROME_BIN is not set")
        options.binary_location = chrome_path

    driver = uc.Chrome(options=options)
    
    return driver


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
    driver = create_driver()
    information = {}

    try:
        try:
            company_name, company_info, desc = get_wiki_link(company, driver)
        except Exception as e:
            raise Exception(f"[Wikipedia Error] {e}")

        try:
            country = find_country_of_origin(
                company,
                african_countries,
                company_info if company_info else {},
                african_demonyms,
                driver
            )
        except Exception as e:
            raise Exception(f"[Country Detection Error] {e}")

        if not country:
            raise Exception(
                f"[Country Match Error] Could not find country of origin for '{company}' among African countries."
            )

        try:
            name_for_stats = company_name if company_name else company
            competitors, funding, company_information_dict = get_company_stats(
                name_for_stats, driver)
        except Exception as e:
            raise Exception(f"[Growjo Error] {e}")

        information = {
            "company": name_for_stats,
            "company_info_fixed": company_information_dict,
            "company_info": company_info if company_info else {},
            "description": desc if desc else "",
            "country": country,
            "competitors": competitors,
            "funding": funding,
            #"scrape_time_seconds": round(time.time() - start, 2)
        }

        return information

    except Exception as e:
        print(str(e))
        return {
            "company": company,
            "error": str(e),
            "company_info_fixed": {},
            "company_info": {},
            "description": "",
            "country": "",
            "competitors": {},
            "funding": {},
            #"scrape_time_seconds": round(time.time() - start, 2)
        }

    finally:
        driver.quit()
