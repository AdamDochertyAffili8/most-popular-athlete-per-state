"""
Identify the most-covered athlete per US state per year from NYT data.

Usage (run from project root):
    python -m src.analyze                        # all years
    python -m src.analyze --years 2010 2015      # specific years
    python -m src.analyze --min-articles 5       # raise noise threshold

Output:
    results/rankings.parquet    full ranked table (all athletes, all states, all years)
    results/rankings.csv        same, human-readable
    results/top_per_state.csv   rank-1 athlete per state per year
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.states import (
    NON_ATHLETES,
    SPORT_CATEGORIES,
    SPORTS_SUBJECTS,
    clean_person_name,
    glocation_to_state,
    organizations_to_states,
)

PROCESSED_DIR = Path("data/processed")
RESULTS_DIR = Path("results")
DEFAULT_MIN_ARTICLES = 2


def load_processed(years: list[int] | None) -> pd.DataFrame:
    files = sorted(PROCESSED_DIR.glob("*.parquet"))
    if years:
        files = [f for f in files if int(f.stem) in years]
    if not files:
        sys.exit(f"No processed Parquet files found in {PROCESSED_DIR}/")
    print(f"Loading {len(files)} year file(s)...", flush=True)
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def filter_sports(df: pd.DataFrame) -> pd.DataFrame:
    def _is_sports(subs) -> bool:
        return bool(subs is not None and len(subs) > 0 and any(s in SPORTS_SUBJECTS for s in subs))
    return df[df["subjects"].apply(_is_sports)].copy()


def explode_persons(df_sports: pd.DataFrame) -> pd.DataFrame:
    out = (
        df_sports[["article_id", "year", "persons"]]
        .explode("persons")
        .rename(columns={"persons": "person"})
        .dropna(subset=["person"])
    )
    out["person"] = out["person"].apply(clean_person_name)
    out = out[out["person"] != ""]
    out = out[~out["person"].isin(NON_ATHLETES)]
    return out.reset_index(drop=True)


def explode_glocation_states(df_sports: pd.DataFrame) -> pd.DataFrame:
    out = (
        df_sports[["article_id", "glocations"]]
        .explode("glocations")
        .dropna(subset=["glocations"])
    )
    out["state"] = out["glocations"].map(glocation_to_state)
    return out.dropna(subset=["state"])[["article_id", "state"]]


def explode_org_states(df_sports: pd.DataFrame) -> pd.DataFrame:
    """Map organizations tags (team names) to states and explode to one row per (article, state)."""
    out = (
        df_sports[["article_id", "organizations"]]
        .copy()
    )
    out["state"] = out["organizations"].apply(
        lambda orgs: organizations_to_states(orgs) if orgs is not None and len(orgs) > 0 else []
    )
    return (
        out[["article_id", "state"]]
        .explode("state")
        .dropna(subset=["state"])
        .reset_index(drop=True)
    )


def build_state_pairs(df_sports: pd.DataFrame) -> pd.DataFrame:
    """Combine glocation-based and team-name-based state pairs, deduplicated."""
    gloc_states = explode_glocation_states(df_sports)
    org_states = explode_org_states(df_sports)
    combined = pd.concat([gloc_states, org_states], ignore_index=True)
    return combined.drop_duplicates(subset=["article_id", "state"]).reset_index(drop=True)


def dominant_sport(df_sports: pd.DataFrame, merged: pd.DataFrame) -> pd.DataFrame:
    """Return the most-mentioned sport category per (year, state, athlete)."""
    subj = (
        df_sports[["article_id", "subjects"]]
        .explode("subjects")
        .dropna(subset=["subjects"])
        .rename(columns={"subjects": "subject"})
    )
    subj["sport"] = subj["subject"].map(SPORT_CATEGORIES)
    subj = subj.dropna(subset=["sport"])

    sport_counts = (
        merged.merge(subj[["article_id", "sport"]], on="article_id", how="inner")
        .groupby(["year", "state", "person", "sport"])["article_id"]
        .nunique()
        .reset_index()
        .rename(columns={"person": "athlete", "article_id": "n"})
        .sort_values("n", ascending=False)
        .drop_duplicates(subset=["year", "state", "athlete"], keep="first")
        [["year", "state", "athlete", "sport"]]
    )
    return sport_counts


def build_rankings(
    df_persons: pd.DataFrame,
    df_states: pd.DataFrame,
    df_sports: pd.DataFrame,
    min_articles: int,
) -> pd.DataFrame:
    merged = df_persons.merge(df_states, on="article_id")

    counts = (
        merged
        .groupby(["year", "state", "person"])["article_id"]
        .nunique()
        .reset_index()
        .rename(columns={"person": "athlete", "article_id": "article_count"})
    )

    counts = counts[counts["article_count"] >= min_articles].copy()

    # Attach dominant sport
    sport_df = dominant_sport(df_sports, merged)
    counts = counts.merge(sport_df, on=["year", "state", "athlete"], how="left")
    counts["sport"] = counts["sport"].fillna("Other")

    counts["rank"] = (
        counts
        .groupby(["year", "state"])["article_count"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    return counts.sort_values(["year", "state", "rank"]).reset_index(drop=True)


def print_sample(top: pd.DataFrame, sample_year: int) -> None:
    sample = top[top["year"] == sample_year].sort_values("state")
    if sample.empty:
        return
    print(f"\n--- Top athlete per state, {sample_year} ---")
    print(f"{'State':<25} {'Athlete':<35} {'Articles':>8}")
    print("-" * 70)
    for _, row in sample.iterrows():
        print(f"{row['state']:<25} {row['athlete']:<35} {row['article_count']:>8,}")


def main(years: list[int] | None = None, min_articles: int = DEFAULT_MIN_ARTICLES) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)

    df = load_processed(years)
    print(f"  {len(df):,} total articles loaded")

    df_sports = filter_sports(df)
    pct = len(df_sports) / len(df) * 100
    print(f"  {len(df_sports):,} sports articles ({pct:.1f}%)")

    df_persons = explode_persons(df_sports)
    df_states = build_state_pairs(df_sports)
    print(f"  {len(df_persons):,} person-article pairs")
    print(f"  {len(df_states):,} US state-article pairs (glocations + team names)")
    print(f"  min article threshold: {min_articles}")

    print("\nBuilding rankings...", flush=True)
    rankings = build_rankings(df_persons, df_states, df_sports, min_articles)

    rankings.to_parquet(RESULTS_DIR / "rankings.parquet", index=False)
    rankings.to_csv(RESULTS_DIR / "rankings.csv", index=False)
    print(f"Saved {len(rankings):,} rows -> results/rankings.parquet + .csv")

    top = rankings[rankings["rank"] == 1].copy()
    top.to_csv(RESULTS_DIR / "top_per_state.csv", index=False)
    print(f"Saved {len(top):,} top-athlete rows -> results/top_per_state.csv")

    sample_year = (years[len(years) // 2] if years else 2010)
    print_sample(top, sample_year)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="*", type=int)
    parser.add_argument("--min-articles", type=int, default=DEFAULT_MIN_ARTICLES)
    args = parser.parse_args()
    main(args.years, args.min_articles)
