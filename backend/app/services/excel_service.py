from io import BytesIO
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from app.models.expiration import ConsolidatedWorkbookData
from app.models.expiration import ExpirationRecord
from app.services.component_catalog import DEFAULT_COMPONENT_COLUMNS
from app.services.component_catalog import OTHER_COMPONENTS_COLUMN

EXPIRED_FILL = PatternFill(fill_type="solid", fgColor="F6E7A1")
ACTIVE_FILL = PatternFill(fill_type="solid", fgColor="CFE8C6")
BODY_FONT = Font(color="1C1B18")
HEADER_FONT = Font(bold=True, color="1C1B18")


def build_expiration_workbook(records: list[ExpirationRecord]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Expirations"
    sheet.append(["Seccion", "Nombre", "Hito", "Fecha"])

    for record in records:
        sheet.append([record.source_section, record.name, record.milestone, record.expiration_date])
        _apply_status_style(sheet, sheet.max_row, record.expiration_date)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_consolidated_workbook(data: ConsolidatedWorkbookData) -> bytes:
    workbook = Workbook()
    base_sheet = workbook.active
    base_sheet.title = "Base"
    _build_base_sheet(base_sheet, data)
    _build_client_view_sheet(workbook.create_sheet("VistaClientes"), data)
    _build_uncataloged_sheet(workbook.create_sheet("ComponentesNoCatalogados"), data)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _build_base_sheet(sheet, data: ConsolidatedWorkbookData) -> None:
    sheet.append(["Cliente", "Componente", "FechaVencimiento"])
    _style_header(sheet, 3)

    for record in data.records:
        sheet.append(
            [
                record.client,
                record.component,
                record.expiration_date,
            ]
        )
        _apply_status_style(sheet, sheet.max_row, record.expiration_date, columns=("A", "B", "C"))


def _build_client_view_sheet(sheet, data: ConsolidatedWorkbookData) -> None:
    headers = ["Cliente", "Periodo", *DEFAULT_COMPONENT_COLUMNS, OTHER_COMPONENTS_COLUMN]
    sheet.append(headers)
    _style_header(sheet, len(headers))

    values_by_client = _group_client_view_values(data)
    for client, period in data.clients:
        component_values = values_by_client.get((client, period), {})
        sheet.append(
            [
                client,
                period,
                *[component_values.get(component, "") for component in DEFAULT_COMPONENT_COLUMNS],
                component_values.get(OTHER_COMPONENTS_COLUMN, ""),
            ]
        )


def _build_uncataloged_sheet(sheet, data: ConsolidatedWorkbookData) -> None:
    sheet.append(["NombreDetectado", "Cliente", "Periodo", "FechaVencimiento", "FuenteEWA"])
    _style_header(sheet, 5)

    for record in data.records:
        if record.is_cataloged:
            continue
        sheet.append(
            [
                record.detected_name,
                record.client,
                record.period,
                record.expiration_date,
                record.source_filename,
            ]
        )


def _group_client_view_values(data: ConsolidatedWorkbookData) -> dict[tuple[str, str], dict[str, str]]:
    grouped: dict[tuple[str, str], dict[str, list[str]]] = {}

    for record in data.records:
        client_key = (record.client, record.period)
        if record.component in DEFAULT_COMPONENT_COLUMNS:
            component_values = grouped.setdefault(client_key, {}).setdefault(record.component, [])
            display_value = _format_client_view_value(record.expiration_date, record.milestone)
            if display_value not in component_values:
                component_values.append(display_value)
            continue

        component_values = grouped.setdefault(client_key, {}).setdefault(OTHER_COMPONENTS_COLUMN, [])
        display_value = _format_other_component_value(record.component, record.expiration_date, record.milestone)
        if display_value not in component_values:
            component_values.append(display_value)

    return {
        client_key: {
            component: "; ".join(values)
            for component, values in component_values.items()
        }
        for client_key, component_values in grouped.items()
    }


def _format_client_view_value(expiration_date: str, milestone: str) -> str:
    if milestone:
        return f"{expiration_date} ({milestone})"
    return expiration_date


def _format_other_component_value(component: str, expiration_date: str, milestone: str) -> str:
    return f"{component}: {_format_client_view_value(expiration_date, milestone)}"


def _style_header(sheet, columns_count: int) -> None:
    for column_index in range(1, columns_count + 1):
        sheet.cell(row=1, column=column_index).font = HEADER_FONT


def _apply_status_style(
    sheet,
    row_index: int,
    expiration_date: str,
    columns: tuple[str, ...] = ("A", "B", "C", "D"),
) -> None:
    target_fill = _resolve_fill(expiration_date)

    for column in columns:
        cell = sheet[f"{column}{row_index}"]
        cell.fill = target_fill
        cell.font = BODY_FONT


def _resolve_fill(expiration_date: str) -> PatternFill:
    try:
        normalized_date = date.fromisoformat(expiration_date)
    except ValueError:
        return ACTIVE_FILL

    return EXPIRED_FILL if normalized_date < date.today() else ACTIVE_FILL
