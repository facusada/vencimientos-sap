from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import app
from app.services.document_intelligence import DocumentIntelligenceProvider
from app.services.ewa_analysis_service import get_document_intelligence_provider


client = TestClient(app)


class StubDocumentIntelligenceProvider(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        assert "supported until 02.2027" in text
        return [
            {"nombre": "SAP Product Version", "fecha": "02.2027"},
            {"nombre": "Kernel", "fecha": "2026-12-31", "hito": "End of Standard Vendor Support"},
            {"nombre": "Kernel", "fecha": "2026-12-31", "hito": "End of Standard Vendor Support"},
        ]


def test_post_ewa_analyze_returns_excel_file_for_pdf(monkeypatch):
    app.dependency_overrides[get_document_intelligence_provider] = (
        lambda: StubDocumentIntelligenceProvider()
    )
    monkeypatch.setattr(
        "app.services.ewa_analysis_service.extract_text",
        lambda filename, payload: (
            "SAP Product Version is supported until 02.2027.\nKernel expires on 2026-12-31."
            if filename == "ewa.pdf" and payload == b"fake-pdf"
            else ""
        ),
    )

    try:
        response = client.post(
            "/ewa/analyze",
            files={
                "file": (
                    "ewa.pdf",
                    b"fake-pdf",
                    "application/pdf",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment; filename=ewa-expirations.xlsx" in response.headers["content-disposition"]

    workbook = load_workbook(filename=BytesIO(response.content))
    sheet = workbook.active

    assert sheet["A1"].value == "Seccion"
    assert sheet["B1"].value == "Nombre"
    assert sheet["C1"].value == "Hito"
    assert sheet["D1"].value == "Fecha"
    assert sheet["A2"].value is None
    assert sheet["B2"].value == "SAP Product Version"
    assert sheet["C2"].value is None
    assert sheet["D2"].value == "2027-02-28"
    assert sheet["A3"].value is None
    assert sheet["B3"].value == "Kernel"
    assert sheet["C3"].value == "End of Standard Vendor Support"
    assert sheet["D3"].value == "2026-12-31"


def test_post_api_ewa_analyze_returns_excel_file_for_pdf(monkeypatch):
    app.dependency_overrides[get_document_intelligence_provider] = (
        lambda: StubDocumentIntelligenceProvider()
    )
    monkeypatch.setattr(
        "app.services.ewa_analysis_service.extract_text",
        lambda filename, payload: (
            "SAP Product Version is supported until 02.2027.\nKernel expires on 2026-12-31."
            if filename == "ewa.pdf" and payload == b"fake-pdf"
            else ""
        ),
    )

    try:
        response = client.post(
            "/api/ewa/analyze",
            files={
                "file": (
                    "ewa.pdf",
                    b"fake-pdf",
                    "application/pdf",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment; filename=ewa-expirations.xlsx" in response.headers["content-disposition"]


def test_post_ewa_analyze_rejects_unsupported_extension():
    response = client.post(
        "/ewa/analyze",
        files={"file": ("ewa.csv", b"irrelevant", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"


def test_post_ewa_analyze_returns_clear_error_when_ai_finds_nothing(monkeypatch):
    class EmptyProvider(DocumentIntelligenceProvider):
        def extract_expirations(self, text: str) -> list[dict[str, str]]:
            return []

    app.dependency_overrides[get_document_intelligence_provider] = lambda: EmptyProvider()
    monkeypatch.setattr(
        "app.services.ewa_analysis_service.extract_text",
        lambda filename, payload: (
            "This EWA contains recommendations but no support dates."
            if filename == "ewa.pdf" and payload == b"fake-pdf"
            else ""
        ),
    )

    try:
        response = client.post(
            "/ewa/analyze",
            files={
                "file": (
                    "ewa.pdf",
                    b"fake-pdf",
                    "application/pdf",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "No se detectaron fechas de vencimiento en el EWA enviado."


def test_post_ewa_analyze_rejects_non_pdf_input():
    response = client.post(
        "/ewa/analyze",
        files={
            "file": (
                "ewa.docx",
                b"legacy-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"
