# Most Popular Athlete Per State

Analyses New York Times coverage from 2000 to 2026 to find the most distinctively covered athlete per US state per year.

## Methodology

1. **Data collection** — Uses the [NYT Archive API](https://developer.nytimes.com/docs/archive-product/1/overview), which returns every article published in a given month, including the keyword tags the NYT assigns each article (`persons`, `glocations`, `subject`).
2. **State bucketing** — Articles are mapped to US states via the `glocations` keyword tags.
3. **Athlete identification** — Athletes are identified via the `persons` keyword tags, filtered by the `Sports` subject tag where present.
4. **Ranking** — For each state/year combination, athletes are ranked by article count to find the most covered.

## Project Structure

```
├── src/              # Source code
├── data/
│   ├── raw/          # Raw API responses (gitignored — not for redistribution)
│   └── processed/    # Cleaned/transformed data (gitignored)
├── results/          # Final output tables and charts
├── .env.example      # Required environment variables (copy to .env)
└── requirements.txt
```

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and add your NYT API key:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env`:
   ```
   NYT_API_KEY=your_key_here
   ```
   Get a key at https://developer.nytimes.com/

## Data

Raw data is not committed to this repository. The `data/` directory will reach several GB and contains NYT article data that must not be redistributed per NYT Terms of Service.
