import json
import logging
import os

from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def remove_empty_json_objects(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as infile:
            data = json.load(infile)
        with open(file_path, 'w', encoding='utf-8') as outfile:
            json.dump({k: v for k, v in data.items() if v}, outfile, indent=4, ensure_ascii=False)

    except (json.JSONDecodeError, OSError) as e:
        logging.error(f"Error processing {file_path}: {e}")


def get_path_of_all_files_in_dir(directory):
    return [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]


if __name__ == '__main__':
    files = get_path_of_all_files_in_dir("./data")

    for path in tqdm(files, desc="Processing files"):
        remove_empty_json_objects(path)

    print("All files have been processed.")
