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

    assert {"nombre": "SAP Product Version for ECC 6.0", "fecha": "02.2027", "hito": ""} in result
    assert {"nombre": "The system kernel", "fecha": "2026-12-31", "hito": ""} in result
    assert {"nombre": "SSL Server PSE certificate", "fecha": "31.01.2028", "hito": ""} in result


def test_fake_document_intelligence_detects_vendor_support_dates_from_ewa_tables():
    text = """
    End of Standard Vendor Support*
    End of Extended Vendor Support*
    Comment
    SQL Server 2012
    11.07.2017
    12.07.2022
    Planned Date
    1177356
    * Maintenance phases and duration for the DB version are defined by the vendor.
    Standard vendor support for your database version has already ended / will end in the near future.
    09.01.2018
    10.10.2023
    1177282
    * Maintenance phases and duration for the operating system version are defined by the vendor.
    The following table lists all information about your SAP kernel(s) currently in use.
    Instance(s)
    Age in Months
    OS Family
    749
    500
    97
    Windows Server (x86_64)
    """

    provider = FakeSemanticDocumentIntelligence()

    result = provider.extract_expirations(text)

    assert {
        "nombre": "SQL Server 2012",
        "fecha": "11.07.2017",
        "hito": "End of Standard Vendor Support",
    } in result
    assert {
        "nombre": "SQL Server 2012",
        "fecha": "12.07.2022",
        "hito": "End of Extended Vendor Support",
    } in result
    assert {
        "nombre": "Operating System",
        "fecha": "09.01.2018",
        "hito": "End of Standard Vendor Support",
    } in result
    assert {
        "nombre": "Operating System",
        "fecha": "10.10.2023",
        "hito": "End of Extended Vendor Support",
    } in result


def test_azure_openai_document_intelligence_parses_json_response():
    captured_kwargs: dict[str, object] = {}

    def create_completion(**kwargs):
        captured_kwargs.update(kwargs)
        return mock_response

    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"items":[{"nombre":"Kernel","fecha":"2026-12-31","hito":"End of Extended Vendor Support"},{"nombre":"SAP Product Version","fecha":"02.2027","hito":""}]}'
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
    assert '"hito":"End of Standard Vendor Support or End of Extended Vendor Support when present, otherwise empty string"' in captured_kwargs["messages"][0]["content"]
    assert "Return each unique nombre, fecha, and hito combination at most once." in captured_kwargs["messages"][0]["content"]
    assert "Use only component names that appear in the document text" in captured_kwargs["messages"][1]["content"]
    assert "Ignore analysis windows" in captured_kwargs["messages"][1]["content"]
    assert result == [
        {"nombre": "Kernel", "fecha": "2026-12-31", "hito": "End of Extended Vendor Support"},
        {"nombre": "SAP Product Version", "fecha": "02.2027", "hito": ""},
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

    assert result == [{"nombre": "Kernel", "fecha": "2026-12-31", "hito": ""}]


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

    assert result == [{"nombre": "Kernel", "fecha": "2026-12-31", "hito": ""}]


def test_azure_openai_document_intelligence_recovers_complete_items_from_truncated_json():
    repeated_item = '{"nombre":"SAP HANA Database","fecha":"31.12.2023","hito":""}'
    mock_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=(
                        '{"items":['
                        '{"nombre":"SAP HANA Database","fecha":"31.12.2023","hito":"End of Standard Vendor Support"},'
                        f"{repeated_item},{repeated_item},"
                        '{"nombre":"SAP'
                    )
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

    result = provider.extract_expirations("SAP HANA Database expires on 31.12.2023.")

    assert result == [
        {
            "nombre": "SAP HANA Database",
            "fecha": "31.12.2023",
            "hito": "End of Standard Vendor Support",
        },
        {"nombre": "SAP HANA Database", "fecha": "31.12.2023", "hito": ""},
    ]


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
