"""
Process raw per-month Parquet files into a clean per-year dataset.

Input:  data/raw/YYYY_MM.parquet  (one per month)
Output: data/processed/YYYY.parquet  (one per year)

Each output row is one article with keyword lists split by type:
  persons[], glocations[], subjects[]
"""

import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

SCHEMA = pa.schema([
    ("article_id",    pa.string()),
    ("pub_date",      pa.string()),
    ("year",          pa.int16()),
    ("month",         pa.int8()),
    ("headline",      pa.string()),
    ("section_name",  pa.string()),
    ("news_desk",     pa.string()),
    ("persons",       pa.list_(pa.string())),
    ("glocations",    pa.list_(pa.string())),
    ("subjects",      pa.list_(pa.string())),
    ("organizations", pa.list_(pa.string())),
])


def split_keywords(keywords) -> tuple[list[str], list[str], list[str], list[str]]:
    persons, glocations, subjects, organizations = [], [], [], []
    for kw in keywords:
        name = kw["name"]
        value = kw["value"]
        if name == "persons":
            persons.append(value)
        elif name == "glocations":
            glocations.append(value)
        elif name == "subject":
            subjects.append(value)
        elif name == "organizations":
            organizations.append(value)
    return persons, glocations, subjects, organizations


def process_year(year: int) -> pa.Table | None:
    month_files = sorted(RAW_DIR.glob(f"{year}_*.parquet"))
    if not month_files:
        return None

    ids, dates, years, months = [], [], [], []
    headlines, sections, desks = [], [], []
    persons_col, glocations_col, subjects_col, organizations_col = [], [], [], []

    for path in month_files:
        month_num = int(path.stem.split("_")[1])
        table = pq.read_table(path)

        for i in range(table.num_rows):
            row = {col: table.column(col)[i].as_py() for col in table.schema.names}
            persons, glocations, subjects, organizations = split_keywords(row["keywords"] or [])

            ids.append(row["article_id"])
            dates.append(row["pub_date"])
            years.append(year)
            months.append(month_num)
            headlines.append(row["headline"])
            sections.append(row["section_name"])
            desks.append(row["news_desk"])
            persons_col.append(persons)
            glocations_col.append(glocations)
            subjects_col.append(subjects)
            organizations_col.append(organizations)

    return pa.table(
        {
            "article_id":    ids,
            "pub_date":      dates,
            "year":          pa.array(years, type=pa.int16()),
            "month":         pa.array(months, type=pa.int8()),
            "headline":      headlines,
            "section_name":  sections,
            "news_desk":     desks,
            "persons":       persons_col,
            "glocations":    glocations_col,
            "subjects":      subjects_col,
            "organizations": organizations_col,
        },
        schema=SCHEMA,
    )


def main(years: list[int] | None = None) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if years is None:
        available = sorted({int(p.stem[:4]) for p in RAW_DIR.glob("*.parquet")})
    else:
        available = sorted(years)

    if not available:
        sys.exit(f"No raw Parquet files found in {RAW_DIR}/")

    print(f"Processing {len(available)} years: {available[0]}–{available[-1]}\n")

    total_articles = 0
    for year in available:
        out_path = PROCESSED_DIR / f"{year}.parquet"
        print(f"  {year} ... ", end="", flush=True)
        table = process_year(year)
        if table is None:
            print("no raw files found, skipping")
            continue
        pq.write_table(table, out_path)
        total_articles += table.num_rows
        print(f"{table.num_rows:,} articles -> {out_path}")

    print(f"\nDone — {total_articles:,} articles total across {len(available)} years.")


if __name__ == "__main__":
    import sys
    years = [int(y) for y in sys.argv[1:]] if len(sys.argv) > 1 else None
    main(years)
