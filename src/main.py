import os
import re
import logging
import json
import argparse
from joblib import Parallel, delayed
import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def write_range_to_json(range_start, range_end, base_url):
    results = Parallel(n_jobs=8, backend='threading')(
        delayed(scrape)(f"{base_url}{k}") for k in range(range_start, range_end))
    results_as_dict = {str(j + range_start): results[j] for j in range(len(results))}
    with open(f"./data/{range_start}-{range_end}.json", 'w', encoding='utf-8') as outfile:
        json.dump(results_as_dict, outfile, indent=4, ensure_ascii=False)
    logging.info(f"Saved data from {range_start} to {range_end}")


def scrape(url):
    s = requests.Session()
    retries = Retry(total=10, backoff_factor=0.1)
    s.mount('https://opac.nlai.ir/', HTTPAdapter(max_retries=retries))
    try:
        response = s.get(url=url, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, features="lxml")
        form = soup.find("form", attrs={"name": "search_BrowseSearchHitsForm"})
        if not form:
            return {}
        formcontent = form.find('td', attrs={"class": "formcontent"})
        td = formcontent.find('td', attrs={"width": "100%"})
        rows = td.find_all('tr')
        item = {}
        translatable = str.maketrans('', '', '\u200e\u200c\u200f\u202a\u202b\u202c\u202d\u202e')
        for row in rows:
            row_list = row.find_all('td')
            key = row_list[0].text.translate(translatable)
            value = row_list[2].text.translate(translatable)
            if key in item:
                item[key] += " " + value
            else:
                item[key] = value
        return item
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 500:
            logging.warning(f"Received 500 error for URL: {url}. Skipping.")
            return {}
        else:
            logging.error(f"HTTP error occurred for URL {url}: {e}")
            raise


def find_last_completed_range(data_dir_path: str):
    files = [f for f in os.listdir(data_dir_path) if f.endswith(".json")]
    max_end = 0
    for f in files:
        match = re.match(r"(\d+)-(\d+)\.json", f)
        if match:
            _, end = map(int, match.groups())
            if end > max_end:
                max_end = end
    return max_end


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scrape bibliographic data")
    parser.add_argument("--start", type=int, help="Optional start index for scraping")
    args = parser.parse_args()

    data_dir = "./data"
    os.makedirs(data_dir, exist_ok=True)

    if args.start:
        start_index = args.start
        logging.info(f"Starting from user-provided index {start_index}")
    else:
        start_index = find_last_completed_range(data_dir)
        logging.info(f"Starting from last completed range {start_index}")

    for i in range(start_index, 11000000, 100):
        file_path = f"{data_dir}/{i}-{i + 100}.json"
        if not os.path.exists(file_path):
            write_range_to_json(i, i + 100, "https://opac.nlai.ir/opac-prod/bibliographic/")
        else:
            logging.info(f"{file_path} exists, skipping.")
