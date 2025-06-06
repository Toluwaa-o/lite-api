from country_named_entity_recognition import find_countries
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app.scrapper_functions.data.data import african_countries
import requests
import time
import undetected_chromedriver as uc
from datetime import datetime
from bs4 import BeautifulSoup
import re
import feedparser
from urllib.parse import urlparse, parse_qs, unquote
from collections import Counter
import os


def url(company: str, search_type: str) -> tuple[str, str]:
    """Generates a DuckDuckGo search URL based on the company name and search type.

    Args:
        company (str): The name of the company to search for.
        search_type (str): The type of search to perform.
            Accepts "wiki" for Wikipedia, "stats" for Growjo stats, 'crunch' for crunchbase stats, or any other value for general country of origin.

    Returns:
        str: A full DuckDuckGo HTML search URL for the given company and search type.
    """
    base_link = "https://html.duckduckgo.com/html/?q="
    if search_type == 'wiki':
        keyword = f"{company} company wikipedia"
    elif search_type == 'stats':
        keyword = f"{company} growjo.com company"
    elif search_type == 'crunch':
        keyword = f"{company} crunchbase.com company"
    else:
        keyword = f"{company} company founded in what country?"
    return base_link, keyword


def clean_ddg_urls(url: str) -> str:
    """Extracts and returns the clean URL from a DuckDuckGo redirect link.

    DuckDuckGo search result URLs often contain a `uddg` parameter
    which holds the actual destination URL. This function parses and
    decodes that value.

    Args:
        url (str): The DuckDuckGo redirect URL.

    Returns:
        str: The clean destination URL if found, otherwise an empty string.
    """
    if url:
        if "uddg=" in url:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            clean_url = unquote(query_params.get("uddg", [""])[0])
            return clean_url
        else:
            return url


def extract_link(res, link_type: str) -> str:
    """Extracts a specific type of link from DuckDuckGo search results.

    Searches for anchor tags in the result and attempts to extract the first
    link that contains the specified `link_type`. It cleans the link using
    `clean_ddg_urls` and further processes it to remove any redirection formatting.

    Args:
        res: A BeautifulSoup object representing the parsed HTML of a DuckDuckGo search result.
        link_type (str): A string indicating the expected type of link to extract
            (e.g., "wikipedia", "growjo").

    Returns:
        str: A cleaned direct URL containing the specified `link_type`.

    Raises:
        Exception: If no matching link containing the `link_type` is found.
    """
    links = res.find_all("a", class_="result__url")
    for link in links[:2]:
        raw_href = link.get("href")
        if not raw_href:
            continue

        cleaned_href = clean_ddg_urls(raw_href)

        if cleaned_href and link_type in cleaned_href:
            return cleaned_href.split("/url?q=")[-1].split("&")[0]

    raise Exception(f"Cannot find a {link_type} link for the company.")


def extract_most_mentioned_country(full_text: str, african_countries: list) -> str:
    """Identifies the most frequently mentioned African country in a given text.

    Converts the input text to lowercase and searches for exact matches of each country
    name from the provided list. It counts occurrences using regex word boundaries to
    avoid partial matches.

    Args:
        full_text (str): The text in which to search for country mentions.
        african_countries (list): A list of African country names to search for.

    Returns:
        str: The name of the most frequently mentioned country, or an empty string if none are found.
    """
    full_text = full_text.lower()
    country_counts = Counter()

    patterns = {
        country: re.compile(rf"\b{re.escape(country.lower())}\b")
        for country in african_countries
    }

    for country, pattern in patterns.items():
        matches = pattern.findall(full_text)
        if matches:
            country_counts[country] += len(matches)

    if country_counts:
        return country_counts.most_common(1)[0][0]

    return ""


def find_country_of_origin(company: str, african_countries: list, company_info: dict, african_demonyms: dict, driver) -> str:
    """
    Attempts to determine the African country of origin for a given company.
    Only returns a result if it is in the list of African countries.
    """
    country_markers = ["headquarters", "country"]

    # 1. Check known company_info fields
    for marker in country_markers:
        if marker in company_info:
            result = find_countries(company_info[marker])
            if result:
                country_name = result[0][0].name
                if country_name in african_countries:
                    return country_name
            continue

    # 2. Perform DuckDuckGo search
    try:
        base, query = url(company, 'country')
        driver.get(base)

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q")))
        search_input = driver.find_element(By.NAME, "q")
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.RETURN)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        elements = soup.find_all("div", class_="result")
        full_text = " ".join(set(el.text.strip() for el in elements)).lower()

        country = extract_most_mentioned_country(full_text, african_countries)
        if country in african_countries:
            return country

        reversed_map = {v.lower(): k for k, v in african_demonyms.items()}
        for demonym in reversed_map:
            if demonym in full_text:
                return reversed_map[demonym]

        for country in african_countries:
            pattern = r"\b(?:in|from|based in|located in|headquartered in|a[n]?|an)?\s*" + re.escape(
                country.lower()) + r"\b"
            if re.search(pattern, full_text):
                return country

    except Exception as e:
        print(f"Error finding country of origin: {e}")

    return ""


