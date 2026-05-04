from app.utils.settings import AppSettings, get_settings


def test_get_settings_reads_azure_openai_environment(monkeypatch):
    monkeypatch.setenv("EWA_AI_PROVIDER", "azure-openai")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example-resource.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/ewa")

    settings = get_settings()

    assert settings == AppSettings(
        ai_provider="azure-openai",
        azure_openai_api_key="test-key",
        azure_openai_endpoint="https://example-resource.openai.azure.com",
        azure_openai_deployment="gpt-4.1-mini",
        database_url="postgresql://user:pass@localhost:5432/ewa",
    )
