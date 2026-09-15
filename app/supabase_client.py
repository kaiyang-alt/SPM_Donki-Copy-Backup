import os

from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")

if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
    raise ValueError("Supabase environment variables are missing.")


def create_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)