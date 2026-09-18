import os
import re
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

    for i in range(start_index, 12000000, 100):
        file_path = f"{data_dir}/{i}-{i + 100}.json"
        if not batch_is_complete(data_dir, os.path.basename(file_path)):
            write_range_to_json(i, i + 100, "https://opac.nlai.ir/opac-prod/bibliographic/")
        else:
            logging.info(f"{file_path} exists, skipping.")