def extract_company_details(li_list: list) -> dict:
    """Extracts specific company-related metrics from a list of text strings.

    The function scans through the list to find entries that contain known
    section headers (e.g., "annual revenue", "employees") and extracts numeric
    or relevant textual information using a regex pattern.

    Args:
        li_list (list): A list of strings, typically `<li>` elements from HTML, containing company info.

    Returns:
        dict: A dictionary mapping each relevant section (e.g., "annual revenue") to its extracted value.
    """
    company_info = {}
    sections = [
        "annual revenue", "venture funding", "revenue per employee",
        "total funding", "current valuation", "employees", "employee count"
    ]
    seen = set()
    for li in li_list:
        li_lower = li.lower()
        for section in sections:
            if section in li_lower and section not in seen:
                match = re.search(
                    r"[\$€£]?\s?\d{1,3}(?:[,\d{3}]*)(?:\.\d+)?\s?[kmbKMB]?", li)
                if match:
                    company_info[section] = match.group().strip()
                else:
                    company_info[section] = li.strip()
                seen.add(section)
                break

    return company_info


def extract_table_data(table) -> dict:
    """Parses an HTML table and extracts its content into a structured dictionary.

    The function reads the header from the `<thead>` and rows from the `<tbody>`,
    mapping each header to a list of column values. It also removes any hashtags
    followed by digits (e.g., "#123") from the cell values.

    Args:
        table: A BeautifulSoup Tag object representing an HTML table.

    Returns:
        dict: A dictionary where each key is a column header and the corresponding
              value is a list of cleaned data entries from that column.
    """
    table_data = {}

    head = table.find("thead")
    if head:
        header_cells = head.find_all("th")
    else:
        first_row = table.find("tr")
        header_cells = first_row.find_all("th") or first_row.find_all("td")

    headers = [cell.text.strip() for cell in header_cells]
    for header in headers:
        table_data[header] = []

    # Extract rows
    body = table.find("tbody") or table
    rows = body.find_all("tr") if head else body.find_all("tr")[1:]

    for row in rows:
        cells = row.find_all("td")
        for i in range(min(len(cells), len(headers))):
            text = cells[i].text.strip()
            cleaned = re.sub(r"#\d+", "", text).strip()
            table_data[headers[i]].append(cleaned)

    return table_data


def extract_investor_no(company_name: str, driver) -> int:
    """Extracts the number of investors for a given company using a DuckDuckGo search.

    The function searches for a phrase like "total X investors" in the DuckDuckGo search
    results page for the query "[company_name] has how many investors?" It counts how often
    each number appears in that pattern and returns the most common one.

    Args:
        company_name (str): The name of the company to search for.

    Returns:
        int: The most commonly mentioned number of investors found in the search results.
             Returns 0 if no relevant information is found.
    """

    search = f"how many investors does {company_name} have?"
    target_url = 'https://html.duckduckgo.com/html/'

    full_text = ""

    try:
        driver.get(target_url)

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q")))
        search_input = driver.find_element(By.NAME, "q")
        search_input.clear()
        search_input.send_keys(search)
        search_input.send_keys(Keys.RETURN)

        page = driver.page_source
        soup = BeautifulSoup(page, 'html.parser')
        elements = soup.find_all('div', class_='result')

        full_text = " ".join({el.text.strip().lower()
                             for el in elements})

    except Exception as e:
        print(f"[Search error] {e}")
        return 0

    # Pattern matching different possible investor-related phrases
    pattern = re.compile(
        r"has\s+(\d+)\s+investors|"
        r"from\s+(\d+)\s+investors|"
        r"total\s+of\s+(\d+)\s+investors|"
        r"raised\s+.*?\s+from\s+(\d+)\s+investors|"
        r"backed\s+by\s+(\d+)\s+investors|"
        r"(\d+)\s+investors\s+participated|"
        r"(\d+)\s+institutional\s+investors|"
        r"(\d+)\s+investors",
        re.IGNORECASE
    )

    try:
        matches = pattern.findall(full_text)

        numbers = [int(num)
                   for match in matches for num in match if num.isdigit()]

        if numbers:
            return Counter(numbers).most_common(1)[0][0]

    except Exception as e:
        print(f"[Regex error] {e}")

    return 0


