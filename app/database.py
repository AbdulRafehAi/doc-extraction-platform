# app/database.py - database connection setup

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# The engine is the connection to PostgreSQL
engine = create_engine(settings.database_url)

# A session is one "conversation" with the database
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """All our table classes will inherit from this."""
    pass


def get_db():
    """Give each request its own session, and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()