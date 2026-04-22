from collections.abc import Iterable
import re

from app.models.expiration import ExpirationRecord
from app.models.expiration import RawExpirationFinding
from app.services.document_intelligence import _infer_component_name
from app.parsers.text_extractor import extract_text
from app.services.document_intelligence import (
    DocumentIntelligenceProvider,
    create_document_intelligence_provider,
)
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
SECTION_HEADING_HINTS = (
    "maintenance phases",
    "maintenance status",
    "sap kernel release",
    "certificates",
)


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


def build_expiration_records(
    text: str,
    provider: DocumentIntelligenceProvider,
) -> list[ExpirationRecord]:
    raw_items = provider.extract_expirations(text)
    findings = _coerce_raw_findings(raw_items)
    deduplicated: list[ExpirationRecord] = []
    seen: set[tuple[str, str]] = set()

    for finding in findings:
        resolved_name = _resolve_finding_name(text, finding)
        resolved_section = _resolve_finding_section(text, finding.raw_date)
        normalized = normalize_date(finding.raw_date)
        if normalized is None:
            continue
        if not _should_export_finding(text, finding, resolved_name):
            continue

        key = (resolved_name, normalized.isoformat())
        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(
            ExpirationRecord(
                source_section=resolved_section,
                name=resolved_name,
                expiration_date=normalized.isoformat(),
            )
        )

    return deduplicated


def _coerce_raw_findings(raw_items: Iterable[dict[str, str]]) -> list[RawExpirationFinding]:
    findings: list[RawExpirationFinding] = []

    for item in raw_items:
        name = item.get("nombre", "").strip()
        raw_date = item.get("fecha", "").strip()
        if not name or not raw_date:
            continue

        findings.append(RawExpirationFinding(name=name, raw_date=raw_date))

    return findings


def _resolve_finding_name(text: str, finding: RawExpirationFinding) -> str:
    suggested_name = finding.name.strip()
    candidates = _find_source_candidates(
        text,
        finding.raw_date,
        allow_forward_lookup=_is_generic_component_name(suggested_name),
    )

    matched_candidate = _match_source_candidate(suggested_name, candidates)
    if matched_candidate:
        return matched_candidate

    if (
        suggested_name
        and suggested_name in text
        and not _is_generic_component_name(suggested_name)
        and _is_component_like_name(suggested_name)
        and not _is_invalid_candidate_name(suggested_name)
    ):
        return suggested_name

    inferred_name = _infer_name_from_source_text(text, finding.raw_date)
    if inferred_name:
        return inferred_name

    return suggested_name


def _infer_name_from_source_text(text: str, raw_date: str) -> str:
    for line in text.splitlines():
        stripped_line = line.strip()
        if not stripped_line or raw_date not in stripped_line:
            continue

        inferred_name = _infer_component_name(stripped_line, stripped_line.index(raw_date)).strip()
        if inferred_name:
            return inferred_name

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
    )
    return bool(re.fullmatch(r"\d+|[\d.\-]+|\d+\s+hosts?", normalized)) or any(
        hint in normalized for hint in invalid_sentence_hints
    )


def _should_export_finding(text: str, finding: RawExpirationFinding, resolved_name: str) -> bool:
    contexts = _collect_context_windows(text, finding.raw_date)
    if not contexts:
        return True

    if any(_is_noise_context(window) for window in contexts) and not any(
        _has_support_context(window) for window in contexts
    ):
        return False

    if resolved_name and not _is_generic_component_name(resolved_name):
        return True

    return any(_has_support_context(window) for window in contexts)


def _collect_context_windows(text: str, raw_date: str) -> list[list[str]]:
    lines = [line.strip() for line in text.splitlines()]
    windows: list[list[str]] = []

    for index, line in enumerate(lines):
        if raw_date not in line:
            continue

        start = max(0, index - 5)
        end = min(len(lines), index + 6)
        windows.append([candidate for candidate in lines[start:end] if candidate])

    return windows


def _resolve_finding_section(text: str, raw_date: str) -> str:
    lines = [line.strip() for line in text.splitlines()]

    for index, line in enumerate(lines):
        if raw_date not in line:
            continue

        window = [candidate for candidate in lines[max(0, index - 5) : index + 6] if candidate]
        vendor_support_context = _has_vendor_support_context(window)

        for lookback_index in range(index - 1, -1, -1):
            candidate = lines[lookback_index].strip()
            if not candidate:
                continue
            if vendor_support_context and candidate.lower() == "sap kernel release":
                continue
            if _is_section_heading(candidate):
                return candidate

    return ""


def _has_support_context(window: list[str]) -> bool:
    normalized_window = " ".join(window).lower()
    return any(hint in normalized_window for hint in SUPPORT_CONTEXT_HINTS)


def _is_noise_context(window: list[str]) -> bool:
    normalized_window = " ".join(window).lower()
    return any(hint in normalized_window for hint in NOISE_CONTEXT_HINTS)


def _has_vendor_support_context(window: list[str]) -> bool:
    normalized_window = " ".join(window).lower()
    vendor_support_hints = (
        "end of standard vendor support",
        "end of extended vendor support",
        "database version has already ended",
        "operating system version",
    )
    return any(hint in normalized_window for hint in vendor_support_hints)


def _is_section_heading(line: str) -> bool:
    normalized = line.strip().lower()
    if normalized.startswith("* "):
        return False
    if normalized.endswith(" - maintenance phases"):
        return True
    if normalized.endswith(" - maintenance status"):
        return True
    if "support package stack for" in normalized:
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
