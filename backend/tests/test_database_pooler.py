from app.core.database import asyncpg_connect_args, uses_transaction_pooler


def test_transaction_pooler_detected_for_supabase() -> None:
    url = (
        "postgresql+asyncpg://postgres.abc:pass@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
    )
    assert uses_transaction_pooler(url) is True
    assert asyncpg_connect_args(url)["statement_cache_size"] == 0


def test_local_postgres_uses_default_cache() -> None:
    url = "postgresql+asyncpg://synapse:synapse@localhost:5432/synapse"
    assert uses_transaction_pooler(url) is False
    assert asyncpg_connect_args(url) == {}
