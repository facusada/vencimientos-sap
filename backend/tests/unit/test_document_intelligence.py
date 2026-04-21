from types import SimpleNamespace

from app.services.document_intelligence import (
    AzureOpenAIDocumentIntelligence,
    FakeSemanticDocumentIntelligence,
    create_document_intelligence_provider,
)
from app.utils.settings import AppSettings


def test_fake_document_intelligence_detects_varied_phrasings():
    text = """
    SAP Product Version for ECC 6.0 is supported until 02.2027 according to the maintenance plan.
    The system kernel expires on 2026-12-31 and should be upgraded.
    SSL Server PSE certificate valid until 31.01.2028.
    """

    provider = FakeSemanticDocumentIntelligence()

    result = provider.extract_expirations(text)

    assert {"nombre": "SAP Product Version for ECC 6.0", "fecha": "02.2027"} in result
    assert {"nombre": "The system kernel", "fecha": "2026-12-31"} in result
    assert {"nombre": "SSL Server PSE certificate", "fecha": "31.01.2028"} in result


def test_azure_openai_document_intelligence_parses_json_response():
    captured_kwargs: dict[str, object] = {}

    def create_completion(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_response

    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"items":[{"nombre":"Kernel","fecha":"2026-12-31"},{"nombre":"SAP Product Version","fecha":"02.2027"}]}'
                )
            )
        ]
    )
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=create_completion
            )
        )
    )

    provider = AzureOpenAIDocumentIntelligence(
        settings=AppSettings(
            ai_provider="azure-openai",
            azure_openai_api_key="test-key",
            azure_openai_endpoint="https://example-resource.openai.azure.com",
            azure_openai_deployment="gpt-4.1-mini",
        ),
        client=mock_client,
    )

    result = provider.extract_expirations("Kernel expires on 2026-12-31.")

    assert captured_kwargs["response_format"] == {"type": "json_object"}
    assert "BEGIN_DOCUMENT" in captured_kwargs["messages"][1]["content"]
    assert "Use only component names that appear in the document text" in captured_kwargs["messages"][1]["content"]
    assert "Ignore analysis windows" in captured_kwargs["messages"][1]["content"]
    assert result == [
        {"nombre": "Kernel", "fecha": "2026-12-31"},
        {"nombre": "SAP Product Version", "fecha": "02.2027"},
    ]


def test_azure_openai_document_intelligence_extracts_json_from_markdown_fence():
    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='```json\n{"items":[{"nombre":"Kernel","fecha":"2026-12-31"}]}\n```'
                )
            )
        ]
    )
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: mock_response
            )
        )
    )

    provider = AzureOpenAIDocumentIntelligence(
        settings=AppSettings(
            ai_provider="azure-openai",
            azure_openai_api_key="test-key",
            azure_openai_endpoint="https://example-resource.openai.azure.com",
            azure_openai_deployment="gpt-4.1-mini",
        ),
        client=mock_client,
    )

    result = provider.extract_expirations("Kernel expires on 2026-12-31.")

    assert result == [{"nombre": "Kernel", "fecha": "2026-12-31"}]


def test_azure_openai_document_intelligence_extracts_json_when_wrapped_in_text():
    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='Encontré estos resultados:\n{"items":[{"nombre":"Kernel","fecha":"2026-12-31"}]}'
                )
            )
        ]
    )
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: mock_response
            )
        )
    )

    provider = AzureOpenAIDocumentIntelligence(
        settings=AppSettings(
            ai_provider="azure-openai",
            azure_openai_api_key="test-key",
            azure_openai_endpoint="https://example-resource.openai.azure.com",
            azure_openai_deployment="gpt-4.1-mini",
        ),
        client=mock_client,
    )

    result = provider.extract_expirations("Kernel expires on 2026-12-31.")

    assert result == [{"nombre": "Kernel", "fecha": "2026-12-31"}]


def test_create_document_intelligence_provider_builds_azure_provider_from_settings():
    provider = create_document_intelligence_provider(
        settings=AppSettings(
            ai_provider="azure-openai",
            azure_openai_api_key="test-key",
            azure_openai_endpoint="https://example-resource.openai.azure.com",
            azure_openai_deployment="gpt-4.1-mini",
        ),
        client=object(),
    )

    assert isinstance(provider, AzureOpenAIDocumentIntelligence)
