"""
Generate an interactive US choropleth map of the most-covered athlete per state per year.

Usage (run from project root):
    python -m src.visualize

Output: results/top_athlete_map.html  (self-contained, open in any browser)
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

RESULTS_DIR = Path("results")

STATE_ABBR: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
}


def fmt_name(name: str) -> str:
    """Convert 'Last, First' NYT format to 'First Last' for display."""
    if pd.isna(name):
        return ""
    parts = str(name).split(",", 1)
    if len(parts) == 2:
        return f"{parts[1].strip()} {parts[0].strip()}"
    return str(name)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_DIR / "top_per_state.csv")
    df = df[df["rank"] == 1].copy()

    # Break ties: highest count first, then alphabetical by athlete
    df = df.sort_values(
        ["year", "state", "article_count", "athlete"],
        ascending=[True, True, False, True],
    )
    df = df.drop_duplicates(subset=["year", "state"], keep="first")

    df["state_abbr"] = df["state"].map(STATE_ABBR)
    df = df.dropna(subset=["state_abbr"])

    # Expand to full grid (all years × all states) so animation frames are consistent
    all_years = sorted(df["year"].unique())
    grid = pd.DataFrame(
        [{"year": y, "state": s, "state_abbr": a} for y in all_years for s, a in STATE_ABBR.items()]
    )
    df = grid.merge(df.drop(columns=["state_abbr"]), on=["year", "state"], how="left")

    df["athlete_display"] = df["athlete"].apply(fmt_name)
    df["label"] = df.apply(
        lambda r: f"{r['athlete_display']} ({int(r['article_count'])} articles)"
        if pd.notna(r["athlete"])
        else "No data (below threshold)",
        axis=1,
    )
    # Plotly needs a numeric value for color; use 0 for missing so they render grey
    df["color_val"] = df["article_count"].fillna(0)

    return df


def build_figure(df: pd.DataFrame) -> go.Figure:
    # Cap color scale at 95th percentile so outliers don't wash out the palette
    p95 = df.loc[df["article_count"].notna(), "article_count"].quantile(0.95)

    fig = px.choropleth(
        df,
        locations="state_abbr",
        locationmode="USA-states",
        color="color_val",
        scope="usa",
        animation_frame="year",
        custom_data=["state", "athlete_display", "article_count", "label"],
        color_continuous_scale=[
            [0.0,  "#e8e8e8"],   # grey for no-data states
            [0.01, "#cce5ff"],
            [0.5,  "#3399ff"],
            [1.0,  "#003d99"],
        ],
        range_color=[0, p95],
        title="Most-Covered Athlete per US State per Year — NYT Archive 2000–2026",
        labels={"color_val": "NYT Articles"},
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "%{customdata[3]}"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(font=dict(size=20), x=0.5, xanchor="center"),
        coloraxis_colorbar=dict(
            title="Articles",
            tickvals=[0, round(p95 * 0.25), round(p95 * 0.5), round(p95 * 0.75), round(p95)],
        ),
        geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="white"),
        margin=dict(l=0, r=0, t=60, b=0),
        height=550,
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            y=0,
            x=0.5,
            xanchor="center",
            buttons=[
                dict(label="Play",  method="animate",
                     args=[None, {"frame": {"duration": 800, "redraw": True}, "fromcurrent": True}]),
                dict(label="Pause", method="animate",
                     args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}]),
            ],
        )],
    )

    # Slow down slider animation to match button
    fig.layout.sliders[0].update(currentvalue=dict(prefix="Year: ", font=dict(size=16)))

    return fig


def main() -> None:
    print("Loading rankings...", flush=True)
    df = load_data()
    print(f"  {df['athlete'].notna().sum():,} state-year slots with data across {df['year'].nunique()} years")

    print("Building figure...", flush=True)
    fig = build_figure(df)

    out_path = RESULTS_DIR / "top_athlete_map.html"
    fig.write_html(str(out_path), include_plotlyjs="cdn")
    print(f"Saved -> {out_path}")
    print("Open that file in any browser to explore the interactive map.")


if __name__ == "__main__":
    main()
