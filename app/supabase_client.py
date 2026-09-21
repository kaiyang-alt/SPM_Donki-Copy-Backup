import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL") or "https://mock.supabase.co"
supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_KEY") or "mock-key"

# Global default client instance
supabase: Client = create_client(supabase_url, supabase_key)


def create_supabase_client() -> Client:
    """Returns a basic unauthenticated or default Supabase client."""
    return create_client(supabase_url, supabase_key)


def create_authenticated_supabase_client(access_token: str) -> Client:
    """Returns a Supabase client configured with a specific user's Bearer access token."""
    client = create_client(supabase_url, supabase_key)
    if access_token:
        client.postgrest.auth(access_token)
    return client