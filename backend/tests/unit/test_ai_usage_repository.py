import pytest

from app.models.expiration import EwaAiUsage
from app.services.ai_usage_repository import PostgresAiUsageRepository


def test_postgres_ai_usage_repository_requires_database_url_on_save():
    repository = PostgresAiUsageRepository("")

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        repository.save_usages(
            [EwaAiUsage(client="Cliente A", period="2026-04", source_filename="a.pdf")]
        )
