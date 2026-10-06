# Data Structure Management Service

Small REST API for managing metadata about data — **datasets** (business
entities like Customer or Order) and the **data elements** (fields like
`email`, `date_of_birth`) that belong to them.

Built with FastAPI + SQLModel + SQLite.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate   # windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then:
- http://localhost:8000/docs — Swagger UI, easiest way to try the endpoints
- http://localhost:8000/openapi.json — the raw schema

Tests:

```bash
pytest
```

Or with Docker:

```bash
docker build -t dsm . && docker run --rm -p 8000:8000 dsm
```

## Endpoints

| Method | Path | What it does |
|--------|------|--------------|
| POST | `/datasets` | create a dataset |
| GET | `/datasets` | list datasets |
| GET | `/datasets/{id}` | get a dataset + its elements |
| POST | `/datasets/{id}/elements` | add an element to a dataset |
| GET | `/datasets/{id}/elements` | list a dataset's elements (filterable) |

The list-elements endpoint takes optional filters: `?data_type=STRING`,
`?is_pii=true`, `?search=mail`.

Quick example:

```bash
curl -X POST localhost:8000/datasets -H 'content-type: application/json' \
  -d '{"name":"Customer","description":"a customer"}'

curl -X POST localhost:8000/datasets/1/elements -H 'content-type: application/json' \
  -d '{"name":"email","data_type":"STRING","is_pii":true}'

curl localhost:8000/datasets/1
```

## Data model

A Dataset has many DataElements (one-to-many). An element always belongs to
one dataset and can't exist without it, so deleting a dataset deletes its
elements.

```
Dataset (id, name[unique], description, created_at, updated_at)
   |
   | 1-to-many  (FK dataset_id, ON DELETE CASCADE)
   v
DataElement (id, dataset_id, name, data_type, description,
             is_required, is_pii, created_at)
             unique(dataset_id, name)
```

A few decisions worth calling out:

**Element names are unique per dataset, not globally.** That's the
`unique(dataset_id, name)` constraint. So `Customer` can't define `email`
twice, but `Customer.email` and `Supplier.email` are allowed — they're
genuinely different fields. This felt like the most important rule to get
right, so it's enforced in the DB and there's a test for it.

**Constraints are in the database, not just the API.** Uniqueness, the foreign
key, NOT NULL — all on the tables. The API checks the same things first to
give nicer error messages (409 instead of a 500), but the DB is the real
guarantee. API checks can be skipped by a bug or lost to a race between two
requests; the DB constraint can't.

> One SQLite gotcha: it ignores foreign keys unless you run
> `PRAGMA foreign_keys=ON` on each connection. Without that the cascade does
> nothing. That's handled in `app/database.py`.

**data_type is an enum**, not a free-text string: `STRING`, `INTEGER`,
`FLOAT`, `BOOLEAN`, `DATE`, `DATETIME`. Keeps stored values consistent and
shows up as a dropdown of valid values in the Swagger docs. Downside is that
adding a type is a code change, but the set is small and stable so that's fine.

**Validation is split in two.** Pydantic handles the shape of the request
(required fields, lengths, valid enum value, no blank names) and rejects bad
input with a 422 before it hits the DB. The database handles integrity
(uniqueness, FK). The request/response schemas in `schemas.py` are kept
separate from the table models in `models.py` so clients can't set fields like
`id` or `created_at`.

## Optional extras I included

- `is_pii` flag on elements, plus a filter to list only PII fields
- filtering/search on the elements list (by type, PII, name)
- Swagger/OpenAPI (free with FastAPI)
- Dockerfile

## Assumptions / trade-offs

- SQLite + `create_all` on startup to keep it simple. Real app → Postgres +
  Alembic migrations.
- Only create/list/retrieve + add/list elements, since that's what was asked.
  No update/delete endpoints yet (the cascade is already set up for delete
  though).
- No auth or pagination — out of scope here, but pagination is the first thing
  I'd add before any real data volume.
- This service stores *metadata* about fields, so it doesn't validate real
  record values against those types — there are no records yet. That belongs
  in whatever service stores the actual data.

## If I had more time

- PATCH/DELETE for datasets and elements
- pagination + sorting on the list endpoints
- retention/lifecycle fields (the model takes extra columns cleanly)
- swap create_all for Alembic

## Layout

```
app/
  main.py         app + startup
  database.py     engine, session, the SQLite FK pragma
  models.py       tables + constraints (the data model)
  schemas.py      request/response models (validation)
  routers/
    datasets.py   all the endpoints
tests/
  conftest.py     in-memory db fixture
  test_api.py
```
