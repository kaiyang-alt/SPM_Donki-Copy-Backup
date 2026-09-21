import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Find SPM_Donki root directory dynamically (2 levels up from app1/supabase_client.py)
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path)

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "") or os.environ.get("SUPABASE_KEY", "")

if not url or not key:
    raise ValueError(
        f"Missing Supabase credentials! Could not load SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY "
        f"from environment or .env file at {env_path}"
    )

supabase: Client = create_client(url, key)