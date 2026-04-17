from io import BytesIO

from openpyxl import Workbook

from app.models.expiration import ExpirationRecord


def build_expiration_workbook(records: list[ExpirationRecord]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Expirations"
    sheet.append(["Nombre", "Fecha"])

    for record in records:
        sheet.append([record.name, record.expiration_date])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
