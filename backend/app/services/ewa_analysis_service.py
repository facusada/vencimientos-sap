from collections.abc import Iterable
import re

from app.models.expiration import AnalyzedEwaDocument
from app.models.expiration import ConsolidatedAnalysisResult
from app.models.expiration import ExpirationRecord
from app.models.expiration import RawExpirationFinding
from app.services.document_intelligence import _collect_following_full_dates
from app.services.document_intelligence import _extract_following_operating_system_dates
from app.services.document_intelligence import _infer_component_name
from app.parsers.text_extractor import extract_text
from app.services.document_intelligence import (
    DocumentIntelligenceProvider,
    create_document_intelligence_provider,
)
from app.services.consolidation_service import consolidate_ewa_documents
from app.services.excel_service import build_consolidated_workbook
from app.services.excel_service import build_expiration_workbook
from app.utils.dates import normalize_date
from app.utils.settings import get_settings

HEADER_HINTS = {
    "sap product version",
    "sap netweaver version",
    "database version",
    "operating system",
    "support package stack",
    "maintenance end",
    "current version",
    "available version",
    "current support package stack",
    "available support package stack",
    "number of days until maintenance end",
    "end of mainstream maintenance",
    "end of standard vendor support",
    "end of extended vendor support",
    "status",
    "comment",
    "sap note",
    "host",
    "instance(s)",
    "sap kernel release",
    "patch level",
    "age in months",
    "os family",
    "first day",
    "last day",
    "analysis type",
    "data source",
}
GENERIC_NAME_HINTS = (
    "your ",
    "main product version",
    "netweaver version",
    "database version",
    "operating system",
)
SUPPORT_CONTEXT_HINTS = (
    "maintenance",
    "support",
    "vendor support",
    "mainstream maintenance",
    "security maintenance",
    "support package stack",
    "support package has run out of security maintenance",
    "end of standard vendor support",
    "end of extended vendor support",
    "end of mainstream maintenance",
)
EXPIRATION_CONTEXT_HINTS = (
    "maintenance end",
    "end of standard vendor support",
    "end of extended vendor support",
    "end of mainstream maintenance",
    "supported until",
    "valid until",
    "expires on",
    "end of support",
    "runs out of maintenance",
    "run out of security maintenance",
)
NOISE_CONTEXT_HINTS = (
    "analysis type",
    "analysis of thread samples",
    "data source",
    "first day",
    "last day",
    "maximal cpu consumption",
    "maximal memory consumption",
    "statement history",
    "top statements",
    "time consumption",
    "memory consumption",
    "origin of sql statement",
    "thread samples",
    "analysis of where clause",
    "running id",
    "data collection",
    "hour of maximal cpu",
)
OPERATIONAL_DATE_CONTEXT_HINTS = (
    "release date",
    "deployment date",
    "age of deployment date",
    "finalassembly date",
    "final assembly date",
    "ageoffinal assembly date",
    "support package importdate",
    "support package import date",
    "ageofsp importdate",
    "hana update information",
    "date version",
    "date | version",
)
SECTION_HEADING_HINTS = (
    "maintenance phases",
    "maintenance status",
    "sap kernel release",
    "certificates",
)
PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
STANDARD_VENDOR_SUPPORT = "End of Standard Vendor Support"
EXTENDED_VENDOR_SUPPORT = "End of Extended Vendor Support"


def get_document_intelligence_provider() -> DocumentIntelligenceProvider:
    return create_document_intelligence_provider(settings=get_settings())


def analyze_ewa_file(
    filename: str,
    payload: bytes,
    provider: DocumentIntelligenceProvider | None = None,
) -> bytes:
    content = extract_text(filename, payload)
    records = build_expiration_records(content, provider or get_document_intelligence_provider())
    if not records:
        raise ValueError("No se detectaron fechas de vencimiento en el EWA enviado.")
    return build_expiration_workbook(records)


