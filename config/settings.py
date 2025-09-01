from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in .env")

if not SERPAPI_KEY:
    print("Warning: SERPAPI_KEY not set — enrichment may fail")
