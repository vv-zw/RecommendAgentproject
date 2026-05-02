import pymysql
from ai_config import settings
from urllib.parse import urlparse

def get_db_connection():
    """Establishes a connection to the MySQL database using PyMySQL."""
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured in the environment.")

    try:
        url = urlparse(settings.DATABASE_URL)
        connection = pymysql.connect(
            host=url.hostname,
            user=url.username,
            password=url.password,
            database=url.path[1:], # Remove leading '/'
            port=url.port or 3306,
            cursorclass=pymysql.cursors.DictCursor # Return rows as dictionaries
        )
        return connection
    except pymysql.MySQLError as err:
        print(f"Error connecting to database: {err}")
        raise RuntimeError("Failed to connect to the database.") from err

def is_database_enabled() -> bool:
    """Checks if the database URL is configured."""
    return bool(settings.DATABASE_URL)
