# nlai_crawler

A Python crawler that downloads bibliographic records from the National Library
and Archives of Iran's online catalog and saves them as JSON files.

## Requirements

- Python 3.14 or newer.
- [uv](https://docs.astral.sh/uv/) for dependency and virtual environment management.
- Internet access to `https://opac.nlai.ir/`.

Dependencies are declared in `pyproject.toml` and locked in `uv.lock`:

| Package          | Purpose                                 |
|------------------|-----------------------------------------|
| `beautifulsoup4` | Extract bibliographic fields from HTML  |
| `lxml`           | Parse HTML for Beautiful Soup           |
| `requests`       | Fetch catalog pages with retries        |
| `joblib`         | Run requests concurrently               |

## Setup

Install the locked dependencies into the project's `.venv`:

```sh
uv sync --locked
```

The commands below use `uv run`, so activating the virtual environment manually
is not necessary.

## Run the crawler

The entry point is `src/main.py`. Run it from the project root:

```sh
uv run python -m src.main
```

To choose a starting record ID, for example 1:

```sh
uv run python -m src.main --start 1
```

To view command-line options without starting a crawl:

```sh
uv run python -m src.main --help
```

Without `--start`, the crawler starts at the greatest ending ID in existing
range filenames, or at 0 if there are none. It skips existing batch filenames;
this resume mechanism does not validate their contents or repair earlier gaps.
The crawl uses eight worker threads and batches of 100 IDs, with batch starts
below 11,000,000. There is currently no command-line option for an ending ID.

## Output directory

Files are named `<start>-<end>.json`, where the ending ID is exclusive. For
example, `--start 1` writes its first batch to `data/1-101.json`, containing
requested IDs 1 through 100. Each file maps string record IDs to dictionaries of
bibliographic field labels and text values.
