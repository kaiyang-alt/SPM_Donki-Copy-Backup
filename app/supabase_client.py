import os

from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()


def create_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("Supabase environment variables are missing.")

    return create_client(supabase_url, supabase_key)


def create_authenticated_supabase_client(access_token: str) -> Client:
    """Create a Supabase client whose database calls use the user's JWT."""
    client = create_supabase_client()
    client.postgrest.auth(access_token)
    return client
