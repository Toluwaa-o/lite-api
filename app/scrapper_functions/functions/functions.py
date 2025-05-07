import numpy as np
import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from country_named_entity_recognition import find_countries
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.scrapper_functions.data.data import macro_indicator_dict, indicator_descriptions
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import re
import time
import feedparser
import os


def url(company: str, wiki: bool) -> str:
    """
    Generates a Google search URL based on the company name and context.

    Args:
        company (str): The name of the company to search for.
        wiki (bool): If True, generates a search query for the company's Wikipedia page.
                     If False, generates a search query for finding the country the company was founded in.

    Returns:
        str: A complete Google search URL for the specified query.
    """

    if wiki:
        keyword = f"{company} company wikipedia"
        return "https://google.com/search?q="+keyword
    else:
        keyword = f"{company} company founded in what country?"
        return "https://google.com/search?q="+keyword


def extract_wiki_link(res: str) -> str:
    """
    Extracts the first Wikipedia link from a Selenium search results page.

    Args:
        res (selenium.webdriver.remote.webelement.WebElement): 
            The Selenium WebElement representing the Google search results.

    Returns:
        str: The direct URL to the company's Wikipedia page.

    Raises:
        Exception: If a Wikipedia link is not found in the search results.
    """
    links = res.find_elements(By.TAG_NAME, "a")
    href = links[0].get_attribute('href')
    if href and "wikipedia.org" in href:
        href = href.split("/url?q=")[-1].split("&")[0]

        return href
    else:
        raise Exception("Cannot find a Wikipedia page for the company")


def get_wiki_link(company: str) -> tuple:
    """
    Retrieves and parses information about a company from its Wikipedia page.

    This function uses a headless browser (via undetected-chromedriver) to perform a Google search 
    for the company, locates the first Wikipedia link in the results, fetches the content of the 
    Wikipedia page, and extracts both structured data from the infobox and descriptive text from 
    the main content. It also verifies that the entity is likely a company by checking for keywords 
    in the introductory paragraph.

    Args:
        company (str): The name of the company to search for.

    Returns:
        tuple:
            - company_name (str): The Wikipedia page title of the company.
            - company_info (dict): A dictionary containing structured information from the infobox.
            - new_dsc (str): The cleaned first paragraph, typically a brief company description.

    Raises:
        Exception: If the Wikipedia page cannot be found, or if the page is not likely about a company.
    """

    print("GOOGLE_CHROME_BIN:", os.getenv("GOOGLE_CHROME_BIN"))
    chrome_path = os.getenv("GOOGLE_CHROME_BIN")
    if not chrome_path:
        raise ValueError("GOOGLE_CHROME_BIN is not set")

    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )
    options.binary_location = chrome_path

    driver = uc.Chrome(options=options)

    try:

        driver.get(url(company, True))
        time.sleep(1)
        results = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "res"))
        )

        uri = extract_wiki_link(results)
        driver.quit()
        response = requests.get(uri)
        soup = BeautifulSoup(response.content, 'html.parser')

        infobox = soup.find('table', class_='infobox')

        if infobox:
            rows = infobox.find_all('tr')
            info_label, info_data = [], []
            for row in rows:
                label = row.find('th')
                data = row.find('td')
                if label and data:
                    info_label.append(label.text.strip())
                    info_data.append(data.text.strip())

        large_text = soup.find('div', class_='mw-body-content')

        desc = ''
        if large_text:
            p_tag = large_text.find('p')
            if p_tag:
                desc = p_tag.text.strip()

        new_dsc = re.sub(r'\[\d*\]', '', desc)

        company_keywords = ["company", "startup", "corporation", "firm",
                            "organization", "business", "enterprise", "subsidiary"]

        if not any(keyword in large_text.text.strip().lower() for keyword in company_keywords):
            raise Exception('Name entered is most likely not a company.')

        company_info = {}
        units = ['hundred', 'thousand', 'million', 'billion', 'trillion']

        for i in range(len(info_label)):
            money_field = False

            is_present = [st in info_data[i] for st in units]
            money_field = any(is_present)

            if money_field:
                pattern = r'US\$\d+.?\d+ \w+'
                res = re.search(pattern, info_data[i])
                if res:
                    company_info[info_label[i].lower()] = res.group()
                else:
                    company_info[info_label[i].lower()] = info_data[i]
            else:
                company_info[info_label[i].lower()] = info_data[i].replace(
                    "\n", ", ").replace(",,", ",")
        company_name = uri.split('/')[-1]

        return company_name, company_info, new_dsc
    except Exception as e:
        print(f"Something went wrong while scrapping from wikipedia: {e}")
        raise Exception(
            f"Something went wrong while scrapping from wikipedia: {e}")


