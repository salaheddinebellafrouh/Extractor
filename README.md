# Academic Paper Extractor

A lightweight Python script that pulls paper metadata from the [OpenAlex API](https://openalex.org) and exports it to CSV.

Built as a reusable template for academic/bibliographic data extraction. The same pattern (auth, cursor pagination, retry with backoff, flat record normalization) applies to Web of Science, Scopus, and Crossref with minimal changes, only the endpoint and field paths differ.

## Features

- No API key required (uses OpenAlex, which is free and open)
- Cursor-based pagination for large result sets
- Automatic retry with exponential backoff on rate limits and transient errors
- Clean flat CSV output, one row per paper
- Filter by search query and year range
- Sorted by citation count by default

## Requirements

- Python 3.10+
- `requests`

Install the dependency:

```bash
pip install requests
```

## Usage

```bash
python extractor1.py --query "machine learning healthcare" --from 2022 --to 2024 --limit 50 --out results.csv
```

### Arguments

| Argument  | Required | Description                                       |
|-----------|----------|---------------------------------------------------|
| `--query` | Yes      | Search query, e.g. `"climate change agriculture"` |
| `--from`  | No       | Start year (e.g. `2022`)                          |
| `--to`    | No       | End year (e.g. `2024`)                            |
| `--limit` | No       | Max number of records (default: 50)               |
| `--out`   | No       | Output CSV path (default: `results.csv`)          |

### Examples

Pull the top 100 cited papers on quantum computing from 2023 onward:

```bash
python extractor1.py --query "quantum computing" --from 2023 --limit 100 --out quantum.csv
```

Pull papers on a narrow topic into a custom file:

```bash
python extractor1.py --query "federated learning medical imaging" --from 2021 --to 2024 --limit 200 --out fed_learning.csv
```

## Output fields

Each row in the CSV contains:

- `openalex_id`
- `title`
- `authors` (semicolon-separated)
- `institutions` (semicolon-separated, deduplicated)
- `source_title` (journal or venue)
- `publish_year`, `publish_date`
- `doi`
- `issn_l`
- `document_type`
- `is_open_access`
- `times_cited`
- `reference_count`

## Adapting to other APIs

The script is structured so the API-specific pieces are isolated:

- `build_session()` — authentication headers
- `fetch_page()` — pagination logic
- `normalize_record()` — field mapping

To adapt it for Web of Science, Scopus, or another source, swap the endpoint URL, update the auth header, and rewrite `normalize_record()` to match the new response shape. The rest of the pipeline stays the same.

## Notes

- OpenAlex asks that clients identify themselves in the `User-Agent` header for faster, more reliable access (the "polite pool"). Replace the placeholder email in `build_session()` with your own before running at scale.
- The Starter API for Web of Science has a free tier limited to 50 requests per day and does not include citation counts. Paid tiers are tied to institutional subscriptions.

## License

MIT