def analyze_ewa_files_for_consolidation(
    files: list[tuple[str, bytes]],
    clients: list[str],
    period: str,
    provider: DocumentIntelligenceProvider | None = None,
) -> ConsolidatedAnalysisResult:
    _validate_consolidation_inputs(files, clients, period)
    resolved_provider = provider or get_document_intelligence_provider()
    documents: list[AnalyzedEwaDocument] = []

    for (filename, payload), client in zip(files, clients, strict=True):
        content = extract_text(filename, payload)
        documents.append(
            AnalyzedEwaDocument(
                client=client.strip(),
                period=period,
                filename=filename,
                records=build_expiration_records(content, resolved_provider),
            )
        )

    consolidated_data = consolidate_ewa_documents(documents)
    return ConsolidatedAnalysisResult(
        workbook=build_consolidated_workbook(consolidated_data),
        no_result_documents=consolidated_data.no_result_documents,
    )


def _validate_consolidation_inputs(files: list[tuple[str, bytes]], clients: list[str], period: str) -> None:
    if not files:
        raise ValueError("Debe enviar al menos un archivo EWA.")
    if len(files) != len(clients):
        raise ValueError("La cantidad de clientes debe coincidir con la cantidad de archivos.")
    if not PERIOD_PATTERN.match(period):
        raise ValueError("El periodo debe tener formato YYYY-MM.")
    if any(not client.strip() for client in clients):
        raise ValueError("Cada archivo debe tener un cliente asociado.")


def build_expiration_records(
    text: str,
    provider: DocumentIntelligenceProvider,
) -> list[ExpirationRecord]:
    raw_items = provider.extract_expirations(text)
    findings = _coerce_raw_findings(raw_items)
    deduplicated: list[ExpirationRecord] = []
    seen: set[tuple[str, str, str]] = set()

    for finding in findings:
        normalized = normalize_date(finding.raw_date)
        if normalized is None:
            continue

        key = (finding.name, normalized.isoformat(), finding.milestone)
        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(
            ExpirationRecord(
                source_section=_resolve_finding_section(text, finding.raw_date, finding.name),
                name=finding.name,
                expiration_date=normalized.isoformat(),
                milestone=finding.milestone,
            )
        )

    return _prefer_extended_vendor_support(deduplicated)


def _prefer_extended_vendor_support(records: list[ExpirationRecord]) -> list[ExpirationRecord]:
    preferred_keys = {
        (record.source_section, record.name)
        for record in records
        if record.milestone == EXTENDED_VENDOR_SUPPORT
    }

    if not preferred_keys:
        return records

    filtered: list[ExpirationRecord] = []
    for record in records:
        if (
            record.milestone == STANDARD_VENDOR_SUPPORT
            and (record.source_section, record.name) in preferred_keys
        ):
            continue
        filtered.append(record)

    return filtered


def _coerce_raw_findings(raw_items: Iterable[dict[str, str]]) -> list[RawExpirationFinding]:
    findings: list[RawExpirationFinding] = []

    for item in raw_items:
        name = item.get("nombre", "").strip()
        raw_date = item.get("fecha", "").strip()
        milestone = item.get("hito", "").strip()
        if not name or not raw_date:
            continue

        findings.append(RawExpirationFinding(name=name, raw_date=raw_date, milestone=milestone))

    return findings


def _resolve_finding_name(text: str, finding: RawExpirationFinding) -> str:
    suggested_name = finding.name.strip()
    if _should_preserve_suggested_name(suggested_name):
        return suggested_name

    candidates = _find_source_candidates(
        text,
        finding.raw_date,
        allow_forward_lookup=_is_generic_component_name(suggested_name),
    )

    matched_candidate = _match_source_candidate(suggested_name, candidates)
    if matched_candidate:
        return matched_candidate

    inferred_name = _infer_name_from_source_text(text, finding.raw_date)
    if (
        suggested_name
        and suggested_name in text
        and not _is_generic_component_name(suggested_name)
        and _is_component_like_name(suggested_name)
        and not _is_invalid_candidate_name(suggested_name)
    ):
        return suggested_name

    if inferred_name:
        return inferred_name

    return suggested_name