def get_company_stats(company_name: str, driver) -> tuple:
    """Fetches company statistics such as competitors, funding information, and basic company details.

    This function performs a DuckDuckGo search for the company"s Growjo page and scrapes it to extract:
    - Competitors (from a specific table)
    - Funding data (from another table)
    - Company details such as revenue, valuation, employee count, and industry
    - Number of investors (from search-based parsing)

    Args:
        company_name (str): The name of the company to retrieve statistics for.

    Returns:
        tuple: A tuple containing:
            - dict: A dictionary of competitor data extracted from Growjo.
            - dict: A dictionary of funding data extracted from Growjo.
            - dict: A dictionary of company details including:
                * "annual revenue"
                * "venture funding"
                * "revenue per employee"
                * "total funding"
                * "current valuation"
                * "employees"
                * "employee count"
                * "investors"
                * "industry"

    Raises:
        Exception: If the Growjo link or required data elements cannot be found.
    """
    try:
        target_url, query = url(company_name, 'stats')

        driver.get(target_url)
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q")))

        search_input = driver.find_element(By.NAME, "q")
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.RETURN)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        search_results = soup.find("div", class_="results")

        main_link = extract_link(search_results, "growjo.com")
        if not main_link:
            raise Exception("Growjo link not found in search results")

        if company_name.strip().lower() == 'andela':
            driver.get('https://growjo.com/company/Andela')
        else:
            driver.get(main_link)
            
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main")))
        grow_soup = BeautifulSoup(driver.page_source, "html.parser")
    except Exception as e:
        print(f"[Navigation Error] {e}")
        return {}, {}, {}

    # --- Initialize Outputs ---
    competitors, funding, company_info = {}, {}, {}
    industry = ""

    # --- Industry ---
    try:
        info_div = grow_soup.find("div", id="revenue-financials")
        print(f"info_div: {info_div}")
        
        if info_div:
            for a in info_div.find_all("a"):
                if "/industry/" in a.get("href", ""):
                    industry = a.text.strip()
                    break
    except Exception as e:
        print(f"[Industry Parsing Error] {e}")

    tables = grow_soup.find_all("table", class_="cstm-table")

    # --- Competitors ---
    try:
        for table in tables:
            header_cells = table.find("thead").find_all("th")
            headers = [th.text.strip().lower() for th in header_cells]

            if "competitor name" in headers:
                competitors = extract_table_data(table)
                break
    except Exception as e:
        print(f"[Competitors Table Error] {e}")

    # --- Funding ---
    try:
        for table in tables:
            header_cells = table.find("thead").find_all("th")
            headers = [th.text.strip().lower() for th in header_cells]

            if "lead investors" in headers:
                funding = extract_table_data(table)
                break
    except Exception as e:
        print(f"[Funding Table Error] {e}")

    # --- Company Details ---
    try:
        info_div = grow_soup.find("div", class_="col-md-5")
        lis = [li.text.strip() for li in info_div.find_all("li")]
    except Exception as e:
        print(f"[Company Info Extraction Error] {e}")
        lis = []

    company_info = extract_company_details(lis)

    try:
        company_info["investors"] = extract_investor_no(company_name, driver)
    except Exception as e:
        print(f"[Investor Extraction Error] {e}")
        company_info["investors"] = 0

    company_info["industry"] = industry

    return competitors, funding, company_info


# def get_crunchbase_info(company: str, african_countries: list, driver) -> tuple:
#     """
#     Fetches Crunchbase link and scrapes key company information.

#     This function performs a DuckDuckGo search for the company's Crunchbase profile,
#     navigates to the organization's page, and extracts the following:
#     - Number of employees
#     - Address/location of the company
#     - Country (inferred from address)

#     The function ensures the company is based in Africa by validating the country field.

#     Args:
#         company (str): The name of the company to retrieve information for.
#         african_countries (list): A list of all African country names.
#         driver (WebDriver): A Selenium WebDriver instance for browsing.

#     Returns:
#         tuple: A tuple containing:
#             - str or None: The company's address.
#             - str or None: The inferred country from the address.
#             - str or None: The employee count description (e.g., "4113 Employees").

#     Raises:
#         Exception: If Crunchbase page is not found, or the company is not African-based.
#     """
#     address = country = employees = None  # Default return values

#     try:
#         target_url, query = url(company, 'crunch')

#         driver.get(target_url)
#         WebDriverWait(driver, 5).until(
#             EC.presence_of_element_located((By.NAME, "q")))

#         search_input = driver.find_element(By.NAME, "q")
#         search_input.clear()
#         search_input.send_keys(query)
#         search_input.send_keys(Keys.RETURN)

