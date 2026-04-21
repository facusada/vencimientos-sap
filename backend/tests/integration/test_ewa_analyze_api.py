from io import BytesIO

from docx import Document
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
            {"nombre": "Kernel", "fecha": "2026-12-31"},
            {"nombre": "Kernel", "fecha": "2026-12-31"},
        ]


def test_post_ewa_analyze_returns_excel_file_for_docx():
    app.dependency_overrides[get_document_intelligence_provider] = (
        lambda: StubDocumentIntelligenceProvider()
    )

    document = Document()
    document.add_paragraph("SAP Product Version is supported until 02.2027.")
    document.add_paragraph("Kernel expires on 2026-12-31.")

    buffer = BytesIO()
    document.save(buffer)

    try:
        response = client.post(
            "/ewa/analyze",
            files={
                "file": (
                    "ewa.docx",
                    buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
    assert sheet["C1"].value == "Fecha"
    assert sheet["A2"].value is None
    assert sheet["B2"].value == "SAP Product Version"
    assert sheet["C2"].value == "2027-02-28"
    assert sheet["A3"].value is None
    assert sheet["B3"].value == "Kernel"
    assert sheet["C3"].value == "2026-12-31"


def test_post_ewa_analyze_rejects_unsupported_extension():
    response = client.post(
        "/ewa/analyze",
        files={"file": ("ewa.csv", b"irrelevant", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type"


def test_post_ewa_analyze_returns_empty_excel_when_ai_finds_nothing():
    class EmptyProvider(DocumentIntelligenceProvider):
        def extract_expirations(self, text: str) -> list[dict[str, str]]:
            return []

    app.dependency_overrides[get_document_intelligence_provider] = lambda: EmptyProvider()

    document = Document()
    document.add_paragraph("This EWA contains recommendations but no support dates.")

    buffer = BytesIO()
    document.save(buffer)

    try:
        response = client.post(
            "/ewa/analyze",
            files={
                "file": (
                    "ewa.docx",
                    buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    workbook = load_workbook(filename=BytesIO(response.content))
    sheet = workbook.active

    assert sheet.max_row == 1
    assert sheet["A1"].value == "Seccion"
    assert sheet["B1"].value == "Nombre"
    assert sheet["C1"].value == "Fecha"


def test_post_ewa_analyze_returns_excel_file_for_doc(monkeypatch):
    class LegacyStubProvider(DocumentIntelligenceProvider):
        def extract_expirations(self, text: str) -> list[dict[str, str]]:
            assert "legacy doc content" in text
            return [{"nombre": "Kernel", "fecha": "2026-12-31"}]

    app.dependency_overrides[get_document_intelligence_provider] = (
        lambda: LegacyStubProvider()
    )
    monkeypatch.setattr(
        "app.services.ewa_analysis_service.extract_text",
        lambda filename, payload: "legacy doc content" if filename == "ewa.doc" and payload == b"legacy-doc" else "",
    )

    try:
        response = client.post(
            "/ewa/analyze",
            files={
                "file": (
                    "ewa.doc",
                    b"legacy-doc",
                    "application/msword",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    workbook = load_workbook(filename=BytesIO(response.content))
    sheet = workbook.active

    assert sheet["A1"].value == "Seccion"
    assert sheet["B1"].value == "Nombre"
    assert sheet["C1"].value == "Fecha"
    assert sheet["A2"].value is None
    assert sheet["B2"].value == "Kernel"
    assert sheet["C2"].value == "2026-12-31"
