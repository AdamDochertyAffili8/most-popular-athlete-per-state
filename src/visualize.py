"""
Generate a styled HTML page with an interactive US choropleth map.

Usage (run from project root):
    python -m src.visualize

Output: docs/index.html  (GitHub Pages root)
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

RESULTS_DIR = Path("results")
DOCS_DIR = Path("docs")

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

SPORT_COLORS: dict[str, str] = {
    "Football":      "#3a7bd5",   # royal blue
    "Basketball":    "#f07d18",   # vivid orange
    "Baseball":      "#d42b2b",   # red
    "Hockey":        "#18b8d4",   # ice cyan
    "Soccer":        "#22a84e",   # green
    "Tennis":        "#c8d41a",   # lime-yellow (tennis ball)
    "Golf":          "#8a3dd4",   # purple
    "Boxing/MMA":    "#d41a8a",   # hot magenta
    "Olympics":      "#d49a1a",   # amber-gold
    "Auto Racing":   "#8a9db8",   # steel grey
    "Horse Racing":  "#956030",   # saddle brown
    "Track & Field": "#1ad4aa",   # mint-teal (distinct from ice-cyan hockey)
    "Other":         "#5a6a80",   # slate
    "No data":       "#252d3a",   # near-invisible dark (blends with bg)
}

SPORT_ORDER = list(SPORT_COLORS.keys())

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Most-Covered Athlete per US State — NYT 2000–2026</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Inter', sans-serif;
      background: #0f1117;
      color: #e8e8e8;
      min-height: 100vh;
    }}

    header {{
      max-width: 960px;
      margin: 0 auto;
      padding: 52px 24px 28px;
    }}

    .kicker {{
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #7a8a9a;
      margin-bottom: 14px;
    }}

    h1 {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: clamp(26px, 4vw, 42px);
      font-weight: 700;
      line-height: 1.15;
      color: #f0f0f0;
      margin-bottom: 18px;
    }}

    .subtitle {{
      font-size: 15px;
      line-height: 1.65;
      color: #9aabb8;
      max-width: 640px;
    }}

    .map-container {{
      max-width: 1100px;
      margin: 8px auto 0;
      padding: 0 12px;
      background: #161b24;
      border-radius: 12px;
      overflow: hidden;
    }}

    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 20px;
      padding: 18px 24px 4px;
    }}

    .legend-item {{
      display: flex;
      align-items: center;
      gap: 7px;
      font-size: 12px;
      color: #bbc8d4;
      font-weight: 500;
    }}

    .legend-swatch {{
      width: 12px;
      height: 12px;
      border-radius: 2px;
      flex-shrink: 0;
    }}

    footer {{
      max-width: 960px;
      margin: 0 auto;
      padding: 24px 24px 48px;
      border-top: 1px solid #1e2530;
      margin-top: 24px;
    }}

    .footnote {{
      font-size: 12px;
      color: #5a6a7a;
      line-height: 1.7;
      max-width: 680px;
    }}

    .footnote strong {{ color: #7a8a9a; }}

    .source {{
      margin-top: 10px;
      font-size: 11px;
      color: #445060;
    }}
  </style>
</head>
<body>

  <header>
    <p class="kicker">Data Journalism · NYT Archive Analysis</p>
    <h1>The Most-Covered Athlete in Every US State</h1>
    <p class="subtitle">
      Using the New York Times Archive API, we identified the athlete mentioned most
      in NYT sports articles linked to each state — by year, from 2000 to 2026.
      State assignment comes from geographic tags and team names in article metadata.
    </p>
  </header>

  <div class="map-container">
    <div class="legend">
      {legend_items}
    </div>
    {plotly_div}
  </div>

  <footer>
    <p class="footnote">
      <strong>Grey states</strong> had no athlete mentioned in 2+ NYT sports articles
      linked to that state in a given year. This reflects The Times' coverage patterns,
      not the absence of sport — smaller and rural states are underrepresented in a
      national newspaper. State attribution is based on NYT geographic keyword tags and
      a lookup of 200+ professional and college sports team names.
      <strong>2026*</strong> covers January–May only (partial year).
    </p>
    <p class="source">
      Data: New York Times Archive API &nbsp;·&nbsp;
      Analysis covers articles tagged with sports subjects, 2000–May 2026
    </p>
  </footer>

  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  {plotly_script}
</body>
</html>"""


