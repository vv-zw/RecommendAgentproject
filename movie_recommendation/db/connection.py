import psycopg
import psycopg.rows
from movie_recommendation.config import Config


def get_db_connection():
    """Establishes a connection to the PostgreSQL database using psycopg3."""
    url = Config.get_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not configured in the environment.")
    return psycopg.connect(url, row_factory=psycopg.rows.dict_row)


def is_database_enabled() -> bool:
    """Checks if the database URL is configured."""
    return bool(Config.get_database_url())
