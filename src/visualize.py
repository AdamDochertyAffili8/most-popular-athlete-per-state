"""
Generate the full site: docs/index.html + docs/methodology.html

Usage (run from project root):
    python -m src.visualize
"""

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

RESULTS_DIR = Path("results")
DOCS_DIR    = Path("docs")

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
    "Football":      "#3a7bd5",
    "Basketball":    "#f07d18",
    "Baseball":      "#d42b2b",
    "Hockey":        "#18b8d4",
    "Soccer":        "#22a84e",
    "Tennis":        "#c8d41a",
    "Golf":          "#8a3dd4",
    "Boxing/MMA":    "#d41a8a",
    "Olympics":      "#d49a1a",
    "Auto Racing":   "#8a9db8",
    "Horse Racing":  "#956030",
    "Track & Field": "#1ad4aa",
    "Other":         "#5a6a80",
    "No data":       "#252d3a",
}

SPORT_ORDER = list(SPORT_COLORS.keys())


def fmt_name(name: str) -> str:
    if pd.isna(name):
        return ""
    parts = str(name).split(",", 1)
    return f"{parts[1].strip()} {parts[0].strip()}" if len(parts) == 2 else str(name)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    top = pd.read_csv(RESULTS_DIR / "top_per_state.csv")
    top = top[top["rank"] == 1].copy()
    top = top.sort_values(["year", "state", "article_count", "athlete"],
                          ascending=[True, True, False, True])
    top = top.drop_duplicates(subset=["year", "state"], keep="first")
    top["state_abbr"] = top["state"].map(STATE_ABBR)
    top = top.dropna(subset=["state_abbr"])

    all_years = sorted(top["year"].unique())
    grid = pd.DataFrame(
        [{"year": y, "state": s, "state_abbr": a}
         for y in all_years for s, a in STATE_ABBR.items()]
    )
    df = grid.merge(top.drop(columns=["state_abbr"]), on=["year", "state"], how="left")
    df["sport"] = df["sport"].fillna("No data")
    df["athlete_display"] = df["athlete"].apply(fmt_name)
    df["article_count"] = df["article_count"].fillna(0).astype(int)

    rankings = pd.read_csv(RESULTS_DIR / "rankings.csv")
    return df, rankings


def compute_leaderboard(rankings: pd.DataFrame) -> dict:
    """Top-5 athletes per year by peak article count in any single state."""
    peak = (rankings.groupby(["year", "athlete", "sport"])["article_count"]
            .max().reset_index()
            .sort_values(["year", "article_count"], ascending=[True, False]))
    result = {}
    for year, grp in peak.groupby("year"):
        grp = grp.drop_duplicates(subset=["athlete"], keep="first").head(5)
        result[int(year)] = [
            {"name": fmt_name(r["athlete"]), "sport": r["sport"],
             "articles": int(r["article_count"])}
            for _, r in grp.iterrows()
        ]
    return result


def compute_records(top1: pd.DataFrame) -> list[dict]:
    """Four all-time records computed from the rank-1 dataset."""
    records = []

    # 1. Most dominant single-season performance
    idx = top1["article_count"].idxmax()
    r = top1.loc[idx]
    records.append({
        "icon": "🏆",
        "label": "Most dominant single season",
        "value": f"{int(r['article_count'])} articles",
        "detail": f"{fmt_name(r['athlete'])} · {r['state']} · {int(r['year'])}"
    })

    # 2. Most unique states topped (career)
    career = top1.groupby("athlete")["state"].nunique().sort_values(ascending=False)
    records.append({
        "icon": "🗺️",
        "label": "Most states topped (career)",
        "value": f"{int(career.iloc[0])} states",
        "detail": fmt_name(career.index[0])
    })

    # 3. Longest consecutive years topping one state
    best_streak, best_athlete, best_state = 0, "", ""
    for (athlete, state), grp in top1.groupby(["athlete", "state"]):
        yrs = sorted(grp["year"].tolist())
        streak = cur = 1
        for i in range(1, len(yrs)):
            cur = cur + 1 if yrs[i] == yrs[i - 1] + 1 else 1
            streak = max(streak, cur)
        if streak > best_streak:
            best_streak, best_athlete, best_state = streak, athlete, state
    records.append({
        "icon": "🔥",
        "label": "Longest consecutive reign",
        "value": f"{best_streak} years in a row",
        "detail": f"{fmt_name(best_athlete)} · {best_state}"
    })

    # 4. Most total years topping one state (not necessarily consecutive)
    pair_years = top1.groupby(["athlete", "state"])["year"].count().sort_values(ascending=False)
    best = pair_years.index[0]
    records.append({
        "icon": "⏱️",
        "label": "Most years topping one state",
        "value": f"{int(pair_years.iloc[0])} years",
        "detail": f"{fmt_name(best[0])} · {best[1]}"
    })

    return records


