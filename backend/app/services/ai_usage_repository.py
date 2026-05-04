from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.expiration import EwaAiUsage
from app.utils.settings import get_settings


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ewa_ai_usage (
    id BIGSERIAL PRIMARY KEY,
    client TEXT NOT NULL,
    input_tokens INTEGER NULL,
    output_tokens INTEGER NULL,
    total_tokens INTEGER NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

INSERT_USAGE_SQL = """
INSERT INTO ewa_ai_usage (
    client,
    input_tokens,
    output_tokens,
    total_tokens
) VALUES (%s, %s, %s, %s)
"""


class AiUsageRepository(ABC):
    @abstractmethod
    def save_usages(self, usages: list[EwaAiUsage]) -> None:
        """Persist AI usage entries."""


class PostgresAiUsageRepository(AiUsageRepository):
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def save_usages(self, usages: list[EwaAiUsage]) -> None:
        if not usages:
            return
        if not self._database_url:
            raise RuntimeError("DATABASE_URL is required to persist AI usage in PostgreSQL")

        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg dependency is not installed") from exc

        rows = [
            (
                usage.client,
                usage.input_tokens,
                usage.output_tokens,
                usage.total_tokens,
            )
            for usage in usages
        ]

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_TABLE_SQL)
                cursor.executemany(INSERT_USAGE_SQL, rows)
            connection.commit()


def get_ai_usage_repository() -> AiUsageRepository:
    settings = get_settings()
    return PostgresAiUsageRepository(settings.database_url or "")