def _infer_name_from_source_text(text: str, raw_date: str) -> str:
    for line in text.splitlines():
        stripped_line = line.strip()
        if not stripped_line or raw_date not in stripped_line:
            continue

        if "|" in stripped_line:
            inferred_table_name = _infer_component_name_from_table_row(stripped_line, raw_date)
            if inferred_table_name:
                return inferred_table_name

        inferred_name = _infer_component_name(stripped_line, stripped_line.index(raw_date)).strip()
        if inferred_name:
            return inferred_name

    return ""


def _infer_component_name_from_table_row(line: str, raw_date: str) -> str:
    cells = [cell.strip(" .:-") for cell in line.split("|")]
    if raw_date not in cells:
        return ""

    date_index = cells.index(raw_date)
    if date_index <= 0:
        return ""

    for candidate in reversed(cells[:date_index]):
        if (
            not candidate
            or _looks_like_date(candidate)
            or _is_header_like(candidate)
            or _is_invalid_candidate_name(candidate)
            or re.search(r"\d+\s+hosts?$", candidate.lower())
            or candidate.lower().startswith("srv-")
            or candidate.lower().startswith("host ")
        ):
            continue
        return candidate

    return ""


def _find_source_candidates(
    text: str,
    raw_date: str,
    allow_forward_lookup: bool = False,
) -> list[tuple[str, str]]:
    lines = [line.strip() for line in text.splitlines()]
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()

    for index, line in enumerate(lines):
        if raw_date not in line:
            continue

        candidate_name, candidate_index = _find_candidate_name_before_line(lines, index)
        if not candidate_name and allow_forward_lookup:
            candidate_name, candidate_index = _find_candidate_name_after_line(lines, index)
        if not candidate_name or candidate_name in seen:
            continue

        seen.add(candidate_name)
        candidates.append((candidate_name, _find_candidate_context(lines, candidate_index)))

    return candidates


def _find_candidate_name_before_line(lines: list[str], index: int) -> tuple[str, int]:
    for lookback_index in range(index - 1, max(-1, index - 7), -1):
        candidate = lines[lookback_index].strip()
        if (
            not candidate
            or _is_header_like(candidate)
            or _is_section_heading(candidate)
            or _looks_like_date(candidate)
            or _is_invalid_candidate_name(candidate)
        ):
            continue
        return candidate, lookback_index

    return "", -1


def _find_candidate_context(lines: list[str], candidate_index: int) -> str:
    context_lines: list[str] = []

    for lookback_index in range(candidate_index - 1, max(-1, candidate_index - 7), -1):
        candidate = lines[lookback_index].strip()
        if not candidate:
            continue
        if _is_header_like(candidate) or _has_support_context([candidate]):
            context_lines.append(candidate)

    return " ".join(reversed(context_lines))


def _find_candidate_name_after_line(lines: list[str], index: int) -> tuple[str, int]:
    for lookahead_index in range(index + 1, min(len(lines), index + 15)):
        candidate = lines[lookahead_index].strip()
        if (
            not candidate
            or _is_header_like(candidate)
            or _is_section_heading(candidate)
            or _looks_like_date(candidate)
            or _is_invalid_candidate_name(candidate)
        ):
            continue
        return candidate, lookahead_index

    return "", -1


