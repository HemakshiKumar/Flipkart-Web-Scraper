# Recommendation service

FastAPI wrapper around the repository's scraping, preprocessing and TF-IDF
recommendation logic. See the root `README.md` for the project overview.

## Layout

```
app/
  config.py             settings + the notebook's Flipkart selectors
  logging_config.py     one line per stage, request id on every line
  models.py             request/response schemas (the only public shapes)
  main.py               FastAPI app, error mapping
  services/
    scraper.py          the notebook's scraping cells
    extractors.py       structural fallback when a selector stops matching
    preprocessing.py    the notebook's cleaning + DESCRIPTION cells
    requirements.py     natural language -> filters / query terms / weights
    recommender.py      TfidfVectorizer + cosine similarity + ranking
    dataset.py          cache -> scrape -> seed dataset
    pipeline.py         orchestration + engine cache
tests/                  57 tests, no network access
```

## Run

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows;  source .venv/bin/activate elsewhere
pip install -r requirements-dev.txt
python run.py                     # or: uvicorn app.main:app --port 8000
pytest
```

## Endpoints

### `GET /api/health`

```json
{ "status": "ok", "scrapingEnabled": true, "seedDatasetAvailable": true, "maxRecommendations": 50 }
```

### `POST /api/recommend`

| Field | Type | Rules |
| --- | --- | --- |
| `query` | string | 2 – `MAX_QUERY_LENGTH` (120) characters, required |
| `requirements` | string | up to `MAX_REQUIREMENTS_LENGTH` (500) characters |
| `limit` | int | 1 – `MAX_RECOMMENDATIONS` (50), default 10 |
| `refresh` | bool | bypass the dataset cache for this search |

Response shape: see the root `README.md`.

## Errors

Failures are returned as `{ "error": <user-facing text>, "code": <machine code> }`.
Selector names, file paths, upstream messages and tracebacks stay in the server log.

| Code | Status | Meaning |
| --- | --- | --- |
| `invalid_request` | 422 | schema validation failed |
| `scraping_failed` | 502 | no dataset could be obtained for the query |
| `internal_error` | 500 | anything else |

## Configuration

Every setting is an environment variable (or a line in `backend/.env`); see
`.env.example`. The ones worth knowing:

| Variable | Default | Purpose |
| --- | --- | --- |
| `FLIPKART_SELECTORS` | – | JSON object merged over the notebook's selectors |
| `STRUCTURAL_FALLBACK` | `true` | allow schema.org extraction for fields a selector missed |
| `SCRAPING_ENABLED` | `true` | set to `false` to serve from cache/seed only |
| `MAX_PRODUCTS_PER_SEARCH` | `20` | product pages fetched per search |
| `SCRAPE_CONCURRENCY` | `4` | higher values get 403s from Flipkart |
| `CACHE_TTL_SECONDS` | `21600` | how long a scraped search stays fresh |
| `SEED_DATASET_FALLBACK` | `true` | rank the repository dataset when scraping fails |
| `WEIGHT_SIMILARITY` / `WEIGHT_RATING` / `WEIGHT_POPULARITY` | `0.70` / `0.20` / `0.10` | ranking blend |

## Debugging a request

Every log line carries the request id that is also returned in the `X-Request-Id`
header, and each stage logs exactly once:

```
[b24ccdad] scrape.search      query='bluetooth headphones' url=…
[b24ccdad] scrape.links       query='bluetooth headphones' found=34
[b24ccdad] scrape.products    query='bluetooth headphones' scraped=20/20
[b24ccdad] preprocess.done    rows_in=20 rows_out=20
[b24ccdad] engine.built       products=20 vocabulary=517
[b24ccdad] engine.recommended query='…' candidates=12 returned=10 top_score=0.541
[b24ccdad] pipeline.done      source=live dataset=20 returned=10 elapsed_ms=8875
```

A missing line tells you which stage failed. `scrape.links … found=0` means the
configured selectors no longer match the search page.

## Replacing the scraper

The pipeline only requires a dataset with the notebook's columns
(`TITLE`, `PRICE`, `AVG RATING`, `DETAILS`, `RETURN POLICY`, `REVIEW COUNT`, `URL`).
Dropping a CSV in that shape into `backend/data/cache/<slug>-<hash>.csv` makes it the
dataset for that query, and any other producer (a headless browser, an official feed)
can be swapped in behind `DatasetService` without touching the frontend.
