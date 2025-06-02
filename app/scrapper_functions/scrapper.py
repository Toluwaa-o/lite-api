# Import the required libraries
from app.scrapper_functions.data.data import african_countries, african_demonyms
from app.scrapper_functions.functions.functions import get_wiki_link, find_country_of_origin, get_company_stats
import time
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver import Chrome
from queue import Queue
import time
import undetected_chromedriver as uc
import os


class BrowserPool:
    def __init__(self, size=3):
        self.pool = Queue(maxsize=size)
        for _ in range(size):
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

            self.pool.put(uc.Chrome(options=options))

    def get_browser(self):
        return self.pool.get()

    def release_browser(self, browser):
        browser.get("about:blank")  # Reset state
        self.pool.put(browser)
    
    def cleanup(self):
        while not self.pool.empty():
            try:
                browser = self.pool.get_nowait()
                browser.quit()
            except Exception as e:
                print(f"Error cleaning up browser: {e}")


def information_scrapper(company: str, browser_pool: BrowserPool = None) -> dict:
    """
    Scrapes company information from multiple sources in parallel.

    Args:
        company: Name of the company to research
        browser_pool: Optional browser pool for Selenium reuse

    Returns:
        Dictionary containing all scraped company information

    Raises:
        Exception: If critical information (like country) cannot be found
    """
    start_time = time.time()
    information = {"company": company}

    local_pool = False
    if browser_pool is None:
        browser_pool = BrowserPool()
        local_pool = True

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all tasks at once
            futures = {
                "wiki": executor.submit(get_wiki_link, company, browser_pool),
                "stats": executor.submit(get_company_stats, company, browser_pool),
                "country": executor.submit(
                    find_country_of_origin,
                    company,
                    african_countries,
                    {},
                    african_demonyms,
                    browser_pool
                )
            }

            # Process results as they complete
            for key, future in futures.items():
                try:
                    result = future.result()

                    if key == "wiki":
                        company_name, company_info, desc = result
                        information.update({
                            "company": company_name,
                            "company_info": company_info,
                            "description": desc
                        })
                    elif key == "stats":
                        competitors, funding, company_info_dict = result
                        information.update({
                            "competitors": competitors or {},
                            "funding": funding or {},
                            "company_info_fixed": company_info_dict or {}
                        })
                    elif key == "country":
                        if not result:
                            raise ValueError("Country not found")
                        information["country"] = result

                except Exception as e:
                    error_msg = f"{key} scraping failed: {str(e)}"
                    print(error_msg)

                    if key == "country":
                        raise Exception(error_msg)

        #information["processing_time_sec"] = round(time.time() - start_time, 2)
        
        if not information.get("country"):
            raise ValueError("Could not determine country of origin")

        return information

    finally:
        if local_pool:
            browser_pool.cleanup()