def _match_source_candidate(suggested_name: str, candidates: list[tuple[str, str]]) -> str:
    if not candidates:
        return ""

    scored_candidates: list[tuple[int, int, str]] = []
    suggestion_tokens = _tokenize_name(suggested_name)

    for candidate_name, candidate_context in candidates:
        score = len(suggestion_tokens & _tokenize_name(candidate_name))
        score = max(score, len(suggestion_tokens & _tokenize_name(candidate_context)))

        if "main product version" in suggested_name.lower() and "product version" in candidate_context.lower():
            score += 2
        if "netweaver" in suggested_name.lower() and "netweaver" in candidate_name.lower():
            score += 2
        if any(hint in candidate_context.lower() for hint in SUPPORT_CONTEXT_HINTS):
            score += 1

        scored_candidates.append((score, _structure_score(candidate_name), candidate_name))

    best_score, _, best_candidate = max(scored_candidates, default=(0, 0, ""))
    if best_score > 0 and _is_component_like_name(best_candidate):
        return best_candidate

    if _is_generic_component_name(suggested_name):
        best_structured_candidate = _best_structured_candidate(candidates)
        if best_structured_candidate:
            return best_structured_candidate

    if (
        _is_generic_component_name(suggested_name)
        and len(candidates) == 1
        and _is_component_like_name(candidates[0][0])
        and _has_support_context([candidates[0][1]])
    ):
        return candidates[0][0]

    return ""


def _is_generic_component_name(name: str) -> bool:
    normalized = name.strip().lower()
    return any(hint in normalized for hint in GENERIC_NAME_HINTS)


def _should_preserve_suggested_name(name: str) -> bool:
    normalized = name.strip()
    if not normalized:
        return False
    if _is_generic_component_name(normalized) or _is_invalid_candidate_name(normalized):
        return False

    component_hints = (
        "sap",
        "hana",
        "netweaver",
        "fiori",
        "kernel",
        "linux",
        "windows",
        "server",
        "database",
        "oracle",
        "sql",
        "package",
    )
    lowered = normalized.lower()
    return _is_component_like_name(normalized) and any(hint in lowered for hint in component_hints)


def _is_header_like(line: str) -> bool:
    normalized = line.strip().lower()
    return normalized in HEADER_HINTS


def _looks_like_date(line: str) -> bool:
    return bool(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}|\d{2}\.\d{4}", line.strip()))


def _tokenize_name(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in {"your", "main", "version", "sap", "the", "under", "runs", "supported", "product"}
    }


def _is_invalid_candidate_name(candidate_name: str) -> bool:
    normalized = candidate_name.strip().lower()
    compact = re.sub(r"[^a-z0-9]+", "", normalized)
    invalid_sentence_hints = (
        "offered by sap",
        "will expire in the next",
        "has expired",
        "rating legend",
        "description",
        "standard vendor support",
        "extended vendor support",
        "maintenance phases and duration",
        "operating system version",
        "the following table lists",
        "planned date",
        "for more information",
        "supported until",
        "expires on",
        "valid until",
        "maintenance until",
        "end of support",
        "software product",
        "operating system",
        "vendor support",
        "end of maintenance",
        "end of mainstream maintenance",
        "sap_ui release",
    )
    invalid_exact_values = {"rating", "status", "comment", "support", "end"}
    compact_invalid_hints = {re.sub(r"[^a-z0-9]+", "", hint) for hint in invalid_sentence_hints}
    return (
        bool(re.fullmatch(r"\d+|[\d.\-]+|\d+\s+hosts?", normalized))
        or normalized in invalid_exact_values
        or any(hint in normalized for hint in invalid_sentence_hints)
        or any(hint and hint in compact for hint in compact_invalid_hints)
    )


def _should_export_finding(text: str, finding: RawExpirationFinding, resolved_name: str) -> bool:
    contexts = _collect_context_windows(text, finding.raw_date)
    local_contexts = _collect_context_windows(text, finding.raw_date, lookback=2, lookahead=2)
    if not contexts:
        return True

    has_expiration_context = any(_has_expiration_context(window) for window in local_contexts)
    has_operational_date_context = any(_has_operational_date_context(window) for window in local_contexts)

    if has_operational_date_context and not has_expiration_context:
        return False

    if any(_is_noise_context(window) for window in contexts) and not any(
        _has_support_context(window) for window in contexts
    ):
        return False

    if resolved_name and not _is_generic_component_name(resolved_name):
        return has_expiration_context or not has_operational_date_context

    return has_expiration_context or any(_has_support_context(window) for window in contexts)