def find_country_of_origin(company: str, african_countries: list, company_info: dict) -> str:
    """
    Attempts to determine the African country of origin for a given company 
    by performing a Google search and scanning the text content of the result page.

    Parameters:
    -----------
    company (str): The name of the company to search for.

    african_countries (list): A list of African country names to match against the page content.

    company_info (dict): A dictionary containing structured information from the infobox.

    Returns:
    --------
    country : str
        The name of the country found in the page content, or an empty string if none matched.
    """
    country_markers = ['headquarters', 'country']

    for marker in country_markers:
        if marker in company_info.keys():
            result = find_countries(company_info[marker])
            if result:
                country_name = result[0][0].name
                return country_name
            else:
                continue

    chrome_path = os.getenv("GOOGLE_CHROME_BIN")
    if not chrome_path:
        raise ValueError("GOOGLE_CHROME_BIN is not set")

    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )
    options.binary_location = chrome_path

    driver = uc.Chrome(options=options)

    try:
        driver.get(url(company, False))
        time.sleep(2)

        elements = driver.find_elements(By.TAG_NAME, 'div')
        full_text = " ".join(set([el.text for el in elements])).lower()
        driver.quit()

        for country in african_countries:
            pattern = r"\b(?:in|from|based in|located in|headquartered in|a[n]?|an)?\s*" + re.escape(
                country.lower()) + r"\b"
            if re.search(pattern, full_text):
                return country

        for country in african_countries:
            if re.search(rf"\b{re.escape(country.lower())}\b", full_text):
                return country

    except Exception as e:
        print(f"Error finding country of origin: {e}")
        driver.quit()

    return ''


def get_macro_data(limit: int, c: str, c_codes: dict, mi_dict: dict, cr_codes: dict) -> dict:
    """
    Fetches macroeconomic data for a specific country, its region, and the world 
    from the World Bank API.

    Args:
        limit (int): Number of data points (years) to retrieve per indicator.
        c (str): Country name (used as a key to retrieve codes).
        c_codes (dict): Mapping of country names to their ISO country codes.
        mi_dict (dict): Dictionary mapping macroeconomic categories to indicator codes and their readable names.
        cr_codes (dict): Mapping of country names to their corresponding region codes.

    Returns:
        dict: A dictionary containing macroeconomic data for:
            - The specified country (`nation`)
            - The country’s region (prefixed with region code)
            - The world (prefixed with 'world')
            - The list of years (`date`)
    """

    country_code = c_codes[c]
    country_region_code = cr_codes[c]

    macro_data_dict = {'nation': [c for _ in range(limit)], 'date': []}

    for cat in mi_dict.keys():
        for code in mi_dict[cat].keys():
            macro_data_dict[mi_dict[cat][code]] = []
            indicator = code
            url = f'https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}?format=json'

            response = requests.get(url)
            data = response.json()

            for item in data[1][:limit]:
                macro_data_dict[mi_dict[cat][code]].append(item['value'])
                macro_data_dict['date'].append(item['date'])

        for code in mi_dict[cat].keys():
            macro_data_dict[f'{country_region_code}_{mi_dict[cat][code]}'] = []
            indicator = code
            url = f'https://api.worldbank.org/v2/country/{country_region_code}/indicator/{indicator}?format=json'

            response = requests.get(url)
            data = response.json()

            for item in data[1][:limit]:
                macro_data_dict[f'{country_region_code}_{mi_dict[cat][code]}'].append(
                    item['value'])
                macro_data_dict['date'].append(item['date'])

        for code in mi_dict[cat].keys():
            macro_data_dict[f'world_{mi_dict[cat][code]}'] = []
            indicator = code
            url = f'https://api.worldbank.org/v2/country/WLD/indicator/{indicator}?format=json'

            response = requests.get(url)
            data = response.json()

            for item in data[1][:limit]:
                macro_data_dict[f'world_{mi_dict[cat][code]}'].append(
                    item['value'])
                macro_data_dict['date'].append(item['date'])

    macro_data_dict['date'] = list(set(macro_data_dict['date']))

    return macro_data_dict


