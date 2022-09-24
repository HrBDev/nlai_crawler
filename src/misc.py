import json
import os


def remove_empty_json_objects(file_path):
    with open(file_path, 'r', encoding='utf-8') as infile:
        data = json.load(infile)
        infile.close()
    with open(file_path, 'w', encoding='utf-8') as outfile:
        json.dump({k: v for k, v in data.items() if v}, outfile, indent=4, ensure_ascii=False)
        outfile.close()


def get_path_of_all_files_in_dir():
    return [f"./data/{f}" for f in os.listdir("./data")]


if __name__ == '__main__':
    for path in get_path_of_all_files_in_dir():
        try:
            remove_empty_json_objects(path)
        except:
            pass
