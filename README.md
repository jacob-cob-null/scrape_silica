# Pax Silica Discourse Intelligence Pipeline

[![Data Architecture: Medallion](https://img.shields.io/badge/Architecture-Medallion%20(Bronze%20%E2%86%92%20Silver%20%E2%86%92%20Gold)-blue.svg)](#architecture)
[![Database: DuckDB](https://img.shields.io/badge/Storage-DuckDB%20%2B%20Snappy%20Parquet-orange.svg)](#silver-layer)
[![NLP: Laya NLI](https://img.shields.io/badge/NLP-Zero--Shot%20Cross--Encoder%20(CUDA)-green.svg)](#ai-semantic-filtering)
[![Scale: 100K+](https://img.shields.io/badge/Corpus-107K%2B%20Records-purple.svg)](#dataset-metrics)

An end-to-end, production-grade Medallion ELT and NLP pipeline designed to capture, clean, deduplicate, and semantically score public netizen discourse regarding the U.S.-led **"Pax Silica"** semiconductor and AI infrastructure initiative in the Philippines.

---

## Architecture Flow

```mermaid
flowchart TD
    subgraph Bronze["Bronze Layer (Raw Ingestion)"]
        direction TB
        E1["YouTube (Data API v3 + Transcripts)"]
        E2["Reddit (Headless Playwright Posts & Comments)"]
        E3["TikTok (Zeeschuimer NDJSON Exports)"]
        E4["Bluesky (AT Protocol API)"]
        E5["Mastodon, HackerNews, GDELT & RSS"]
        
        E1 --> B1[("data/bronze/automated/*.json")]
        E2 --> B2[("data/bronze/drop_folder/*.ndjson")]
        E3 --> B3[("data/bronze/zeeschuimer/*.ndjson")]
        E4 --> B1
        E5 --> B1
    end

    subgraph Silver["Silver Layer (Cleaning & Staging)"]
        direction TB
        C1["Cleaner (Regex, Whitespace, PII strip)"]
        D1["SHA-256 Deterministic Content Hasher"]
        DB[("DuckDB: pax_silica_staging.duckdb<br/>(ON CONFLICT DO NOTHING)")]
        
        B1 & B2 & B3 --> C1 --> D1 --> DB
    end

    subgraph AI["AI Semantic Filtering (GPU Inference)"]
        direction TB
        CRIT["Criteria Schema (eval/criteria.json)<br/>Anchor Entailment (noul)"]
        LAYA["LAYA Zero-Shot Cross-Encoder<br/>(NVIDIA RTX 3060 CUDA, Batch=32)"]
        UPD["Vectorized Batch Update<br/>(decision_rating & confidence)"]
        
        DB --> LAYA
        CRIT --> LAYA
        LAYA --> UPD --> DB
    end

    subgraph Gold["Gold Layer (Analytics-Ready Corpus)"]
        direction TB
        EXP["Exporter (Schema Enforcement)"]
        G_PQ[("data/gold/pax_silica_corpus.parquet<br/>(Snappy Compressed)")]
        G_CSV[("data/gold/pax_silica_corpus.csv<br/>(UTF-8 Quoted)")]
        
        DB --> EXP --> G_PQ & G_CSV
    end

    classDef bronze fill:#f9d5e5,stroke:#333,stroke-width:1px;
    classDef silver fill:#eeeeee,stroke:#333,stroke-width:1px;
    classDef ai fill:#d5e8d4,stroke:#274e13,stroke-width:1px;
    classDef gold fill:#fff2cc,stroke:#b45f06,stroke-width:1px;

    class E1,E2,E3,E4,E5,B1,B2,B3 bronze;
    class C1,D1,DB silver;
    class CRIT,LAYA,UPD ai;
    class EXP,G_PQ,G_CSV gold;
```

---

## Evaluation & Ground-Truth Methodology

To ensure high data quality across multilingual social text (English, Tagalog, and Taglish code-switching), the pipeline incorporates a rigorous evaluation benchmark.

```mermaid
sequenceDiagram
    autonumber
    participant Sample as 400-Row Stratified Sample
    participant GroundTruth as Human / LLM Audited Labels (eval/laya_sample.csv)
    participant Model as LAYA Cross-Encoder (noul)
    participant Evaluator as score_eval.py Engine
    
    Sample->>GroundTruth: Curate ground truth (none, weak, direct, core)
    GroundTruth->>GroundTruth: Audit review queue (needs_review_outcomes.csv)
    Sample->>Model: GPU Batch Inference (Hypothesis Entailment)
    Model->>Evaluator: Emit P(true) Closeness Percentage (0-100%)
    Evaluator->>Evaluator: Compute Precision, Recall, F1 & ECE across thresholds
    Note over Evaluator: Achieves 92.4% Recall on direct/core anchors at t=50
```

### Evaluation Benchmark Highlights:
- **Ground Truth Corpus**: 386 labeled rows across YouTube, Reddit, and TikTok.
- **Anchor Recall**: **95% (40/42 anchors)** validated against the human audit queue.
- **Model Formulation**: Uses binary hypothesis entailment (`noul`) rather than multi-class categorical splitting, preventing probability dilution across Taglish comments.
- **Performance**:
  - **Threshold 50**: **92.4% Recall** (captures nearly all relevant discourse).
  - **Threshold 75**: **0.532 F1** (balanced operating point for high-precision analytical slices).

---

## Data Layers (Medallion Standard)

| Layer | Storage Engine | Path | Purpose |
| :--- | :--- | :--- | :--- |
| **Bronze** | Raw JSON / NDJSON | `data/bronze/` | Immutable, verbatim raw payloads from APIs and web scrapers. |
| **Silver** | In-Process OLAP (DuckDB) | `data/silver/pax_silica_staging.duckdb` | Standardized text, SHA-256 deduplicated, with `decision_rating` and `confidence` fields. |
| **Gold** | Columnar Parquet & CSV | `data/gold/pax_silica_corpus.*` | Strongly-typed 4-column analytical export ready for Data Science & NLP. |

### Gold Schema:
* **`platform`** (`VARCHAR`): Originating platform (`reddit`, `youtube_comment`, `tiktok`, `bluesky`, etc.).
* **`decision_rating`** (`INT64`): Continuous **0%–100% closeness percentage** to the Pax Silica anchor.
* **`confidence`** (`INT64`): Model calibration confidence score (0%–100%).
* **`content`** (`VARCHAR`): Cleaned, normalized social media post or comment text.

---

## Hardware Acceleration (GPU Batching)

The semantic filtering phase is powered by native GPU batch execution on PyTorch + CUDA:

* **Hardware**: Tested on **NVIDIA GeForce RTX 3060 (12 GB VRAM)**.
* **Memory Footprint**: ~1.6 GB VRAM allocated on-demand (no system paging bloat).
* **Throughput**: **~25 to 30 records/second** (`batch_size=32`).
* **Runtime**: ~20 seconds per 500 records; ~55 minutes for 100K+ full corpus passes.

---

## Quickstart

### 1. Environment Setup

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-laya.txt
playwright install chromium
```

Copy `.env.example` to `.env` and fill in API credentials if re-running scrapers.

### 2. Ingest Data (Bronze)

```powershell
# Ingest automated API feeds (YouTube, Bluesky, Mastodon, GDELT, RSS)
$env:PYTHONPATH="."; python main.py ingest --track automated

# Extract Reddit comment threads (Headless Playwright)
$env:PYTHONPATH="."; python -u extractors\playwright_reddit_comments.py
```

### 3. Transform & GPU Score (Silver → Gold)

```powershell
# Run GPU scoring on a test limit of 500 records and export Gold
$env:USE_TF="0"; $env:PYTHONPATH="."; python -c "from transforms import ai_filter, exporter; ai_filter.run(limit=500); exporter.export_gold()"

# Or run the full production pass across all unrated records
$env:USE_TF="0"; $env:PYTHONPATH="."; python -c "from transforms import ai_filter, exporter; ai_filter.run(); exporter.export_gold()"
```

### 4. Evaluate Benchmark Metrics

```powershell
# Check precision/recall/F1 sweep and ECE calibration against ground truth
$env:USE_TF="0"; $env:PYTHONPATH="."; python scripts\score_eval.py --metrics-only
```

---

## Sources & Extractors

| Extractor | Platform | Extraction Protocol |
| :--- | :--- | :--- |
| `api_youtube.py` | YouTube | Official YouTube Data API v3 |
| `api_youtube_transcripts.py` | YouTube Transcripts | `youtube-transcript-api` (Speech-to-text extraction) |
| `playwright_reddit.py` | Reddit Posts | Playwright headless browser DOM scraping |
| `playwright_reddit_comments.py` | Reddit Comments | Recursive depth-0 and depth-1 comment tree parser |
| `parser_zeeschuimer.py` | TikTok | Zeeschuimer browser extension NDJSON parser |
| `api_bluesky.py` | Bluesky | AT Protocol API |
| `api_mastodon.py` | Mastodon | Decentralized Mastodon REST API |
| `api_hacker_news.py` | Hacker News | Algolia HN Search API |
| `api_gdelt.py` | Global News | GDELT 2.0 Global Knowledge Graph API |
| `api_rss.py` | News / Blogs | `feedparser` syndicated feeds |
| `scraper_forums.py` | Specialized Forums | `requests` + `BeautifulSoup` HTML extraction |
