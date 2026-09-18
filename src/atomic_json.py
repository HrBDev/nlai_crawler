import json
import os
import tempfile


def write_json_atomic(file_path, data):
    target = os.path.abspath(file_path)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=os.path.dirname(target),
                prefix=f'.{os.path.basename(target)}.', suffix='.tmp', delete=False,
        ) as outfile:
            temp_path = outfile.name
            json.dump(data, outfile, indent=4, ensure_ascii=False)
        os.replace(temp_path, target)
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


def write_json_lines_atomic(file_path, records):
    """Write one JSON value per line, then replace the destination atomically."""
    target = os.path.abspath(file_path)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', newline='\n',
                dir=os.path.dirname(target),
                prefix=f'.{os.path.basename(target)}.', suffix='.tmp', delete=False,
        ) as outfile:
            temp_path = outfile.name
            for record in records:
                json.dump(record, outfile, ensure_ascii=False, separators=(',', ':'))
                outfile.write('\n')
        os.replace(temp_path, target)
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
