import os
import sys
from collections import defaultdict

import requests
from dotenv import load_dotenv

load_dotenv()

NYT_API_KEY = os.getenv("NYT_API_KEY")
if not NYT_API_KEY:
    sys.exit("NYT_API_KEY not set in .env")


def fetch_month(year: int, month: int) -> list[dict]:
    url = f"https://api.nytimes.com/svc/archive/v1/{year}/{month}.json"
    resp = requests.get(url, params={"api-key": NYT_API_KEY}, timeout=30)
    resp.raise_for_status()
    return resp.json()["response"]["docs"]


def group_keywords(keywords: list[dict]) -> dict[str, list[str]]:
    grouped = defaultdict(list)
    for kw in keywords:
        grouped[kw["name"]].append(kw["value"])
    return dict(grouped)


def print_summary(docs: list[dict], year: int, month: int, sample_size: int = 8) -> None:
    print(f"\nNYT Archive — {year}-{month:02d}")
    print(f"Total articles: {len(docs):,}\n")
    print(f"--- Sample ({sample_size} evenly-spaced articles) ---\n")

    step = max(1, len(docs) // sample_size)
    samples = [docs[i * step] for i in range(sample_size)]

    for i, doc in enumerate(samples, 1):
        headline = doc.get("headline", {}).get("main", "(no headline)")
        kw = group_keywords(doc.get("keywords", []))
        print(f"[{i}] {headline}")
        print(f"     section : {doc.get('section_name') or '—'}")
        print(f"     desk    : {doc.get('news_desk') or '—'}")
        for tag_type in ("persons", "glocations", "subject"):
            values = kw.get(tag_type)
            if values:
                print(f"     {tag_type:<9}: {', '.join(values)}")
        print()


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    month = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    docs = fetch_month(year, month)
    print_summary(docs, year, month)