def fmt_name(name: str) -> str:
    if pd.isna(name):
        return ""
    parts = str(name).split(",", 1)
    return f"{parts[1].strip()} {parts[0].strip()}" if len(parts) == 2 else str(name)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_DIR / "top_per_state.csv")
    df = df[df["rank"] == 1].copy()
    df = df.sort_values(
        ["year", "state", "article_count", "athlete"],
        ascending=[True, True, False, True],
    )
    df = df.drop_duplicates(subset=["year", "state"], keep="first")
    df["state_abbr"] = df["state"].map(STATE_ABBR)
    df = df.dropna(subset=["state_abbr"])

    all_years = sorted(df["year"].unique())
    grid = pd.DataFrame(
        [{"year": y, "state": s, "state_abbr": a}
         for y in all_years for s, a in STATE_ABBR.items()]
    )
    df = grid.merge(df.drop(columns=["state_abbr"]), on=["year", "state"], how="left")
    df["sport"] = df["sport"].fillna("No data")
    df["athlete_display"] = df["athlete"].apply(fmt_name)
    df["article_count"] = df["article_count"].fillna(0).astype(int)
    return df


def make_choropleth(df_year: pd.DataFrame) -> go.Choropleth:
    sport_idx = [
        SPORT_ORDER.index(s) if s in SPORT_ORDER else SPORT_ORDER.index("Other")
        for s in df_year["sport"]
    ]
    hover = [
        (f"<b style='font-size:14px'>{row.athlete_display}</b><br>"
         f"<span style='color:#aaa'>{row.sport} &nbsp;·&nbsp; {int(row.article_count)} articles</span>")
        if row.sport != "No data"
        else "<span style='color:#777'>No data this year</span>"
        for row in df_year.itertuples()
    ]
    return go.Choropleth(
        locations=df_year["state_abbr"],
        z=sport_idx,
        locationmode="USA-states",
        text=hover,
        hovertemplate="<b>%{location}</b><br>%{text}<extra></extra>",
        colorscale=[[i / (len(SPORT_ORDER) - 1), color]
                    for i, color in enumerate(SPORT_COLORS.values())],
        zmin=0,
        zmax=len(SPORT_ORDER) - 1,
        showscale=False,
        marker_line_color="#0f1117",
        marker_line_width=1.2,
    )


def build_figure(df: pd.DataFrame) -> go.Figure:
    years = sorted(df["year"].unique())
    fig = go.Figure(make_choropleth(df[df["year"] == years[0]]))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            scope="usa",
            bgcolor="rgba(0,0,0,0)",
            lakecolor="#161b24",
            landcolor="#1e2530",
            showlakes=True,
            showframe=False,
            showcoastlines=False,
        ),
        margin=dict(l=0, r=0, t=10, b=10),
        height=520,
        font=dict(family="Inter, sans-serif", color="#9aabb8"),
        sliders=[dict(
            active=0,
            bgcolor="#1e2530",
            bordercolor="#2a3545",
            tickcolor="#445060",
            font=dict(color="#9aabb8", size=12),
            currentvalue=dict(
                prefix="Year: ",
                font=dict(size=15, color="#d0dde8"),
                xanchor="center",
            ),
            pad=dict(t=8, b=8, l=60, r=60),
            steps=[
                dict(
                    method="animate",
                    label=f"{y}*" if y == 2026 else str(y),
                    args=[[str(y)], dict(mode="immediate",
                                        frame=dict(duration=600, redraw=True))],
                )
                for y in years
            ],
        )],
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            bgcolor="#1e2530",
            bordercolor="#2a3545",
            font=dict(color="#d0dde8", size=13),
            x=0.02, y=0.02,
            xanchor="left",
            yanchor="bottom",
            buttons=[
                dict(label="▶  Play",
                     method="animate",
                     args=[None, dict(frame=dict(duration=800, redraw=True),
                                     fromcurrent=True)]),
                dict(label="⏸  Pause",
                     method="animate",
                     args=[[None], dict(frame=dict(duration=0), mode="immediate")]),
            ],
        )],
    )

    fig.frames = [
        go.Frame(data=[make_choropleth(df[df["year"] == y])], name=str(y))
        for y in years
    ]
    return fig


def build_legend_html() -> str:
    items = []
    for sport, color in SPORT_COLORS.items():
        if sport == "No data":
            continue
        items.append(
            f'<div class="legend-item">'
            f'<div class="legend-swatch" style="background:{color}"></div>'
            f'{sport}</div>'
        )
    return "\n      ".join(items)


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)

    print("Loading rankings...", flush=True)
    df = load_data()
    filled = (df["sport"] != "No data").sum()
    print(f"  {filled:,} state-year slots with data across {df['year'].nunique()} years "
          f"({df['year'].min()}–{df['year'].max()})")

    print("Building figure...", flush=True)
    fig = build_figure(df)

    # Export Plotly as a div + inline script (no full HTML wrapper)
    full_html = fig.to_html(include_plotlyjs=False, full_html=False, div_id="map")
    # Split at the closing </div> to separate the div from the script
    div_end = full_html.index("</div>") + 6
    plotly_div = full_html[:div_end]
    plotly_script = full_html[div_end:]

    page = HTML_TEMPLATE.format(
        legend_items=build_legend_html(),
        plotly_div=plotly_div,
        plotly_script=plotly_script,
    )

    out_path = DOCS_DIR / "index.html"
    out_path.write_text(page, encoding="utf-8")
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
