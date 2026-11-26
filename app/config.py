"""Application settings read from environment variables (and a .env file)."""

import os

from dotenv import load_dotenv

load_dotenv()

# Example: postgresql+psycopg2://user:password@localhost:5432/socialradar
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/socialradar",
)

# --- Authentication (JWT) ---------------------------------------------------
# SECRET_KEY signs the tokens. Set a long random value in .env for real use,
# e.g. generate one with:  python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))  # tests use a lower value (faster)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
