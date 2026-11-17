# app/main.py - the entry point of our backend

from fastapi import FastAPI

# Create the application object. The title shows up in the auto-generated docs.
app = FastAPI(
    title="Document Extraction Platform",
    description="Extracts structured data from invoices using AI.",
    version="0.1.0",
)


@app.get("/")
def root():
    """Home endpoint: a friendly welcome message."""
    return {"message": "Document Extraction Platform API is running"}


@app.get("/health")
def health_check():
    """Health endpoint: lets tools check that the server is alive."""
    return {"status": "ok"}