# Flipkart Product Recommendation Engine

A full-stack product discovery app built around the scraping + TF-IDF recommendation
engine originally written in `Web Scraping Project/code file.ipynb`.

Describe a product in plain English, describe what matters to you, and get a ranked
list of real Flipkart products with links back to the store.

```
Next.js frontend  ──POST /api/recommend──▶  Next route handler
                                                  │  (validates, hides the service)
                                                  ▼
                                          FastAPI service (Python)
                                                  │
              requirements parsing → scraping/cache → preprocessing → TF-IDF → ranking
                                                  ▼
                                            ranked products
```

## Repository layout

| Path | What it is |
| --- | --- |
| `Web Scraping Project/` | The original notebook and dataset. Untouched — it remains the source of truth for selectors, cleaning rules and the ranking model. |
| `backend/` | The engine, refactored into a FastAPI service. No logic was reinvented; the notebook's cells map onto modules. |
| `frontend/` | Next.js 16 + TypeScript + Tailwind + shadcn/ui + Framer Motion. |

### Where each notebook cell went

| Notebook | Module |
| --- | --- |
| `find_product_links`, `get_product_*`, the scraping loop | `backend/app/services/scraper.py` |
| Data-cleaning cells (price, return policy, review counts) | `backend/app/services/preprocessing.py` |
| "Preparing data for the TFIDF vectorizer" (`DESCRIPTION`) | `backend/app/services/preprocessing.py` |
| `TfidfVectorizer` + `cosine_similarity` + `recommend_products` | `backend/app/services/recommender.py` |
| Hard-coded URL, headers, CSS classes | `backend/app/config.py` |

## Running it

Two processes: the Python engine and the Next.js app.

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate elsewhere
pip install -r requirements-dev.txt
cp .env.example .env            # optional
python run.py                   # http://127.0.0.1:8000
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local      # points at http://127.0.0.1:8000
npm run dev                     # http://localhost:3000
```

### Checks

```bash
cd backend  && .venv/Scripts/python -m pytest      # 57 tests
cd frontend && npx tsc --noEmit && npx eslint . && npm run build
```

## The pipeline

1. **Requirements parsing** — `services/requirements.py` turns free text into structured
   filters with regular expressions. No LLM is involved and the same sentence always
   produces the same filters.

   | Input | Effect |
   | --- | --- |
   | `>4.5 rating`, `at least 4 star`, `4+ rating` | `AVG RATING >= 4.5` |
   | `under ₹5000`, `below 3k`, `less than 2000` | `PRICE <= 5000` |
   | `between 1000 and 3000` | price range |
   | `high battery life` | query expanded with `playtime playback hours hr charge` |
   | `high rated and cheap` | rating floor 4.0 + price weight in the ranking |
   | `battery life is more important than price` | battery terms weighted up, price weight down |

2. **Dataset acquisition** — `services/dataset.py`: cache → live scrape → cache write.
   A cached search is a CSV in the notebook's own format under `backend/data/cache/`,
   so it can be inspected or hand-edited. Every response reports its `source`
   (`live` / `cache` / `seed`) and the UI shows it.

3. **Preprocessing** — the notebook's cleaning steps, as pure functions.

4. **Ranking** — the notebook's TF-IDF + cosine similarity, blended with the
   rating and review-count strategy the original README describes:

   ```
   score = 0.70 · cosine similarity
         + 0.20 · rating / 5
         + 0.10 · log-scaled review reliability
         (+ price affinity when the user asked for something cheap)
   ```

   Weights live in `backend/app/config.py` and are re-normalised whenever a
   requirement adjusts one of them.

## Two problems found in the original engine

**1. The detail-flattening cell dropped a detail from every product.**
`raw_details[:-2]` was meant to drop the empty fragment left by the trailing `"; "`
separator, but it dropped one real detail as well — so the last specification of
every product never reached the TF-IDF corpus. Preprocessing now filters empty
fragments explicitly and keeps every specification.

**2. Splitting `REVIEW COUNT` crashed on products with no reviews.**
The original used `list.remove("Reviews")`, which raises `ValueError` on a product
whose label reads `"980 Ratings"`. It is now a regex that handles both shapes and
falls back to `0`.

## The selector situation

The notebook's selectors (`a.wjcEIp`, `span.VU-ZEz`, `div.Nx9bqj CxhGGd`,
`div.XQDdHH`, `li._7eSDEz`, `li._1u+DIo`, `span.Wphh3N`) are preserved verbatim in
`backend/app/config.py` and are always tried first.

They no longer match: Flipkart now serves generated per-build class names
(`css-g5y9jx`, `v1zwn21m`) and loads the specification table separately. Replacing
them with today's generated names would be guesswork that breaks again within days,
so instead `services/extractors.py` fills *only the fields the configured selectors
left empty*, using structural sources that do not depend on styling:

* the `schema.org` `ItemList` / `Product` JSON-LD blocks Flipkart embeds for search
  engines — product URL, name, price, description;
* the `"rating" / "ratingsCount" / "reviewsCount"` block in the page's embedded state;
* the `/p/itm…` URL shape and the `<h1>` element.

When you work out the current class names, put them in the `FLIPKART_SELECTORS`
environment variable (a JSON object merged over the defaults) and they take
precedence again — no code change required. Set `STRUCTURAL_FALLBACK=false` to run
strictly on the configured selectors.

**Known limitation:** the specification list (`Battery life: 50 hr`, …) is loaded
client-side by Flipkart and is not in the HTML a single request returns, so
live-scraped rows currently have no `DETAILS` attributes. Flipkart titles are
specification-dense, so ranking still works; the results table hides attribute
columns automatically when the data is not there.

## API

`POST /api/recommend`

```json
{ "query": "bluetooth headphones", "requirements": ">4.5 rating, high battery life", "limit": 10 }
```

```json
{
  "query": "bluetooth headphones",
  "requirements": ">4.5 rating, high battery life",
  "limit": 10,
  "count": 10,
  "source": "live",
  "datasetSize": 20,
  "elapsedMs": 8421,
  "parsed": { "minRating": 4.5, "maxPrice": null, "boostedFeatures": ["battery life"], "notes": ["Rating >= 4.5"] },
  "warnings": [],
  "results": [
    {
      "name": "…",
      "price": 1299,
      "rating": 4.3,
      "score": 0.94,
      "similarity": 0.71,
      "url": "https://www.flipkart.com/…",
      "searchUrl": "https://www.flipkart.com/search?q=…",
      "ratingsCount": 12000,
      "reviewsCount": 900,
      "attributes": { "Battery life": "30 Hrs" },
      "highlights": ["Battery life: 30 Hrs"]
    }
  ]
}
```

Validation, limits and error handling are described in `backend/README.md`.

## Disclaimer

Scraping is for educational and personal use. Flipkart's markup changes frequently
and its terms of service apply.