def _collect_context_windows(
    text: str,
    raw_date: str,
    lookback: int = 5,
    lookahead: int = 5,
) -> list[list[str]]:
    lines = [line.strip() for line in text.splitlines()]
    windows: list[list[str]] = []

    for index, line in enumerate(lines):
        if raw_date not in line:
            continue

        start = max(0, index - lookback)
        end = min(len(lines), index + lookahead + 1)
        windows.append([candidate for candidate in lines[start:end] if candidate])

    return windows


def _resolve_finding_milestone(
    text: str,
    finding: RawExpirationFinding,
    resolved_name: str,
) -> str:
    if finding.milestone:
        return finding.milestone
    if not resolved_name:
        return ""

    return _resolve_vendor_support_milestone(text, resolved_name, finding.raw_date)


def _resolve_vendor_support_milestone(text: str, resolved_name: str, raw_date: str) -> str:
    lines = [line.strip() for line in text.splitlines()]

    for index, line in enumerate(lines):
        normalized = line.lower()
        if not normalized.startswith("end of standard vendor support"):
            continue

        cursor = index + 1
        while cursor < len(lines) and lines[cursor].lower().startswith("end of extended vendor support"):
            cursor += 1
        if cursor < len(lines) and lines[cursor].lower() == "comment":
            cursor += 1

        if cursor >= len(lines):
            continue

        component_name = lines[cursor].strip()
        date_values = _collect_following_full_dates(lines, cursor + 1, limit=3)
        if component_name == resolved_name:
            if len(date_values) >= 1 and date_values[0] == raw_date:
                return "End of Standard Vendor Support"
            if len(date_values) >= 2 and date_values[1] == raw_date:
                return "End of Extended Vendor Support"

        operating_system_dates = _extract_following_operating_system_dates(lines, cursor + 1)
        if resolved_name != "Operating System":
            continue
        if len(operating_system_dates) >= 1 and operating_system_dates[0] == raw_date:
            return "End of Standard Vendor Support"
        if len(operating_system_dates) >= 2 and operating_system_dates[1] == raw_date:
            return "End of Extended Vendor Support"

    return ""