def convert_types(obj):
    """
    Convert NumPy data types to native Python types for JSON serialization.

    This function is useful when dealing with data from pandas or NumPy that contains 
    types like np.int64, np.float64, or np.ndarray which are not directly JSON serializable.

    Args:
        obj: The object to convert. It can be a NumPy scalar (e.g., np.int64),
             a NumPy array, or any other type.

    Returns:
        The equivalent Python-native type:
            - int for NumPy integers
            - float for NumPy floats
            - list for NumPy arrays
            - unchanged if the type is already JSON serializable
    """

    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def get_stats(ds: pd.DataFrame, country_code: str,  region_codes: dict, indicator_codes: dict, year: int = 2024, interval: int = 4) -> dict:
    """
    Extracts and organizes macroeconomic statistics for a given country, including trends
    and comparisons with regional data, from a macroeconomic dataset.

    Args:
        ds (pd.DataFrame): The dataset containing macroeconomic indicators.
        country_code (str): ISO code or identifier for the country.
        region_codes (dict): Mapping of country codes to their respective region codes.
        indicator_codes (dict): Dictionary mapping indicator codes to their readable names,
                                organized by macroeconomic category (e.g., inflation, GDP).
        year (int, optional): The year for which the current statistics are to be retrieved. Default is 2024.
        interval (int, optional): Number of years before the current year to include in trend analysis. Default is 5.

    Returns:
        dict: A dictionary organized by indicator group, where each indicator includes:
            - current_value (value for the specified year)
            - description (description of the indicator)
            - trend (values from the previous interval years)
            - comparison (national vs regional value for the same year)
            - percentage_difference (percentage change between the most recent and 2020's value)
            - volatility_label (categorical label such as "Stable", "Moderately volatile", or "Volatile")
    """

    all_macro_stats = {}

    for group in macro_indicator_dict.keys():
        macro_stats = {}
        years_in_interval = [str(d) for d in range(year - interval, year + 1)]
        for code in indicator_codes[group].keys():
            indicator_name = indicator_codes[group][code]
            macro_stats[f"{indicator_name}"] = {}

            # Extract indicator description
            macro_stats[f"{indicator_name}"]['description'] = indicator_descriptions[indicator_name]

            # Extract current year value for the indicator
            current_value = ds.loc[ds['date'] ==
                                   str(year), indicator_name].values[0]
            macro_stats[f"{indicator_name}"]["current_value"] = convert_types(
                current_value)

            # Extract data for the last 'interval' years
            interval_data = ds.loc[ds['date'].isin(years_in_interval), [
                'date', indicator_name]]

            macro_stats[f"{indicator_name}"]["trend"] = {
                "year": [], 'value': []}
            for i, r in interval_data.iterrows():
                macro_stats[f"{indicator_name}"]["trend"]['year'].append(
                    r['date'][2:])
                macro_stats[f"{indicator_name}"]["trend"]['value'].append(
                    convert_types(r[indicator_name]))

            try:
                # Extract percentage change since 2020
                previous_value = interval_data.loc[interval_data['date']
                                                   == '2020', indicator_name].values[0]

                if previous_value != 0:
                    difference = current_value - previous_value
                    percentage_difference = (difference / previous_value) * 100
                else:
                    percentage_difference = 0

                macro_stats[indicator_name]['percentage_difference'] = percentage_difference
            except Exception as e:
                raise Exception(
                    f"Something went wrong while calculating stats: {e}")

            try:
                # Extract Volatility / Stability
                values = macro_stats[f"{indicator_name}"]["trend"]['value']
                mean = np.mean(values)
                std = np.std(values)

                if mean == 0:
                    volatility_label = "N/A"
                else:
                    cv = std / mean  # Coefficient of Variation

                    if cv < 0.05:
                        volatility_label = "Stable"
                    elif cv < 0.15:
                        volatility_label = "Moderate"
                    else:
                        volatility_label = "Volatile"

                macro_stats[indicator_name]['volatility_label'] = volatility_label
            except Exception as e:
                raise Exception(f"Something went wrong while volatility: {e}")

            # Extract National vs Regional data
            try:
                macro_stats[f"{indicator_name}"]["comparison"] = {}
                regional_value = ds.loc[ds['date'] == str(
                    year), f'{region_codes[country_code]}_{indicator_name}'].values[0]
                macro_stats[f"{indicator_name}"]["comparison"]['regional'] = convert_types(
                    regional_value)
                macro_stats[f"{indicator_name}"]["comparison"]['national'] = convert_types(
                    current_value)
            except KeyError:
                print(f"Region data not found for {indicator_name}")

        all_macro_stats[group] = macro_stats

    return all_macro_stats


