from country_named_entity_recognition import find_countries
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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


def url(company: str, search_type: str) -> str:
    """Generates a DuckDuckGo search URL based on the company name and search type.

    Args:
        company (str): The name of the company to search for.
        search_type (str): The type of search to perform. 
            Accepts "wiki" for Wikipedia, "stats" for Growjo stats, or any other value for general country of origin.

    Returns:
        str: A full DuckDuckGo HTML search URL for the given company and search type.
    """
    base_link = "https://html.duckduckgo.com/html/?q="
    if search_type == 'wiki':
        keyword = f"{company} company wikipedia"
        return base_link, keyword
    elif search_type == 'stats':
        keyword = f"{company} growjo.com company"
        return base_link, keyword
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
    #print(f"Unclean Links: {[l.get('href') for l in links]}")
    #print(f"Clean Links: {[clean_ddg_urls(l.get('href')) for l in links]}")
    href = clean_ddg_urls(links[0].get("href"))
    if href and link_type in href:
        href = href.split("/url?q=")[-1].split("&")[0]
        return href
    else:
        href = clean_ddg_urls(links[1].get("href"))
        if href and link_type in href:
            href = href.split("/url?q=")[-1].split("&")[0]
            return href
        else:
            raise Exception(f"Cannot find a {link_type} link for the company")


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

    for country in african_countries:
        pattern = rf"\b{re.escape(country.lower())}\b"
        matches = re.findall(pattern, full_text)
        if matches:
            country_counts[country] += len(matches)

    if country_counts:
        # Return the country with the highest occurrence
        most_common = country_counts.most_common(1)[0][0]
        return most_common

    return ""


def find_country_of_origin(company: str, african_countries: list, company_info: dict, african_demonyms: dict) -> str:
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

    try:
        base, query = url(company, 'country')
        driver.get(base)
        time.sleep(2)

        search_input = driver.find_element(By.NAME, "q")
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.RETURN)

        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        elements = soup.find_all("div", class_="result")
        full_text = " ".join(set(el.text.strip() for el in elements)).lower()

        country = extract_most_mentioned_country(full_text, african_countries)
        if country in african_countries:
            return country

        for demonym in african_demonyms.values():
            if re.search(rf"\b{re.escape(demonym.lower())}\b", full_text):
                reversed_map = {v.lower(): k for k, v in african_demonyms.items()}
                matched_country = reversed_map.get(demonym.lower())
                if matched_country in african_countries:
                    return matched_country

        for country in african_countries:
            pattern = r"\b(?:in|from|based in|located in|headquartered in|a[n]?|an)?\s*" + re.escape(country.lower()) + r"\b"
            if re.search(pattern, full_text):
                return country

    except Exception as e:
        print(f"Error finding country of origin: {e}")
        try:
            driver.quit()
        except:
            pass

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
    company_information_dict = {}
    sections = [
        "annual revenue", "venture funding", "revenue per employee",
        "total funding", "current valuation", "employees", "employee count"
    ]
    for section in sections:
        for li in li_list:
            if section in li:
                pattern = r"\W\d+\W?\d?+\w?\W?"
                match = re.search(pattern, li)
                if match:
                    company_information_dict[section] = match.group().strip()
                else:
                    company_information_dict[section] = li

    return company_information_dict


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
    ths = head.find_all("th")

    header = [th.text.strip() for th in ths]

    for i in range(len(header)):
        table_data[header[i]] = []

    body = table.find("tbody")
    rows = body.find_all("tr")

    for row in rows:
        tds = row.find_all("td")
        data = [td.text.strip() for td in tds]

        for i in range(len(header)):
            pattern = r"#\d+"
            clean_data = re.sub(pattern, "", data[i])
            table_data[header[i]].append(clean_data)

    return table_data


def extract_investor_no(company_name: str) -> int:
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

    search = f"how many investors does {company_name} have?"
    target_url = 'https://html.duckduckgo.com/html/'

    try:
        driver.get(target_url)
        time.sleep(2)  # Let the page load

        search_input = driver.find_element(By.NAME, "q")
        search_input.clear()
        search_input.send_keys(search)
        search_input.send_keys(Keys.RETURN)

        time.sleep(3)  # Allow results to load

        page = driver.page_source
        soup = BeautifulSoup(page, 'html.parser')
        elements = soup.find_all('div', class_='result')

        full_text = " ".join(set([el.text.strip() for el in elements])).lower()
        full_text = full_text.lower()
    except Exception as e:
        print(e)
    finally:
        driver.quit()

    pattern = r"has\s+(\d+)\s+investors|from\s+(\d+)\s+investors|total\s+of\s+(\d+)\s+investors|raised\s+.*?\s+from\s+(\d+)\s+investors|backed\s+by\s+(\d+)\s+investors|(\d+)\s+investors\s+participated|(\d+)\s+institutional\s+investors|(\d+)\s+investors"

    #print(f"All funding page text: {full_text}")
    try:
        matches = re.findall(pattern, full_text)

        # Flatten the matches: each match is a tuple; extract non-empty group
        numbers = [int(num) for match in matches for num in match if num]

        if numbers:
            number_counts = Counter(numbers)
            #print("Investor number counts:", number_counts)
            return number_counts.most_common(1)[0][0]
    except Exception as e:
        print(e)

    return 0