def make_choropleth(df_year: pd.DataFrame) -> go.Choropleth:
    sport_idx = [
        SPORT_ORDER.index(s) if s in SPORT_ORDER else SPORT_ORDER.index("Other")
        for s in df_year["sport"]
    ]
    hover = [
        (f"<b style='font-size:14px'>{row.athlete_display}</b><br>"
         f"<span style='color:#aaa'>{row.sport} &nbsp;·&nbsp; {int(row.article_count)} articles</span>")
        if row.sport != "No data" else "<span style='color:#555'>No data this year</span>"
        for row in df_year.itertuples()
    ]
    return go.Choropleth(
        locations=df_year["state_abbr"],
        z=sport_idx,
        locationmode="USA-states",
        text=hover,
        hovertemplate="<b>%{location}</b><br>%{text}<extra></extra>",
        colorscale=[[i / (len(SPORT_ORDER) - 1), c] for i, c in enumerate(SPORT_COLORS.values())],
        zmin=0, zmax=len(SPORT_ORDER) - 1,
        showscale=False,
        marker_line_color="#0f1117",
        marker_line_width=1.2,
    )


def build_figure(df: pd.DataFrame) -> go.Figure:
    years = sorted(df["year"].unique())
    fig = go.Figure(make_choropleth(df[df["year"] == years[0]]))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        geo=dict(scope="usa", bgcolor="rgba(0,0,0,0)", lakecolor="#161b24",
                 landcolor="#1e2530", showlakes=True, showframe=False, showcoastlines=False),
        margin=dict(l=0, r=0, t=10, b=10),
        height=480,
        font=dict(family="Inter, sans-serif", color="#9aabb8"),
        sliders=[dict(
            active=0, bgcolor="#1e2530", bordercolor="#2a3545", tickcolor="#445060",
            font=dict(color="#9aabb8", size=11),
            currentvalue=dict(prefix="Year: ", font=dict(size=14, color="#d0dde8"), xanchor="center"),
            pad=dict(t=8, b=8, l=50, r=50),
            steps=[dict(
                method="animate",
                label=f"{y}*" if y == 2026 else str(y),
                args=[[str(y)], dict(mode="immediate", frame=dict(duration=600, redraw=True))],
            ) for y in years],
        )],
        updatemenus=[dict(
            type="buttons", showactive=False, bgcolor="#1e2530", bordercolor="#2a3545",
            font=dict(color="#d0dde8", size=12),
            x=0.02, y=0.02, xanchor="left", yanchor="bottom",
            buttons=[
                dict(label="▶  Play",  method="animate",
                     args=[None, dict(frame=dict(duration=800, redraw=True), fromcurrent=True)]),
                dict(label="⏸  Pause", method="animate",
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
    return "\n".join(
        f'<div class="legend-item"><div class="swatch" style="background:{c}"></div>{s}</div>'
        for s, c in SPORT_COLORS.items() if s != "No data"
    )


def build_records_html(records: list[dict]) -> str:
    cards = []
    for r in records:
        cards.append(
            f'<div class="record-card">'
            f'<div class="record-icon">{r["icon"]}</div>'
            f'<div class="record-label">{r["label"]}</div>'
            f'<div class="record-value">{r["value"]}</div>'
            f'<div class="record-detail">{r["detail"]}</div>'
            f'</div>'
        )
    return "\n".join(cards)


INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Most-Covered Athlete per US State — NYT 2000–2026</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"/>
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Inter',sans-serif;background:#0f1117;color:#e8e8e8;min-height:100vh}

    /* ── Header ── */
    header{max-width:1200px;margin:0 auto;padding:44px 20px 24px}
    nav{display:flex;justify-content:flex-end;margin-bottom:20px}
    nav a{font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
          color:#5a7a9a;text-decoration:none;border-bottom:1px solid #2a3a4a;padding-bottom:2px}
    nav a:hover{color:#9aabb8}
    .kicker{font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;
             color:#5a6a7a;margin-bottom:12px}
    h1{font-family:'Playfair Display',Georgia,serif;font-size:clamp(24px,4vw,40px);
       font-weight:700;line-height:1.15;color:#f0f0f0;margin-bottom:14px}
    .subtitle{font-size:14px;line-height:1.7;color:#8a9ba8;max-width:620px}

    /* ── Main grid: map + sidebar ── */
    .main-grid{
      max-width:1200px;margin:0 auto;padding:0 20px;
      display:grid;grid-template-columns:1fr 280px;gap:20px;align-items:start
    }
    @media(max-width:900px){.main-grid{grid-template-columns:1fr}}

    /* ── Map card ── */
    .map-card{background:#161b24;border-radius:12px;overflow:hidden}
    .legend{display:flex;flex-wrap:wrap;gap:8px 16px;padding:14px 16px 4px}
    .legend-item{display:flex;align-items:center;gap:6px;font-size:11px;color:#8a9ba8;font-weight:500}
    .swatch{width:10px;height:10px;border-radius:2px;flex-shrink:0}

    /* ── Sidebar ── */
    .sidebar{background:#161b24;border-radius:12px;padding:20px;position:sticky;top:20px}
    @media(max-width:900px){.sidebar{position:static}}
    .sidebar-header{display:flex;align-items:baseline;justify-content:space-between;
                    margin-bottom:16px;border-bottom:1px solid #1e2a38;padding-bottom:12px}
    .sidebar-title{font-family:'Playfair Display',serif;font-size:16px;color:#d0dde8}
    .sidebar-year{font-size:28px;font-weight:700;font-family:'Playfair Display',serif;
                  color:#3a7bd5;line-height:1}
    .lb-item{display:grid;grid-template-columns:28px 1fr auto;align-items:center;
             gap:8px;padding:10px 0;border-bottom:1px solid #1a2330}
    .lb-item:last-child{border-bottom:none}
    .lb-rank{font-size:11px;font-weight:700;color:#445060;text-align:center;
             background:#1a2330;border-radius:4px;width:22px;height:22px;
             display:flex;align-items:center;justify-content:center}
    .lb-name{font-size:13px;font-weight:600;color:#d0dde8;line-height:1.3}
    .lb-sport{font-size:11px;color:#5a7a8a;margin-top:2px}
    .lb-count{font-size:13px;font-weight:600;color:#3a7bd5;white-space:nowrap;
              text-align:right;font-variant-numeric:tabular-nums}
    .lb-count span{font-size:10px;font-weight:400;color:#445060;display:block}
    .sidebar-note{font-size:10px;color:#3a4a5a;margin-top:12px;line-height:1.5}

    /* ── Records bar ── */
    .records-section{max-width:1200px;margin:28px auto 0;padding:0 20px}
    .records-title{font-family:'Playfair Display',serif;font-size:20px;color:#c8d4e0;
                   margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid #1e2a38}
    .records-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
    @media(max-width:900px){.records-grid{grid-template-columns:repeat(2,1fr)}}
    @media(max-width:480px){.records-grid{grid-template-columns:1fr}}
    .record-card{background:#161b24;border-radius:10px;padding:18px;
                 border:1px solid #1e2a38}
    .record-icon{font-size:22px;margin-bottom:10px}
    .record-label{font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
                  color:#445060;margin-bottom:8px}
    .record-value{font-size:20px;font-weight:700;font-family:'Playfair Display',serif;
                  color:#d0dde8;margin-bottom:6px;line-height:1.2}
    .record-detail{font-size:12px;color:#5a7a8a;line-height:1.5}

    /* ── Footer ── */
    footer{max-width:1200px;margin:28px auto 0;padding:20px 20px 40px;
           border-top:1px solid #1a2330}
    .footnote{font-size:11px;color:#3a4a5a;line-height:1.7;max-width:700px}
    .footnote strong{color:#5a6a7a}
    .source{margin-top:8px;font-size:10px;color:#2a3a48}
    .source a{color:#3a5a7a;text-decoration:none}
    .source a:hover{color:#5a8aaa}
  </style>
</head>
<body>

<header>
  <nav><a href="methodology.html">Methodology &amp; data</a></nav>
  <p class="kicker">Data Journalism · NYT Archive Analysis</p>
  <h1>The Most-Covered Athlete in Every US State</h1>
  <p class="subtitle">
    Using the New York Times Archive API, we identified the athlete mentioned most
    in NYT sports articles linked to each state — by year, from 2000 to 2026.
  </p>
</header>

<div class="main-grid">
  <div class="map-card">
    <div class="legend">LEGEND_HTML</div>
    PLOTLY_DIV
  </div>

  <aside class="sidebar">
    <div class="sidebar-header">
      <h2 class="sidebar-title">National top 5</h2>
      <div class="sidebar-year" id="sb-year">2000</div>
    </div>
    <div id="leaderboard"></div>
    <p class="sidebar-note">Ranked by article count in their strongest state that year.</p>
  </aside>
</div>

<section class="records-section">
  <h2 class="records-title">All-time records</h2>
  <div class="records-grid">
    RECORDS_HTML
  </div>
</section>

<footer>
  <p class="footnote">
    <strong>Grey states</strong> had no athlete mentioned in 2+ NYT sports articles
    linked to that state in a given year — this reflects The Times' coverage patterns,
    not the absence of sport. State attribution uses NYT geographic tags plus a lookup
    of 200+ pro and college team names.
    <strong>2026*</strong> covers January–May only.
  </p>
  <p class="source">
    Data: <a href="https://developer.nytimes.com/docs/archive-product/1/overview" target="_blank">NYT Archive API</a>
    &nbsp;·&nbsp; 2,326,409 articles &nbsp;·&nbsp; 2000–May 2026
    &nbsp;·&nbsp; <a href="methodology.html">Full methodology</a>
  </p>
</footer>

<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
PLOTLY_SCRIPT

<script>
(function () {
  var data = LEADERBOARD_JSON;
  var sportColors = SPORT_COLORS_JSON;

  function render(year) {
    document.getElementById('sb-year').textContent = year === 2026 ? '2026*' : year;
    var items = data[year] || [];
    var html = items.map(function (item, i) {
      var color = sportColors[item.sport] || '#5a6a80';
      return '<div class="lb-item">' +
        '<div class="lb-rank">' + (i + 1) + '</div>' +
        '<div><div class="lb-name">' + item.name + '</div>' +
        '<div class="lb-sport" style="color:' + color + '">' + item.sport + '</div></div>' +
        '<div class="lb-count">' + item.articles + '<span>articles</span></div>' +
        '</div>';
    }).join('');
    document.getElementById('leaderboard').innerHTML = html || '<p style="color:#3a4a5a;font-size:12px;padding:8px 0">No data</p>';
  }

  var firstYear = FIRST_YEAR;
  render(firstYear);

  var mapDiv = document.getElementById('map');
  if (mapDiv) {
    mapDiv.on('plotly_sliderchange', function (e) {
      render(parseInt(e.step.label));
    });
    mapDiv.on('plotly_animatingframe', function (e) {
      var y = parseInt(e.name);
      if (!isNaN(y)) render(y);
    });
  }
})();
</script>

</body>
</html>"""


METHODOLOGY_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Methodology — Most-Covered Athlete per US State</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"/>
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Inter',sans-serif;background:#0f1117;color:#c8d4e0;
         min-height:100vh;line-height:1.7}
    .wrap{max-width:720px;margin:0 auto;padding:40px 20px 80px}
    nav{margin-bottom:32px}
    nav a{font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
          color:#5a7a9a;text-decoration:none;border-bottom:1px solid #2a3a4a;padding-bottom:2px}
    nav a:hover{color:#9aabb8}
    h1{font-family:'Playfair Display',serif;font-size:clamp(26px,4vw,38px);
       color:#f0f0f0;margin-bottom:8px;line-height:1.15}
    .subtitle{font-size:14px;color:#5a7a8a;margin-bottom:48px}
    h2{font-family:'Playfair Display',serif;font-size:22px;color:#d0dde8;
       margin:40px 0 14px;padding-bottom:8px;border-bottom:1px solid #1e2a38}
    p{font-size:14px;color:#8a9ba8;margin-bottom:14px}
    ul{font-size:14px;color:#8a9ba8;padding-left:20px;margin-bottom:14px}
    li{margin-bottom:6px}
    code{font-family:'Courier New',monospace;font-size:12px;background:#161b24;
         color:#5ab4d4;padding:2px 6px;border-radius:3px}
    .stat-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0}
    @media(max-width:500px){.stat-row{grid-template-columns:1fr}}
    .stat{background:#161b24;border-radius:8px;padding:16px;text-align:center;
          border:1px solid #1e2a38}
    .stat-val{font-size:22px;font-weight:700;font-family:'Playfair Display',serif;
              color:#d0dde8;margin-bottom:4px}
    .stat-lbl{font-size:11px;color:#445060;text-transform:uppercase;letter-spacing:.06em}
    .limit{background:#161b24;border-left:3px solid #3a5a7a;padding:14px 16px;
           border-radius:0 8px 8px 0;margin:20px 0;font-size:13px;color:#7a9aaa}
    footer{margin-top:48px;padding-top:20px;border-top:1px solid #1a2330;
           font-size:11px;color:#2a3a48}
    footer a{color:#3a5a7a;text-decoration:none}
  </style>
</head>
<body>
<div class="wrap">
  <nav><a href="index.html">← Back to map</a></nav>

  <h1>Methodology</h1>
  <p class="subtitle">How we identified the most-covered athlete in every US state, every year.</p>

  <h2>Data source</h2>
  <p>
    All data comes from the
    <a href="https://developer.nytimes.com/docs/archive-product/1/overview" style="color:#5ab4d4">
    NYT Archive API</a>, which returns every article The New York Times published in a given month,
    along with structured keyword metadata the NYT assigns to each piece. We downloaded every month
    from January 2000 through May 2026 — 317 months in total.
  </p>

  <div class="stat-row">
    <div class="stat"><div class="stat-val">2.3M</div><div class="stat-lbl">Articles downloaded</div></div>
    <div class="stat"><div class="stat-val">317</div><div class="stat-lbl">Months covered</div></div>
    <div class="stat"><div class="stat-val">27</div><div class="stat-lbl">Years (2000–2026)</div></div>
  </div>

  <h2>Identifying sports articles</h2>
  <p>
    Each article carries a list of <code>subject</code> keyword tags. We flag an article as
    sports-related if any of its subject tags matches a curated list of ~50 sport categories,
    including <em>Football</em>, <em>Basketball</em>, <em>Baseball</em>, <em>Olympics</em>,
    <em>Mixed Martial Arts</em>, and so on. This produced approximately 136,000 sports articles
    (~5.9% of the corpus).
  </p>

  <h2>Attributing articles to US states</h2>
  <p>We use two complementary signals to link a sports article to a state:</p>
  <ul>
    <li>
      <strong>Geographic tags</strong> — The NYT attaches <code>glocations</code> tags such as
      <em>New York (State)</em>, <em>Los Angeles (Calif)</em>, or <em>Chicago (Ill)</em>.
      We parse these using a lookup that handles parenthetical state abbreviations, full state names,
      and ~150 major US cities.
    </li>
    <li>
      <strong>Team names</strong> — Many sports articles tag the team as an <code>organizations</code>
      keyword (e.g. <em>New York Yankees</em>, <em>Los Angeles Lakers</em>,
      <em>Alabama Crimson Tide</em>) without including an explicit location tag.
      We map 200+ professional and college team names to their home state.
    </li>
  </ul>
  <p>
    Both signals are combined and deduplicated — if an article carries both a Yankees
    organisation tag and a New York glocation, it counts once for New York.
  </p>

  <h2>Identifying athletes</h2>
  <p>
    NYT articles include a <code>persons</code> keyword list naming the key individuals covered.
    We extract every person from every sports article and cross-reference with the state list above
    to produce (article, person, state, year) tuples.
  </p>
  <p>
    To remove noise, we apply a blocklist of people who regularly appear in sports articles
    without being athletes: journalists (including several NYT sports writers who get tagged in
    their own articles), politicians, team owners, league commissioners, coaches, and individuals
    primarily known for involvement in crime cases.
  </p>

  <h2>Ranking</h2>
  <p>
    For each (state, year) pair we count the number of unique articles in which each person
    appears. The person with the highest count is named the most-covered athlete for that
    state-year. We require a minimum of two articles to qualify, which filters out single
    incidental mentions.
  </p>
  <p>
    Where two athletes tie on article count, the map shows the one whose name comes first
    alphabetically — this is an arbitrary tiebreak and both athletes are equally prominent.
  </p>

  <h2>Sport classification</h2>
  <p>
    The colour on the map reflects the sport associated with that athlete's coverage. We
    determine this by finding the most-mentioned sports subject tag across all the articles that
    link that athlete to that state in that year.
  </p>

  <h2>Limitations</h2>
  <div class="limit">
    <strong>Grey states</strong> had no athlete meeting the 2-article threshold in a given year.
    This is a genuine gap in NYT coverage — a national newspaper disproportionately covers
    athletes from large-market states.
  </div>
  <div class="limit">
    <strong>State attribution is imperfect.</strong> An article about the NFL Draft in New York
    might be tagged with all 32 team names, linking it to 30+ states simultaneously. Some
    coverage spills across state lines because of how the NYT applies tags.
  </div>
  <div class="limit">
    <strong>Non-athletes may still appear.</strong> The blocklist covers the most common cases
    but is not exhaustive. Coaches, sports agents, and crime-adjacent figures occasionally
    surface — the blocklist is an open-ended set that can be extended.
  </div>
  <div class="limit">
    <strong>2026 is a partial year</strong> (January–May only). The NYT Archive API does not
    include the current in-progress month.
  </div>

  <h2>Download the data</h2>
  <p>
    The full rankings dataset is available as a CSV:
    <a href="https://github.com/AdamDochertyAffili8/most-popular-athlete-per-state/blob/main/results/top_per_state.csv"
       style="color:#5ab4d4" target="_blank">top_per_state.csv</a> —
    one row per state per year with athlete name, article count, rank, and sport category.
  </p>

  <footer>
    <a href="index.html">← Back to map</a> &nbsp;·&nbsp;
    Data: NYT Archive API &nbsp;·&nbsp; 2000–May 2026
  </footer>
</div>
</body>
</html>"""


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)

    print("Loading data...", flush=True)
    df, rankings = load_data()
    filled = (df["sport"] != "No data").sum()
    print(f"  {filled:,} state-year slots with data across {df['year'].nunique()} years")

    print("Computing leaderboard + records...", flush=True)
    leaderboard = compute_leaderboard(rankings)
    top1 = df[(df["sport"] != "No data")].copy()
    records = compute_records(top1)

    print("Building map figure...", flush=True)
    fig = build_figure(df)

    full_html = fig.to_html(include_plotlyjs=False, full_html=False, div_id="map")
    div_end = full_html.index("</div>") + 6
    plotly_div    = full_html[:div_end]
    plotly_script = full_html[div_end:]

    first_year = min(leaderboard.keys())

    page = INDEX_TEMPLATE
    page = page.replace("LEGEND_HTML",        build_legend_html())
    page = page.replace("PLOTLY_DIV",         plotly_div)
    page = page.replace("PLOTLY_SCRIPT",      plotly_script)
    page = page.replace("RECORDS_HTML",       build_records_html(records))
    page = page.replace("LEADERBOARD_JSON",   json.dumps(leaderboard))
    page = page.replace("SPORT_COLORS_JSON",  json.dumps(SPORT_COLORS))
    page = page.replace("FIRST_YEAR",         str(first_year))

    (DOCS_DIR / "index.html").write_text(page, encoding="utf-8")
    print(f"Saved -> docs/index.html")

    (DOCS_DIR / "methodology.html").write_text(METHODOLOGY_TEMPLATE, encoding="utf-8")
    print(f"Saved -> docs/methodology.html")


if __name__ == "__main__":
    main()
