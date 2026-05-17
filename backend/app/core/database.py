"""Engine helpers for hosted Postgres (Supabase PgBouncer / transaction pooler)."""

from sqlalchemy.engine import make_url


def uses_transaction_pooler(database_url: str) -> bool:
    """True when the URL targets PgBouncer transaction pooling (e.g. Supabase :6543)."""
    parsed = make_url(database_url)
    host = (parsed.host or "").lower()
    return "pooler.supabase.com" in host or parsed.port == 6543


def asyncpg_connect_args(database_url: str) -> dict[str, int]:
    """Disable asyncpg prepared statements — required for Supabase transaction pooler."""
    if uses_transaction_pooler(database_url):
        return {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        }
    return {}


def psycopg_connect_args(database_url: str) -> dict[str, None]:
    """Disable psycopg prepared statements for the same pooler mode."""
    if uses_transaction_pooler(database_url):
        return {"prepare_threshold": None}
    return {}