def get_company_stats(company_name: str) -> tuple:
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

    try:
        target_url, query = url(company_name, 'stats')

        driver.get(target_url)
        time.sleep(2)

        search_input = driver.find_element(By.NAME, "q")
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.RETURN)

        time.sleep(3)

        result = driver.page_source
        soup = BeautifulSoup(result, 'html.parser')

        #print(soup)

        search_results = soup.find("div", class_="results")
        #print(f"Search Results {search_results}")

        main_link = extract_link(search_results, "growjo.com")
        #print(f"main URL {main_link}")

        driver.get(main_link)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception as e:
            print("Timeout waiting for page to load:", e)

        result = driver.page_source
        
        grow_soup = BeautifulSoup(result, "html.parser")
        #print(grow_soup)
    except Exception as e:
        print(e)

    competitors = {}
    funding = {}
    industry = ""

    try:
        horizontal_info = grow_soup.find("div", id="revenue-financials")
        horizontal_info_a = horizontal_info.find_all("a")
        for a in horizontal_info_a:
            href = a.get("href")
            if "/industry/" in href:
                industry = a.text.strip()
    except:
        print("Could not find industry")

    try:
        competitors_table = grow_soup.find_all("table", class_="cstm-table")[1]
        competitors = extract_table_data(competitors_table)
    except:
        print("no competitors table")

    try:
        funding_table = grow_soup.find_all("table", class_="cstm-table")[3]
        funding = extract_table_data(funding_table)
    except:
        print("no funding table")

    try:
        div = grow_soup.find("div", class_="col-md-5")
        lis = div.find_all("li")
        lis_list = [li.text.strip() for li in lis]
    except:
        print("Something went wrong while getting company information list")
        lis_list = []

    company_information_dict = extract_company_details(lis_list)
    company_information_dict["investors"] = extract_investor_no(company_name)
    company_information_dict["industry"] = industry

    return competitors, funding, company_information_dict


def get_wiki_link(company: str) -> tuple:
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

    try:
        base, query = url(company, 'wiki')
        driver.get(base)
        time.sleep(2)

        search_input = driver.find_element(By.NAME, "q")
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.RETURN)

        time.sleep(3)  # Allow results to load
        page = driver.page_source
        soup = BeautifulSoup(page, 'html.parser')

        driver.quit()
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
                label = row.find("th")
                data = row.find("td")
                if label and data:
                    info_label.append(label.text.strip())
                    info_data.append(data.text.strip())

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

        if not any(keyword in large_text.text.strip().lower() for keyword in company_keywords):
            raise Exception("Name entered is most likely not a company.")

        # Process the extracted financial and business data
        company_info = {}
        units = ["hundred", "thousand", "million", "billion", "trillion"]

        for i in range(len(info_label)):
            money_field = False
            is_present = [st in info_data[i] for st in units]
            money_field = any(is_present)

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

        return company_name, company_info, new_dsc
    except Exception as e:
        print(f"Something went wrong while scrapping from wikipedia: {e}")
        raise Exception(
            f"Something went wrong while scrapping from wikipedia: {e}")


def get_sentiment_category(text: str) -> tuple:
    """Analyzes the sentiment of a given text and categorizes it as positive, negative, or neutral.

    This function uses the VADER SentimentIntensityAnalyzer to compute the sentiment score of the input text.
    It returns the compound sentiment score as well as the sentiment category.

    Args:
        text (str): The input text to analyze for sentiment.

    Returns:
        tuple: A tuple containing:
            - float: The compound sentiment score, ranging from -1 (most negative) to 1 (most positive).
            - str: The sentiment category, which can be one of "positive", "negative", or "neutral".
    """
    analyzer = SentimentIntensityAnalyzer()
    score = analyzer.polarity_scores(text)

    if score["compound"] > 0.05:
        sent = "positive"
    elif score["compound"] < -0.05:
        sent = "negative"
    else:
        sent = "neutral"

    return score["compound"], sent


def remove_emojis(text: str) -> str:
    """Removes all emojis from the given text.

    This function uses a regular expression to identify and remove all Unicode characters
    that match the emoji patterns, including emoticons, transport symbols, flags, and other
    pictographs.

    Args:
        text (str): The input string from which emojis will be removed.

    Returns:
        str: The input string with all emojis removed.
    """
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002700-\U000027BF"  # dingbats
        u"\U000024C2-\U0001F251"  # enclosed characters
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r"", text)


def fetch_google_news(company_name: str, limit: int = 10) -> list:
    """Fetches the latest news articles about a company from Google News.

    This function fetches the latest news related to the given company from Google News,
    processes each article"s title to analyze sentiment, and returns a list of articles
    with relevant details.

    Args:
        company_name (str): The name of the company for which to fetch news articles.
        limit (int, optional): The maximum number of articles to return. Defaults to 10.

    Returns:
        list: A list of dictionaries containing details of the fetched articles. Each dictionary
              includes the article ID, title, publication date, link, source, source link, and
              sentiment score.
    """
    query = company_name.replace(" ", "+")
    articles = []

    try:
        rss_url = f"https://news.google.com/rss/search?q={query}"
        feed = feedparser.parse(rss_url)
        sorted_feed = sorted(
            feed.entries, key=lambda x: x.published_parsed, reverse=True)

        for entry in sorted_feed[:limit]:
            score, _ = get_sentiment_category(entry.title.split(" - ")[0])
            dt = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %Z")
            iso_format = dt.isoformat() + "Z"
            details = {
                "id": entry.id,
                "title": remove_emojis(entry.title.split(" - ")[0]),
                "published": iso_format,
                "link": entry.link,
                "source": entry.source.title,
                "source_link": entry.source.href,
                "sentiment_score": score
            }
            articles.append(details)

    except Exception as e:
        print(f"Something went wrong while scrapping from google feed: {e}")
        raise Exception(
            f"Something went wrong while scrapping from google feed: {e}")

    return articles
