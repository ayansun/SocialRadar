"""Application settings read from environment variables (and a .env file)."""

import os

from dotenv import load_dotenv

load_dotenv()

# Example: postgresql+psycopg2://user:password@localhost:5432/socialradar
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/socialradar",
)