def _resolve_finding_section(text: str, raw_date: str, resolved_name: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    component_section = _resolve_section_from_component_anchor(lines, raw_date, resolved_name)
    if component_section:
        return component_section

    for index, line in enumerate(lines):
        if raw_date not in line:
            continue

        section = _find_section_heading_for_index(lines, index, resolved_name)
        if section:
            return section

    return ""


def _resolve_section_from_component_anchor(
    lines: list[str],
    raw_date: str,
    resolved_name: str,
) -> str:
    if not resolved_name:
        return ""

    scored_sections: list[tuple[int, str]] = []

    for index, line in enumerate(lines):
        if resolved_name not in line:
            continue

        section = _find_section_heading_for_index(lines, index, resolved_name)
        if not section:
            continue

        window = [candidate for candidate in lines[max(0, index - 5) : min(len(lines), index + 6)] if candidate]
        score = 3
        if raw_date in line:
            score += 4
        if any(raw_date in candidate for candidate in lines[index : min(len(lines), index + 6)]):
            score += 3
        if _has_support_context(window):
            score += 1

        scored_sections.append((score, section))

    if not scored_sections:
        return ""

    return max(scored_sections, key=lambda item: item[0])[1]


def _find_section_heading_for_index(lines: list[str], index: int, resolved_name: str) -> str:
    window = [candidate for candidate in lines[max(0, index - 5) : min(len(lines), index + 6)] if candidate]
    vendor_support_context = _has_vendor_support_context(window)

    for lookback_index in range(index - 1, -1, -1):
        candidate = lines[lookback_index].strip()
        if not candidate:
            continue
        if vendor_support_context and candidate.lower() == "sap kernel release":
            continue
        if not _is_section_heading(candidate):
            continue
        if not _is_section_compatible_with_name(candidate, resolved_name, window):
            continue
        return candidate

    return ""


def _is_section_compatible_with_name(section: str, resolved_name: str, window: list[str]) -> bool:
    normalized_section = section.strip().lower()
    normalized_name = resolved_name.strip().lower()
    normalized_window = " ".join(window).lower()

    if normalized_section == "sap kernel release":
        kernel_hints = ("kernel", "patch level", "downward compatible kernel")
        return any(hint in normalized_name or hint in normalized_window for hint in kernel_hints)

    return True


def _has_support_context(window: list[str]) -> bool:
    return _matches_context_hints(window, SUPPORT_CONTEXT_HINTS)


def _has_expiration_context(window: list[str]) -> bool:
    return _matches_context_hints(window, EXPIRATION_CONTEXT_HINTS)


def _has_operational_date_context(window: list[str]) -> bool:
    return _matches_context_hints(window, OPERATIONAL_DATE_CONTEXT_HINTS)


def _is_noise_context(window: list[str]) -> bool:
    return _matches_context_hints(window, NOISE_CONTEXT_HINTS)


def _has_vendor_support_context(window: list[str]) -> bool:
    vendor_support_hints = (
        "end of standard vendor support",
        "end of extended vendor support",
        "database version has already ended",
        "operating system version",
    )
    return _matches_context_hints(window, vendor_support_hints)


def _matches_context_hints(window: list[str], hints: tuple[str, ...]) -> bool:
    normalized_window = " ".join(window).lower()
    compact_window = re.sub(r"[^a-z0-9]+", "", normalized_window)

    for hint in hints:
        if hint in normalized_window:
            return True
        compact_hint = re.sub(r"[^a-z0-9]+", "", hint.lower())
        if compact_hint and compact_hint in compact_window:
            return True

    return False


def _is_section_heading(line: str) -> bool:
    normalized = line.strip().lower()
    normalized = re.sub(r"^\d+(?:\.\d+)*\s+", "", normalized)
    if normalized.startswith("* "):
        return False
    if normalized.endswith(" - maintenance phases"):
        return True
    if normalized.endswith(" - maintenance status"):
        return True
    if "support package stack for" in normalized and len(normalized.split()) <= 8 and "." not in normalized:
        return True
    if normalized in {"sap kernel release", "certificates"}:
        return True
    return normalized in SECTION_HEADING_HINTS


def _best_structured_candidate(candidates: list[tuple[str, str]]) -> str:
    filtered_candidates = [
        candidate_name
        for candidate_name, _ in candidates
        if _is_component_like_name(candidate_name)
    ]
    if not filtered_candidates:
        return ""

    scored = sorted(
        ((_structure_score(candidate_name), candidate_name) for candidate_name in filtered_candidates),
        reverse=True,
    )
    return scored[0][1] if scored else ""


def _structure_score(candidate_name: str) -> int:
    score = 0
    if re.search(r"\d", candidate_name):
        score += 2
    if candidate_name.upper() == candidate_name:
        score += 2
    if len(candidate_name.split()) <= 8:
        score += 1
    if not any(char in candidate_name for char in ".:;"):
        score += 1
    if "your " not in candidate_name.lower():
        score += 1
    return score


def _is_component_like_name(candidate_name: str) -> bool:
    normalized = candidate_name.lower()
    invalid_hints = (
        "support package stack",
        "maintenance status",
        "analysis of",
        "first day",
        "last day",
        "data source",
        "analysis type",
        "recommendation",
        "offered by sap",
        "will expire in the next",
        "has expired",
        "rating legend",
        "description",
    )
    return not any(hint in normalized for hint in invalid_hints)
