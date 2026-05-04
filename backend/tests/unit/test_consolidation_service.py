from app.models.expiration import AnalyzedEwaDocument
from app.models.expiration import AiUsageMetrics
from app.models.expiration import ExpirationRecord
from app.services.consolidation_service import consolidate_ewa_documents


def test_consolidate_ewa_documents_adds_client_period_source_and_component_catalog():
    documents = [
        AnalyzedEwaDocument(
            client="Cliente A",
            period="2026-04",
            filename="cliente-a.pdf",
            ai_usage=AiUsageMetrics(input_tokens=900, output_tokens=120, total_tokens=1020),
            records=[
                ExpirationRecord(
                    source_section="SAP Kernel Release",
                    name="SAP Kernel Release",
                    expiration_date="2026-12-31",
                    milestone="End of Standard Vendor Support",
                ),
                ExpirationRecord(
                    source_section="Custom",
                    name="SAP Cloud Connector",
                    expiration_date="2027-01-31",
                    milestone="",
                ),
            ],
        )
    ]

    result = consolidate_ewa_documents(documents)

    assert [
        (
            item.client,
            item.period,
            item.component,
            item.detected_name,
            item.expiration_date,
            item.source_filename,
            item.is_cataloged,
        )
        for item in result.records
    ] == [
        (
            "Cliente A",
            "2026-04",
            "SAP Kernel",
            "SAP Kernel Release",
            "2026-12-31",
            "cliente-a.pdf",
            True,
        ),
        (
            "Cliente A",
            "2026-04",
            "SAP Cloud Connector",
            "SAP Cloud Connector",
            "2027-01-31",
            "cliente-a.pdf",
            False,
        ),
    ]
    assert result.clients == [("Cliente A", "2026-04")]
    assert [
        (
            item.client,
            item.period,
            item.source_filename,
            item.input_tokens,
            item.output_tokens,
            item.total_tokens,
        )
        for item in result.ai_usages
    ] == [
        (
            "Cliente A",
            "2026-04",
            "cliente-a.pdf",
            900,
            120,
            1020,
        )
    ]


def test_consolidate_ewa_documents_keeps_client_row_when_no_records_are_detected():
    documents = [
        AnalyzedEwaDocument(
            client="Cliente Sin Fiori",
            period="2026-04",
            filename="empty.pdf",
            ai_usage=AiUsageMetrics(input_tokens=400, output_tokens=20, total_tokens=420),
            records=[],
        )
    ]

    result = consolidate_ewa_documents(documents)

    assert result.records == []
    assert result.clients == [("Cliente Sin Fiori", "2026-04")]
    assert [
        (item.client, item.period, item.source_filename, item.reason)
        for item in result.no_result_documents
    ] == [
        (
            "Cliente Sin Fiori",
            "2026-04",
            "empty.pdf",
            "Sin vencimientos detectados",
        )
    ]
    assert [
        (
            item.client,
            item.period,
            item.source_filename,
            item.input_tokens,
            item.output_tokens,
            item.total_tokens,
        )
        for item in result.ai_usages
    ] == [
        (
            "Cliente Sin Fiori",
            "2026-04",
            "empty.pdf",
            400,
            20,
            420,
        )
    ]
