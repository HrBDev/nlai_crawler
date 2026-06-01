# -*- coding: utf-8 -*-
import json
import logging
import os
from os.path import exists as file_exists

import requests
from bs4 import BeautifulSoup
from joblib import Parallel, delayed
from requests.adapters import HTTPAdapter, Retry

import misc
from misc import find_keys

# Configure logging
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


if __name__ == '__main__':
    data_dir = "./data"
    os.makedirs(data_dir, exist_ok=True)
    for i in range(1, 11000000, 100):
        file_path = f"{data_dir}/{i}-{i + 100}.json"
        if not file_exists(file_path):
            write_range_to_json(i, i + 100, "https://opac.nlai.ir/opac-prod/bibliographic/")
        else:
            logging.info(f"{file_path} exists skipping.")
            with open(file_path, 'r', encoding='utf-8') as infile:
                data = json.load(infile)
                keys = find_keys(data)
                missing_keys = misc.find_missing_numbers(i, i + 100, keys)
