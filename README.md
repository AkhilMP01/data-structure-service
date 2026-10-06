# Data Structure Management Service

A small REST API for keeping track of metadata about data — not the actual
records, but the structure around them. So you've got **datasets** (business
entities, e.g. Customer or Order) and the **data elements** inside them (the
fields, e.g. email, date_of_birth).

Stack is FastAPI + SQLModel on SQLite.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate   # windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Easiest way to poke at it is the Swagger UI at http://localhost:8000/docs —
you can hit every endpoint from there without touching curl.

Run the tests with `pytest`.

There's a Dockerfile too if you'd rather:

```bash
docker build -t dsm .
docker run --rm -p 8000:8000 dsm
```

## Endpoints

- `POST /datasets` — create a dataset
- `GET /datasets` — list them
- `GET /datasets/{id}` — one dataset, with its elements included
- `POST /datasets/{id}/elements` — add an element to a dataset
- `GET /datasets/{id}/elements` — list a dataset's elements

That last one takes a few optional filters: `?data_type=STRING`,
`?is_pii=true`, `?search=mail`.

Quick run-through:

```bash
curl -X POST localhost:8000/datasets -H 'content-type: application/json' \
  -d '{"name":"Customer","description":"a customer"}'

curl -X POST localhost:8000/datasets/1/elements -H 'content-type: application/json' \
  -d '{"name":"email","data_type":"STRING","is_pii":true}'

curl localhost:8000/datasets/1
```

## The data model

It's a one-to-many setup. A dataset has many data elements, and an element
belongs to exactly one dataset — it doesn't really mean anything on its own, so
if you delete a dataset its elements go with it.

```
Dataset (id, name, description, created_at, updated_at)
  |
  |  many
  v
DataElement (id, dataset_id, name, data_type, description,
             is_required, is_pii, created_at)
```

Some choices I made and why:

**Element names are unique within a dataset, not across the whole thing.** This
was the rule I spent the most time on. You can't define `email` twice on
Customer, but Customer and Supplier can both have an `email` — they're
different fields that might even have different types. It's a composite unique
constraint on (dataset_id, name), and there's a test for it.

**I put the real constraints in the database**, not just in the API code. The
API does check first, mostly so you get a readable 409 instead of an ugly 500,
but the database is what actually guarantees things. A validation check in code
can be skipped by a bug, or two requests can race past it at the same time — a
DB constraint can't be fooled that way.

Side note that bit me: SQLite doesn't enforce foreign keys unless you turn them
on per connection (`PRAGMA foreign_keys=ON`). Without it the cascade delete just
quietly doesn't happen. It's set in `app/database.py`.

**data_type is an enum** — STRING, INTEGER, FLOAT, BOOLEAN, DATE, DATETIME —
rather than a plain string. Keeps the values consistent and you get a proper
dropdown in the Swagger docs. The cost is that adding a new type means a code
change, but the list is short and doesn't change much, so I was fine with that.

**Validation sits in two spots.** Pydantic (in `schemas.py`) checks the request
itself — required fields, lengths, a real enum value, names that aren't just
blank — and bounces bad input with a 422 before it reaches the DB. The database
handles the integrity side (uniqueness, foreign keys). I kept the request/
response schemas separate from the table models so a client can't go setting
`id` or `created_at` itself.

## Extras

Beyond the core requirements I added the PII flag (`is_pii`) with a filter to
list just the PII fields, the search/filter on the elements list, the Docker
setup, and Swagger comes for free with FastAPI.

## Assumptions & trade-offs

- SQLite with `create_all` on startup to keep things simple. For anything real
  I'd use Postgres and Alembic migrations.
- Only built create / list / retrieve plus add / list elements, since that's
  what the brief asked for. No update or delete endpoints yet — though the
  cascade's already wired up for when delete gets added.
- No auth, no pagination. Pagination is the first thing I'd add before real data
  volumes, auth would depend on how this fits into the wider system.
- Since this only stores *metadata* about fields, it doesn't try to validate
  real values against those types — there aren't any records here. That check
  belongs wherever the actual data lives.

## Stuff I'd do next

PATCH/DELETE endpoints, pagination + sorting on the lists, swap create_all for
real migrations, and probably some retention/lifecycle metadata — the model
takes extra columns without much fuss.

## Layout

```
app/
  main.py         app + startup
  database.py     engine, session, the sqlite FK pragma
  models.py       tables + constraints
  schemas.py      request/response models
  routers/
    datasets.py   the endpoints
tests/
  conftest.py     in-memory db fixture
  test_api.py
```
