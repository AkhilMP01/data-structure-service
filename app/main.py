# Run with: uvicorn app.main:app --reload
# Swagger UI at /docs

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import create_db_and_tables
from .routers import datasets


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all is fine for this; a real app would use Alembic migrations
    create_db_and_tables()
    yield


app = FastAPI(
    title="Data Structure Management Service",
    description="Manage datasets (business entities) and the data elements they contain.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(datasets.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
