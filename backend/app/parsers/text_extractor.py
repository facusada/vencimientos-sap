from __future__ import annotations

from io import BytesIO
import re


def extract_text(filename: str, payload: bytes) -> str:
    suffix = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""

    if suffix == "pdf":
        return _extract_pdf_text(payload)

    raise ValueError("Unsupported file type")


def _extract_pdf_text(payload: bytes) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ValueError("PDF processing dependency is not installed") from exc

    lines: list[str] = []
    seen: set[str] = set()

    with pdfplumber.open(BytesIO(payload)) as pdf:
        # Hard rule: ignore the first page of every EWA.
        for page in pdf.pages[1:]:
            _append_unique_lines(lines, seen, _extract_page_layout_lines(page))
            _append_unique_lines(lines, seen, _extract_page_table_lines(page))

    content = "\n".join(lines).strip()
    if not content:
        raise ValueError("PDF does not contain extractable text")
    return content


def _extract_page_layout_lines(page: object) -> list[str]:
    try:
        plain_text = page.extract_text() or ""
    except TypeError:
        plain_text = ""

    if plain_text.strip():
        return _normalize_multiline_text(plain_text)

    try:
        layout_text = page.extract_text(layout=True) or ""
    except TypeError:
        layout_text = ""

    return _normalize_multiline_text(layout_text)


def _extract_page_table_lines(page: object) -> list[str]:
    table_lines: list[str] = []

    for table in page.extract_tables() or []:
        for row in table or []:
            normalized_cells = [_normalize_table_cell(cell) for cell in row or []]
            if not any(normalized_cells):
                continue
            serialized_row = " | ".join(normalized_cells).strip(" |")
            if serialized_row:
                table_lines.append(serialized_row)

    return table_lines


def _append_unique_lines(target: list[str], seen: set[str], new_lines: list[str]) -> None:
    for line in new_lines:
        normalized_key = _normalize_dedup_key(line)
        if not normalized_key or normalized_key in seen:
            continue
        seen.add(normalized_key)
        target.append(line)


def _normalize_multiline_text(text: str) -> list[str]:
    normalized_lines: list[str] = []

    for line in text.splitlines():
        normalized = _normalize_table_cell(line)
        if normalized:
            normalized_lines.append(normalized)

    return normalized_lines


def _normalize_table_cell(value: object) -> str:
    text = str(value or "").replace("\n", " ").strip()
    return re.sub(r"\s+", " ", text)


def _normalize_dedup_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()
