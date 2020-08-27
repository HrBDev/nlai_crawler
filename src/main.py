# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup

from src.settings import mycol


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
        mycol.insert_one(schema)


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
        mycol.insert_one(schema)


if __name__ == '__main__':
    # opac_nlai()
    libs_nlai()
