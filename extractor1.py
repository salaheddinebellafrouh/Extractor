
import argparse
import csv
import sys
import time
from typing import Any

import requests

OPENALEX_URL = "https://api.openalex.org/works"
PAGE_SIZE = 50
MAX_RETRIES = 3
BACKOFF_SECONDS = 2


def build_session() -> requests.Session:
    """Create a reusable HTTP session. OpenAlex asks for a contact email in
    the User-Agent for their 'polite pool' (faster + more reliable)."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": "paper-extractor-demo/1.0 (mailto:demo@example.com)",
        "Accept": "application/json",
    })
    return s


def fetch_page(session: requests.Session, params: dict, cursor: str) -> dict:
    """Fetch one page with retry/backoff on transient failures."""
    params = {**params, "cursor": cursor, "per-page": PAGE_SIZE}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(OPENALEX_URL, params=params, timeout=30)
            if r.status_code == 429:
                wait = BACKOFF_SECONDS * attempt
                print(f"  Rate limited. Sleeping {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                raise
            print(f"  Retry {attempt}/{MAX_RETRIES} after error: {e}", file=sys.stderr)
            time.sleep(BACKOFF_SECONDS * attempt)
    return {}


def normalize_record(rec: dict[str, Any]) -> dict[str, Any]:
    """Flatten a paper record into a flat CSV row."""
    ids = rec.get("ids", {}) or {}
    primary_location = rec.get("primary_location") or {}
    source = primary_location.get("source") or {}
    authorships = rec.get("authorships", []) or []

    author_list = "; ".join(
        (a.get("author") or {}).get("display_name", "") for a in authorships
    )
    institutions = "; ".join({
        inst.get("display_name", "")
        for a in authorships
        for inst in (a.get("institutions") or [])
        if inst.get("display_name")
    })

    return {
        "openalex_id": rec.get("id", "").replace("https://openalex.org/", ""),
        "title": (rec.get("title") or "").strip(),
        "authors": author_list,
        "institutions": institutions,
        "source_title": source.get("display_name", ""),
        "publish_year": rec.get("publication_year", ""),
        "publish_date": rec.get("publication_date", ""),
        "doi": (ids.get("doi") or "").replace("https://doi.org/", ""),
        "issn_l": source.get("issn_l", ""),
        "document_type": rec.get("type", ""),
        "is_open_access": (rec.get("open_access") or {}).get("is_oa", False),
        "times_cited": rec.get("cited_by_count", 0),
        "reference_count": rec.get("referenced_works_count", 0),
    }


def extract(query: str, year_from: int | None, year_to: int | None,
            limit: int, out_path: str) -> int:
    """Run the extraction and write a CSV. Returns row count."""
    session = build_session()

    filters = [f"title_and_abstract.search:{query}"]
    if year_from and year_to:
        filters.append(f"publication_year:{year_from}-{year_to}")
    elif year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")

    params = {"filter": ",".join(filters), "sort": "cited_by_count:desc"}

    rows: list[dict] = []
    cursor = "*"
    page = 1

    while len(rows) < limit and cursor:
        print(f"Fetching page {page}...", file=sys.stderr)
        data = fetch_page(session, params, cursor)
        results = data.get("results", []) or []
        meta = data.get("meta", {}) or {}
        if page == 1:
            print(f"  Total matching records: {meta.get('count', 0)}", file=sys.stderr)
        if not results:
            break
        for rec in results:
            rows.append(normalize_record(rec))
            if len(rows) >= limit:
                break
        cursor = meta.get("next_cursor")
        page += 1

    if not rows:
        print("No records returned.", file=sys.stderr)
        return 0

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} records to {out_path}", file=sys.stderr)
    return len(rows)


def main() -> None:
    p = argparse.ArgumentParser(description="Academic paper extractor (OpenAlex)")
    p.add_argument("--query", required=True, help='Search query, e.g. "machine learning healthcare"')
    p.add_argument("--from", dest="year_from", type=int, help="Start year, e.g. 2022")
    p.add_argument("--to", dest="year_to", type=int, help="End year, e.g. 2024")
    p.add_argument("--limit", type=int, default=50, help="Max records")
    p.add_argument("--out", default="results.csv", help="Output CSV path")
    args = p.parse_args()

    extract(args.query, args.year_from, args.year_to, args.limit, args.out)


if __name__ == "__main__":
    main()