def get_sentiment_category(text: str) -> tuple:
    """
    Analyzes the sentiment of the given text and categorizes it as positive, negative, or neutral
    based on the compound score from VADER sentiment analysis.

    Args:
        text (str): The input text to be analyzed.

    Returns:
        tuple:
            - float: Compound sentiment score ranging from -1 (most negative) to +1 (most positive).
            - str: Sentiment category - 'positive', 'negative', or 'neutral'.
    """

    analyzer = SentimentIntensityAnalyzer()
    score = analyzer.polarity_scores(text)

    if score['compound'] > 0.05:
        sent = 'positive'
    elif score['compound'] < -0.05:
        sent = 'negative'
    else:
        sent = 'neutral'

    return score['compound'], sent


def remove_emojis(text: str) -> str:
    """
    Removes emojis and common symbolic icons from a given text string.

    This function uses a regular expression to identify and remove characters 
    in specific Unicode ranges associated with emojis, pictographs, flags, and 
    other non-text symbols. Useful for cleaning text data for NLP or display.

    Args:
        text (str): The input string potentially containing emojis or icons.

    Returns:
        str: The cleaned string with emojis and icons removed.
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
    return emoji_pattern.sub(r'', text)


def fetch_google_news(company_name: str, limit: int = 10) -> list:
    """
    Fetches recent Google News articles related to a given company and analyzes the sentiment of 
    each article's title using VADER sentiment analysis.

    Args:
        company_name (str): The name of the company to search for in Google News.
        limit (int, optional): The number of news articles to fetch. Defaults to 10.

    Returns:
        list of dict: A list of article metadata dictionaries, each containing:
            - id (str): Unique article identifier.
            - title (str): Cleaned title of the news article.
            - published (str): Publication timestamp of the article.
            - link (str): URL to the full news article.
            - source (str): Name of the news source.
            - source_link (str): URL to the news source.
            - sentiment_score (float): VADER compound sentiment score of the article title.

    Raises:
        Exception: If an error occurs during fetching or parsing the RSS feed.
    """

    query = company_name.replace(' ', '+')
    articles = []

    try:
        rss_url = f"https://news.google.com/rss/search?q={query}"
        feed = feedparser.parse(rss_url)
        sorted_feed = sorted(
            feed.entries, key=lambda x: x.published_parsed, reverse=True)

        for entry in sorted_feed[:limit]:
            score, _ = get_sentiment_category(entry.title.split(' - ')[0])
            dt = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %Z')
            iso_format = dt.isoformat() + 'Z'
            details = {
                "id": entry.id,
                "title": remove_emojis(entry.title.split(' - ')[0]),
                "published": iso_format,
                "link": entry.link,
                "source": entry.source.title,
                'source_link': entry.source.href,
                'sentiment_score': score
            }
            articles.append(details)

    except Exception as e:
        print(f"Something went wrong while scrapping from google feed: {e}")
        raise Exception(
            f"Something went wrong while scrapping from google feed: {e}")

    return articles
