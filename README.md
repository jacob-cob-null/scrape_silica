# Pax Silica Discourse Data Pipeline

A Medallion ELT pipeline to capture, clean, and standardize public netizen discourse regarding the U.S.-led "Pax Silica" semiconductor initiative in the Philippines.

---

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
playwright install chromium
```

Copy `.env.example` to `.env` and fill in your API keys.

---

## Architecture

```
extractors/   →   data/bronze/   →   transforms/   →   data/gold/
  (raw)              (raw files)       (clean+filter)     (parquet/csv)
```

**Data layers:**
- `data/bronze/automated/` — JSON files from API extractors
- `data/bronze/drop_folder/` — manual drops + Playwright Reddit posts & comments (`.ndjson`)
- `data/bronze/zeeschuimer/` — Zeeschuimer exports (TikTok posts & comments `.ndjson`)
- `data/silver/` — deduplicated DuckDB records (`silver_records`)
- `data/gold/` — final Parquet + CSV exports

---

## Stage 1 — Ingestion (Bronze)

### Automated API Sources + Reddit Posts
Pulls from YouTube, Bluesky, Hacker News, Mastodon, RSS feeds, forums, **and Reddit posts** in one go:

```powershell
$env:PYTHONPATH="."; python main.py ingest --track automated
```

### Reddit — Comment Enrichment (Playwright)
Reads all `reddit_posts_*.ndjson` files, visits each post, extracts depth-0 and depth-1 comments. Run **after** the post scraper:

```powershell
$env:PYTHONPATH="."; python -u extractors\playwright_reddit_comments.py
```

### Manual Drops (Zeeschuimer / Playwright parser)
Place `.ndjson` files in `data/bronze/drop_folder/`, then:

```powershell
$env:PYTHONPATH="."; python main.py ingest --track drop_folder
```

---

## Stage 2 — Transform (Silver → Gold)

Cleans, deduplicates, runs AI semantic filter, and exports to Parquet/CSV:

```powershell
$env:PYTHONPATH="."; python main.py transform
```

---

## Full Daily Run (Recommended Order)

```powershell
# 1. All API sources + Reddit posts
$env:PYTHONPATH="."; python main.py ingest --track automated

# 2. Reddit comments (headless, ~20-30 min for all posts)
$env:PYTHONPATH="."; python -u extractors\playwright_reddit_comments.py

# 3. Parse all drop folder files into bronze
$env:PYTHONPATH="."; python main.py ingest --track drop_folder

# 4. Clean, deduplicate, filter, export
$env:PYTHONPATH="."; python main.py transform
```

---

## Quick Test (Trial Mode)

Run with only 2 keywords to validate the pipeline end-to-end:

```powershell
$env:PYTHONPATH="."; python main.py ingest --track automated --trial
```

---

## Sources

| Extractor | Source | Method |
|---|---|---|
| `api_youtube.py` | YouTube | Data API v3 |
| `api_bluesky.py` | Bluesky | AT Protocol API |
| `api_hacker_news.py` | Hacker News | Algolia API |
| `api_mastodon.py` | Mastodon | REST API |
| `api_rss.py` | RSS/News feeds | feedparser |
| `api_gdelt.py` | GDELT | REST API |
| `api_youtube_transcripts.py` | YouTube transcripts | youtube-transcript-api |
| `scraper_forums.py` | Forums | requests + BeautifulSoup |
| `playwright_reddit.py` | Reddit | Headless browser (DOM) |
| `playwright_reddit_comments.py` | Reddit comments | Headless browser (DOM) |
| `parser_zeeschuimer.py` | TikTok/Instagram + drop folder | Zeeschuimer / NDJSON parser |
