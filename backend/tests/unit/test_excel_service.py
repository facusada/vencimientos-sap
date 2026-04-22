from io import BytesIO
from datetime import date

from openpyxl import load_workbook

from app.models.expiration import ExpirationRecord
from app.services.excel_service import build_expiration_workbook


def test_build_expiration_workbook_generates_expected_columns_and_rows():
    records = [
        ExpirationRecord(
            source_section="SAP Kernel Release",
            name="Kernel",
            expiration_date="2026-12-31",
            milestone="",
        ),
        ExpirationRecord(
            source_section="Certificates",
            name="Certificate ABC",
            expiration_date="2026-10-01",
            milestone="End of Extended Vendor Support",
        ),
    ]

    payload = build_expiration_workbook(records)

    workbook = load_workbook(filename=BytesIO(payload))
    sheet = workbook.active

    assert sheet.title == "Expirations"
    assert sheet["A1"].value == "Seccion"
    assert sheet["B1"].value == "Nombre"
    assert sheet["C1"].value == "Hito"
    assert sheet["D1"].value == "Fecha"
    assert sheet["A2"].value == "SAP Kernel Release"
    assert sheet["B2"].value == "Kernel"
    assert sheet["C2"].value is None
    assert sheet["D2"].value == "2026-12-31"
    assert sheet["A3"].value == "Certificates"
    assert sheet["B3"].value == "Certificate ABC"
    assert sheet["C3"].value == "End of Extended Vendor Support"
    assert sheet["D3"].value == "2026-10-01"


def test_build_expiration_workbook_applies_status_colors_for_expired_and_active_dates():
    today = date.today()
    expired_date = today.replace(year=today.year - 1).isoformat()
    active_date = today.replace(year=today.year + 1).isoformat()
    records = [
        ExpirationRecord(
            source_section="Expired",
            name="Old component",
            expiration_date=expired_date,
            milestone="End of Standard Vendor Support",
        ),
        ExpirationRecord(
            source_section="Active",
            name="Future component",
            expiration_date=active_date,
            milestone="",
        ),
    ]

    payload = build_expiration_workbook(records)

    workbook = load_workbook(filename=BytesIO(payload))
    sheet = workbook.active

    expired_fill = sheet["A2"].fill.fgColor.rgb
    active_fill = sheet["A3"].fill.fgColor.rgb

    assert expired_fill == "00F6E7A1"
    assert sheet["B2"].fill.fgColor.rgb == "00F6E7A1"
    assert sheet["C2"].fill.fgColor.rgb == "00F6E7A1"
    assert sheet["D2"].fill.fgColor.rgb == "00F6E7A1"
    assert active_fill == "00CFE8C6"
    assert sheet["B3"].fill.fgColor.rgb == "00CFE8C6"
    assert sheet["C3"].fill.fgColor.rgb == "00CFE8C6"
    assert sheet["D3"].fill.fgColor.rgb == "00CFE8C6"
