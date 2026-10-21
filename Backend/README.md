# Smart Product Search (FastAPI + LangGraph + MongoDB)

Backend only. Handles: name/brand/model search, natural-language queries (English + Hinglish),
category/brand/budget/spec filters, autocomplete and spelling correction.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: add GROQ_API_KEY for the LLM fallback
docker compose up -d            # local MongoDB (or put an Atlas URI in .env)
python -m scripts.seed          # 36 SAMPLE products (illustrative data)
uvicorn app.main:app --reload   # docs at http://localhost:8000/docs
pytest                          # tests use a fake DB, no Mongo needed
```

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/search` | `q` + structured `filters` (incl. `specs`) + `sort` + pagination |
| GET | `/api/v1/search` | same, query-string version (`q, category, brand, min_price, max_price, ...`) |
| GET | `/api/v1/suggest?q=lap` | autocomplete + `did_you_mean` |
| GET | `/api/v1/filters?category=laptop` | facets: brands, price range, spec options |

```bash
curl -X POST localhost:8000/api/v1/search -H 'content-type: application/json' \
  -d '{"q": "Coding ke liye ₹40,000 ke andar laptop"}'

curl -X POST localhost:8000/api/v1/search -H 'content-type: application/json' \
  -d '{"q":"samsng phone","filters":{"max_price":20000,"specs":[{"field":"ram_gb","op":"gte","value":8}]},"sort":"price_asc"}'
```

The response includes `interpreted` (what we understood, usable as filter chips), `query.corrections`
(spelling fixes applied), and `relaxed` (constraints we loosened when nothing matched, e.g. budget stretched).

## LangGraph flow (`app/graph/workflow.py`)
```
normalize -> spell_correct -> parse_rules --(complex query?)--> parse_llm
                                   \______________________________/
                                                  v
                       merge_filters -> search_db --(0 results)--> relax -> search_db
                                              \--> finish
```
* `parse_rules` is free and deterministic (budget, specs, brand, category, use-case).
* `parse_llm` (Groq) runs only when the rules missed something in a long query; failures fall back silently.
* `relax` loosens one constraint at a time, least important first, and reports it.
* Spec filter fields are whitelisted (`catalog.ALLOWED_SPEC_FIELDS`), so clients can't inject Mongo operators.

## Adding categories / real data
* New category: add it in `app/catalog.py` (synonyms, spec fields, use-cases).
* Real data: write an ingest job that maps Flipkart / SerpApi results to the document shape in
  `scripts/seed.py`, then call `rebuild_search_terms(db)`.
* `search_terms` also stores queries that returned results (shared across users): moderate or disable
  with `LOG_QUERIES=false` before going public.
* The vocabulary is loaded into memory at startup; restart (or call `vocab.load(db)`) after re-indexing.
