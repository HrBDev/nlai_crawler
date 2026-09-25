import os
import re
import json
import logging
import argparse
from collections import Counter
from joblib import Parallel, delayed
import requests
from requests.adapters import HTTPAdapter, Retry

from .atomic_json import write_json_atomic
from .decoder import DecodeError, FetchResult, decode_record
from .report_jsonl import REPORT_NAME, batch_is_complete, write_report

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

POPULATED_RECORD_TARGET = 5_974_628
BATCH_SIZE = 100


def write_range_to_json(range_start, range_end, base_url):
    results = Parallel(n_jobs=8, backend='threading')(
        delayed(scrape)(f"{base_url}{k}") for k in range(range_start, range_end))
    results_as_dict = {
        str(j + range_start): result.data for j, result in enumerate(results)
        if result.status in ('populated', 'empty')
    }
    report = {
        str(j + range_start): {
            'status': result.status, 'http_status': result.http_status,
            'error': result.error,
        } for j, result in enumerate(results) if result.status != 'populated'
    }
    os.makedirs('./data/results', exist_ok=True)
    # Mark pending before changing data; mark complete only after both files
    # are saved. An interruption between writes causes a safe batch retry.
    report_path = f'./data/results/{range_start}-{range_end}.jsonl'
    write_report(report_path, range_start, range_end, report, False)
    write_json_atomic(f"./data/{range_start}-{range_end}.json", results_as_dict)
    complete = all(result.status in ('populated', 'empty') for result in results)
    write_report(report_path, range_start, range_end, report, complete)
    logging.info('Saved data from %s to %s: %s', range_start, range_end,
                 dict(Counter(result.status for result in results)))
    return sum(result.status == 'populated' for result in results)


def scrape(url):
    s = requests.Session()
    retries = Retry(total=10, backoff_factor=0.1)
    s.mount('https://opac.nlai.ir/', HTTPAdapter(max_retries=retries))
    try:
        response = s.get(url=url, timeout=25)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        logging.error('HTTP failure for %s: %s', url, e)
        return FetchResult('http_error', http_status=status, error=str(e))
    except requests.exceptions.RequestException as e:
        logging.error('Network failure for %s: %s', url, e)
        return FetchResult('network_error', error=str(e))
    finally:
        s.close()
    try:
        item = decode_record(response.content)
    except DecodeError as e:
        logging.error('Decoding failure for %s: %s', url, e)
        return FetchResult('decode_error', http_status=response.status_code, error=str(e))
    return FetchResult('populated' if item else 'empty', item, response.status_code)


def find_last_completed_range(data_dir_path: str):
    files = [f for f in os.listdir(data_dir_path) if f.endswith(".json")]
    max_end = 0
    incomplete = []
    report_dir = os.path.join(data_dir_path, 'results')
    if os.path.isdir(report_dir):
        files = set(files) | {
            f'{match.group(1)}-{match.group(2)}.json'
            for name in os.listdir(report_dir)
            if (match := REPORT_NAME.fullmatch(name))
        }
    for f in files:
        match = re.fullmatch(r"(\d+)-(\d+)\.json", f)
        if match:
            start, end = map(int, match.groups())
            if not batch_is_complete(data_dir_path, f):
                incomplete.append(start)
            if end > max_end:
                max_end = end
    return min(incomplete) if incomplete else max_end


def count_populated_in_file(path):
    with open(path, encoding='utf-8') as stream:
        return sum(bool(record) for record in json.load(stream).values())


def count_populated_records(data_dir_path):
    return sum(
        count_populated_in_file(os.path.join(data_dir_path, name))
        for name in os.listdir(data_dir_path)
        if re.fullmatch(r'\d+-\d+\.json', name)
    )


def crawl_until_target(start_index, data_dir_path, target=POPULATED_RECORD_TARGET):
    populated = count_populated_records(data_dir_path)
    logging.info('Starting with %s populated records; target is %s', populated, target)
    index = start_index
    while populated < target:
        end = index + BATCH_SIZE
        file_name = f'{index}-{end}.json'
        file_path = os.path.join(data_dir_path, file_name)
        if not batch_is_complete(data_dir_path, file_name):
            previous = count_populated_in_file(file_path) if os.path.exists(file_path) else 0
            current = write_range_to_json(index, end, "https://opac.nlai.ir/opac-prod/bibliographic/")
            populated += current - previous
        else:
            logging.info('%s exists, skipping.', file_path)
        index = end
    logging.info('Reached populated record target: %s', populated)


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

    crawl_until_target(start_index, data_dir)
