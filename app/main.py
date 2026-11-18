# app/main.py - the entry point of our backend

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (importing registers the tables)
from app.database import Base, engine, get_db
from app.routers import documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts: create any missing tables."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Document Extraction Platform",
    description="Extracts structured data from invoices using AI.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(documents.router)


@app.get("/")
def root():
    """Home endpoint: a friendly welcome message."""
    return {"message": "Document Extraction Platform API is running"}


@app.get("/health")
def health_check():
    """Health endpoint: lets tools check that the server is alive."""
    return {"status": "ok"}


@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    """Checks that the API can really talk to PostgreSQL."""
    db.execute(text("SELECT 1"))
    return {"database": "connected"}