from io import BytesIO

from openpyxl import load_workbook

from app.models.expiration import ExpirationRecord
from app.services.excel_service import build_expiration_workbook


def test_build_expiration_workbook_generates_expected_columns_and_rows():
    records = [
        ExpirationRecord(
            source_section="SAP Kernel Release",
            name="Kernel",
            expiration_date="2026-12-31",
        ),
        ExpirationRecord(
            source_section="Certificates",
            name="Certificate ABC",
            expiration_date="2026-10-01",
        ),
    ]

    payload = build_expiration_workbook(records)

    workbook = load_workbook(filename=BytesIO(payload))
    sheet = workbook.active

    assert sheet.title == "Expirations"
    assert sheet["A1"].value == "Seccion"
    assert sheet["B1"].value == "Nombre"
    assert sheet["C1"].value == "Fecha"
    assert sheet["A2"].value == "SAP Kernel Release"
    assert sheet["B2"].value == "Kernel"
    assert sheet["C2"].value == "2026-12-31"
    assert sheet["A3"].value == "Certificates"
    assert sheet["B3"].value == "Certificate ABC"
    assert sheet["C3"].value == "2026-10-01"
