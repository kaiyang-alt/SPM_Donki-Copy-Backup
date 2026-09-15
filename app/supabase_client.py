import os

from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("Supabase environment variables are missing.")

supabase: Client = create_client(supabase_url, supabase_key)