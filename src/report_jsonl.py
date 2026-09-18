"""Per-batch JSON Lines reports containing only non-populated results."""

import json
import os
import re

from .atomic_json import write_json_lines_atomic


REPORT_NAME = re.compile(r'(\d+)-(\d+)\.jsonl')
ISSUE_STATUSES = frozenset(('empty', 'network_error', 'http_error', 'decode_error'))


def report_lines(start, end, results, complete):
    for record_id, result in results.items():
        if result['status'] == 'populated':
            continue
        yield {
            'type': 'result', 'id': record_id,
            'status': result['status'],
            'http_status': result['http_status'],
            'error': result['error'],
        }
    yield {'type': 'batch', 'start': start, 'end': end, 'complete': complete}


def write_report(path, start, end, results, complete):
    write_json_lines_atomic(path, report_lines(start, end, results, complete))


def _valid_results(results, start, end):
    return (isinstance(results, dict)
            and set(results) <= {str(i) for i in range(start, end)}
            and all(isinstance(row, dict)
                    and row.get('status') == 'empty'
                    for row in results.values()))


def jsonl_report_is_complete(path, start, end):
    results = {}
    marker = None
    try:
        with open(path, encoding='utf-8') as infile:
            for line in infile:
                row = json.loads(line)
                if not isinstance(row, dict):
                    return False
                if row.get('type') == 'result' and marker is None:
                    record_id = row.get('id')
                    if (not isinstance(record_id, str) or record_id in results
                            or row.get('status') not in ISSUE_STATUSES):
                        return False
                    results[record_id] = row
                elif row.get('type') == 'batch' and marker is None:
                    marker = row
                else:
                    return False
    except (OSError, ValueError, TypeError):
        return False
    return (marker is not None
            and marker.get('start') == start
            and marker.get('end') == end
            and marker.get('complete') is True
            and _valid_results(results, start, end))


def batch_is_complete(data_dir, filename):
    if not os.path.isfile(os.path.join(data_dir, filename)):
        return False
    match = re.fullmatch(r'(\d+)-(\d+)\.json', filename)
    if match is None:
        return False
    start, end = map(int, match.groups())
    report_dir = os.path.join(data_dir, 'results')
    jsonl_path = os.path.join(report_dir, f'{start}-{end}.jsonl')
    if not os.path.exists(jsonl_path):
        return True  # Data files without reports retain filename-based resume.
    return jsonl_report_is_complete(jsonl_path, start, end)
