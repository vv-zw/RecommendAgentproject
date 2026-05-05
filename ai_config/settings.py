# ai_config/settings.py
import os

# --- Database Settings ---
DATABASE_URL = os.environ.get("DATABASE_URL")

# --- Feature Flags ---
DEBUG_MODE_ENABLED = os.environ.get("DEBUG_MODE_ENABLED", "true").lower() == "true"
EXPLAIN_ENABLED = os.environ.get("EXPLAIN_ENABLED", "true").lower() == "true"

# --- Logging Settings ---
LOG_FILE_PATH = os.environ.get("LOG_FILE", "logs/app.log")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# --- LLM Settings ---
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "deepseek")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-v2")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
