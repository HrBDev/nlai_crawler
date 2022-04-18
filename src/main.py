# -*- coding: utf-8 -*-
import json

import requests
from bs4 import BeautifulSoup
from joblib import Parallel, delayed

from settings import target_collection


def opac_nlai():
    for i in range(1, 7265830):
        url = f"http://opac.nlai.ir/opac-prod/bibliographic/{i}"
        print(url)
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features="lxml")
        form = soup.find("form",
                         attrs={"name": "search_BrowseSearchHitsForm"})
        formcontent = form.find('td', attrs={"class": "formcontent"})
        td = formcontent.find('td', attrs={"width": "100%"})
        rows = td.find_all('tr')
        schema = {}
        for row in rows:
            row_list = row.find_all('td')
            key = row_list[0].text
            value = row_list[2].text
            if schema.get(key) is not None:
                new_val = schema[key] + " " + value
                schema[key] = new_val
            else:
                schema[key] = value
        target_collection.insert_one(schema)


def opac_nlai_write_to_json(range_start, range_end):
    results = Parallel(n_jobs=8)(delayed(scrape)(i) for i in range(range_start, range_end))
    results_as_dict = {}
    preceding_text = 1
    with open(f"dataset1.json", 'w', encoding='utf-8') as outfile:
        for i in range(len(results)):
            results_as_dict[str(preceding_text)] = results[i]
            preceding_text += 1
        json.dump(results_as_dict, outfile, indent=4, ensure_ascii=False)


def scrape(i):
    url = f"http://opac.nlai.ir/opac-prod/bibliographic/{i}"
    print(url)
    response = requests.get(url)
    soup = BeautifulSoup(response.content, features="lxml")
    form = soup.find("form",
                     attrs={"name": "search_BrowseSearchHitsForm"})
    formcontent = form.find('td', attrs={"class": "formcontent"})
    td = formcontent.find('td', attrs={"width": "100%"})
    rows = td.find_all('tr')
    item = {}
    translatable = str.maketrans('', '', '\u200f\u202a\u202b\u202c\u202d\u202e')
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


# Does not work anymore
def libs_nlai():
    for i in range(1, 2324306):
        url = f"https://libs.nlai.ir/bibliography/{i}"
        print(url)
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features="lxml")
        table = soup.find('tbody')
        rows = table.find_all('tr')
        schema = {}
        for row in rows:
            key = row.find('th').text
            value = row.find('td').text
            if schema.get(key) is not None:
                new_val = schema[key] + "," + value
                schema[key] = new_val
            else:
                schema[key] = value
        schema['index'] = i
        target_collection.insert_one(schema)


if __name__ == '__main__':
    opac_nlai_write_to_json(1, 7265830)
