"""
Download the NYT Archive API for every month from 2000 to present.
Saves each month as data/raw/YYYY_MM.parquet. Skips files that already exist,
so the script is safe to re-run after interruption.
"""

import os
import sys
import time
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NYT_API_KEY")
if not API_KEY:
    sys.exit("NYT_API_KEY not set in .env")

RAW_DIR = Path("data/raw")
START_YEAR = 2000
REQUEST_INTERVAL = 7   # seconds between requests; NYT cap is 10/min
MAX_RETRIES = 3

_KW_STRUCT = pa.struct([pa.field("name", pa.string()), pa.field("value", pa.string())])
SCHEMA = pa.schema([
    ("article_id",   pa.string()),
    ("pub_date",     pa.string()),
    ("headline",     pa.string()),
    ("section_name", pa.string()),
    ("news_desk",    pa.string()),
    ("keywords",     pa.list_(_KW_STRUCT)),
])


def month_range(start_year: int) -> list[tuple[int, int]]:
    today = date.today()
    pairs = []
    for year in range(start_year, today.year + 1):
        for month in range(1, 13):
            if year == today.year and month >= today.month:
                return pairs  # skip current month — archive API only covers completed months
            pairs.append((year, month))
    return pairs


def fetch_month(year: int, month: int) -> list[dict]:
    url = f"https://api.nytimes.com/svc/archive/v1/{year}/{month}.json"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params={"api-key": API_KEY}, timeout=60)
            if resp.status_code == 429:
                wait = 30 * attempt
                print(f"  [429] rate limited — sleeping {wait}s", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["response"]["docs"]
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise
            print(f"  [error] {exc} — retry {attempt}/{MAX_RETRIES}", flush=True)
            time.sleep(12 * attempt)
    return []


def docs_to_table(docs: list[dict]) -> pa.Table:
    ids, dates, headlines, sections, desks, keywords = [], [], [], [], [], []
    for doc in docs:
        ids.append(doc.get("_id") or "")
        dates.append(doc.get("pub_date") or "")
        headlines.append((doc.get("headline") or {}).get("main") or "")
        sections.append(doc.get("section_name") or "")
        desks.append(doc.get("news_desk") or "")
        keywords.append([
            {"name": kw.get("name") or "", "value": kw.get("value") or ""}
            for kw in (doc.get("keywords") or [])
        ])
    return pa.table(
        {"article_id": ids, "pub_date": dates, "headline": headlines,
         "section_name": sections, "news_desk": desks, "keywords": keywords},
        schema=SCHEMA,
    )


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    months = month_range(START_YEAR)
    total = len(months)
    already_done = sum(1 for y, m in months if (RAW_DIR / f"{y}_{m:02d}.parquet").exists())
    to_fetch = total - already_done

    print(f"NYT Archive ingestion")
    print(f"  {total} months  |  {already_done} cached  |  {to_fetch} to download")
    if to_fetch > 0:
        mins = (to_fetch * REQUEST_INTERVAL) // 60
        print(f"  estimated time: ~{mins} min at {REQUEST_INTERVAL}s/request\n")

    fetched = 0
    for i, (year, month) in enumerate(months, 1):
        path = RAW_DIR / f"{year}_{month:02d}.parquet"
        if path.exists():
            continue

        label = f"[{i}/{total}] {year}-{month:02d}"
        print(f"{label} fetching ...", end=" ", flush=True)
        docs = fetch_month(year, month)
        pq.write_table(docs_to_table(docs), path)
        fetched += 1
        print(f"{len(docs):,} articles")

        if fetched < to_fetch:
            time.sleep(REQUEST_INTERVAL)

    print(f"\nDone — {fetched} months downloaded, {already_done} already existed.")


if __name__ == "__main__":
    main()
