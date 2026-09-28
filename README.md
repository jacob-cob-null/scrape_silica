# Pax Silica Discourse Data Pipeline

A Medallion ELT pipeline to capture, clean, and standardize public netizen discourse regarding the U.S.-led "Pax Silica" semiconductor initiative in the Philippines.

## Setup
1. Create a virtual environment: `python -m venv venv`
2. Activate the virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your API keys.

## Usage

### Ingestion (Bronze Layer)
To run automated API extraction:
```bash
python main.py ingest --track automated
```

To parse manual Zeeschuimer drops (make sure to place `.ndjson` files in `data/bronze/drop_folder`):
```bash
python main.py ingest --track drop_folder
```

### Transformation (Silver & Gold Layers)
To clean, deduplicate, and export the data to Parquet and CSV:
```bash
python main.py transform
```