#         soup = BeautifulSoup(driver.page_source, 'html.parser')
#         search_results = soup.find("div", class_="results")

#         main_link = extract_link(search_results, "crunchbase.com/organization")
#         if not main_link:
#             raise Exception("Crunchbase link not found in search results")

#         driver.get(main_link)
#         WebDriverWait(driver, 10).until(
#             EC.presence_of_element_located((By.TAG_NAME, "body")))

#         print("page source", driver.page_source)
#         crunch_soup = BeautifulSoup(driver.page_source, "html.parser")
#         print(crunch_soup)
#         # Get employee info
#         emp_el = crunch_soup.find(
#             "label-with-icon", {"iconkey": "icon_people_three"})
#         if emp_el:
#             employees = emp_el.get_text(strip=True)

#         # Get location info
#         addr_el = crunch_soup.find(
#             "label-with-icon", {"iconkey": "icon_location"})
#         if addr_el:
#             address = addr_el.get_text(strip=True)
#             matches = find_countries(address)
#             country = matches[0].name if matches else None

#             if country and country.lower() not in african_countries:
#                 raise Exception("Company is not an African company")

#     except Exception as e:
#         print("Error:", e)

#     return address, country, employees


def get_wiki_link(company: str, driver) -> tuple:
    """Fetches the Wikipedia link and relevant company information.

    This function performs a DuckDuckGo search for the company"s Wikipedia page and scrapes the following:
    - Company name
    - Key financial and business information (e.g., revenue, valuation)
    - A brief company description (summary paragraph from Wikipedia)

    Args:
        company (str): The name of the company to retrieve information for.

    Returns:
        tuple: A tuple containing:
            - str: The name of the company.
            - dict: A dictionary containing key company information (e.g., revenue, valuation).
            - str: A brief description of the company.

    Raises:
        Exception: If the company is not found or if there are issues with scraping Wikipedia.
    """

    try:
        base, query = url(company, 'wiki')
        driver.get(base)
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q")))

        search_input = driver.find_element(By.NAME, "q")
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.RETURN)

        page = driver.page_source
        soup = BeautifulSoup(page, 'html.parser')
        result = soup.find("div", class_="results")

        # Extract the Wikipedia URL and fetch the page content
        uri = extract_link(result, "en.wikipedia.org")
        response = requests.get(uri)
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract the company name from the Wikipedia page
        try:
            company_name = soup.find(
                "span", class_="mw-page-title-main").text.strip()
        except:
            company_name = company

        # Extract information from the company infobox (if available)
        infobox = soup.find("table", class_="infobox")
        info_label, info_data = [], []

        if infobox:
            rows = infobox.find_all("tr")
            for row in rows:
                try:
                    label = row.find("th")
                    data = row.find("td")
                    if label and data:
                        info_label.append(label.text.strip())
                        info_data.append(data.text.strip())
                except:
                    continue

        # Extract a brief company description
        large_text = soup.find("div", class_="mw-body-content")
        desc = ""
        if large_text:
            p_tag = large_text.find("p")
            if p_tag:
                desc = p_tag.text.strip()

        # Clean up the description by removing reference links
        new_dsc = re.sub(r"\[\d*\]", "", desc)

        # Verify that the company name appears to be a valid company
        company_keywords = ["company", "startup", "corporation", "firm",
                            "organization", "business", "enterprise", "subsidiary"]

        text = large_text.get_text(" ", strip=True).casefold()
        if not any(keyword in text for keyword in company_keywords):
            raise Exception("Name entered is most likely not a company.")

        # Process the extracted financial and business data
        company_info = {}
        units = ["hundred", "thousand", "million", "billion", "trillion"]

        for i in range(len(info_label)):
            money_field = any(unit in info_data[i].lower() for unit in units)

            # Extract and clean money-related fields
            if money_field:
                pattern = r"US\$\d+.?\d+ \w+"
                res = re.search(pattern, info_data[i])
                if res:
                    company_info[info_label[i].lower()] = res.group()
                else:
                    company_info[info_label[i].lower()] = re.sub(
                        r"\[\d*\]", "", info_data[i])
            else:
                company_info[info_label[i].lower()] = re.sub(r"\[\d*\]", "", info_data[i].replace(
                    "\n", ", ").replace(",,", ","))

        website_row = infobox.find("a", href=True)
        if website_row and "http" in website_row["href"]:
            company_info["website"] = website_row["href"]

        return company_name, company_info, new_dsc
    except Exception as e:
        print(f"Something went wrong while scrapping from wikipedia: {e}")
        raise Exception(
            f"Something went wrong while scrapping from wikipedia: {e}")
