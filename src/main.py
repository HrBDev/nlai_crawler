# -*- coding: utf-8 -*-
import json
from os.path import exists as file_exists

import requests
from bs4 import BeautifulSoup
from joblib import Parallel, delayed

def write_range_to_json(range_start, range_end, base_url):
    results = Parallel(n_jobs=8)(delayed(scrape)(f"{base_url}{k}") for k in range(range_start, range_end))
    results_as_dict = {}
    with open(f"./data/{range_start}-{range_end}.json", 'w', encoding='utf-8') as outfile:
        for j in range(len(results)):
            results_as_dict[str(j + range_start)] = results[j]
        json.dump(results_as_dict, outfile, indent=4, ensure_ascii=False)
        outfile.close()


def scrape(url):
    print(url)
    response = requests.get(url)
    soup = BeautifulSoup(response.content, features="lxml")
    form = soup.find("form",
                     attrs={"name": "search_BrowseSearchHitsForm"})
    formcontent = form.find('td', attrs={"class": "formcontent"})
    td = formcontent.find('td', attrs={"width": "100%"})
    rows = td.find_all('tr')
    item = {}
    translatable = str.maketrans('', '', '\u200c\u200f\u202a\u202b\u202c\u202d\u202e')
    for row in rows:
        row_list = row.find_all('td')
        key = row_list[0].text.translate(translatable)
        value = row_list[2].text.translate(translatable)
        if item.get(key) is not None:
            new_val = item[key] + " " + value
            item[key] = new_val
        else:
            item[key] = value
    return item


if __name__ == '__main__':
    for i in range(1, 7265830, 100):
        if not file_exists(f"./data/{i}-{i + 100}.json"):
            write_range_to_json(i, i + 100, "https://opac.nlai.ir/opac-prod/bibliographic/")
