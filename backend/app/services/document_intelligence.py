from __future__ import annotations

from abc import ABC, abstractmethod
import json
import re

from app.models.expiration import AiUsageMetrics
from app.utils.settings import AppSettings, get_settings


DATE_PATTERN = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2}|\d{2}\.\d{2}\.\d{4}|\d{2}\.\d{4})\b"
)
FULL_DATE_PATTERN = re.compile(r"^(?:\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2}|\d{2}\.\d{2}\.\d{4})$")

SEMANTIC_PHRASES = (
    "valid until",
    "maintenance until",
    "maintenance ends",
    "end of maintenance",
    "supported until",
    "is supported until",
    "expires on",
    "expiry",
    "expiration",
    "end of support",
)

SYSTEM_PROMPT = """You analyze SAP EarlyWatch Alert reports.
Extract every maintenance, expiration, valid-until, support-until, or end-of-maintenance date.
Return JSON only with this shape:
{"items":[{"nombre":"Component name","fecha":"raw date as seen","hito":"End of Standard Vendor Support or End of Extended Vendor Support when present, otherwise empty string"}]}
Infer the most reasonable component name from nearby context when needed.
Return each unique nombre, fecha, and hito combination at most once.
Do not include explanations or markdown fences."""


class DocumentIntelligenceProvider(ABC):
    @abstractmethod
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        """Return raw AI findings with keys `nombre`, `fecha`, and optional `hito`."""

    def extract_expirations_with_usage(
        self,
        text: str,
    ) -> tuple[list[dict[str, str]], AiUsageMetrics | None]:
        return self.extract_expirations(text), None


class FakeSemanticDocumentIntelligence(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        findings: list[dict[str, str]] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for line in lines:
            lowered = line.lower()
            if not any(phrase in lowered for phrase in SEMANTIC_PHRASES):
                continue

            match = DATE_PATTERN.search(line)
            if match is None:
                continue

            name = _infer_component_name(line, match.start())
            if not name:
                continue

            findings.append({"nombre": name, "fecha": match.group(1), "hito": ""})

        findings.extend(_extract_vendor_support_table_findings(lines))
        return _deduplicate_findings(findings)


class OpenAIDocumentIntelligence(DocumentIntelligenceProvider):
    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        raise ValueError("OpenAI provider is not configured for this environment")


class AzureOpenAIDocumentIntelligence(DocumentIntelligenceProvider):
    def __init__(self, settings: AppSettings, client: object | None = None) -> None:
        self._settings = settings
        self._validate_settings()
        self._client = client or self._build_client()

    def extract_expirations(self, text: str) -> list[dict[str, str]]:
        findings, _ = self.extract_expirations_with_usage(text)
        return findings

    def extract_expirations_with_usage(
        self,
        text: str,
    ) -> tuple[list[dict[str, str]], AiUsageMetrics | None]:
        try:
            response = self._client.chat.completions.create(
                model=self._settings.azure_openai_deployment,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(text)},
                ],
            )
        except Exception as exc:
            raise ValueError(f"Azure OpenAI request failed: {exc}") from exc
        raw_content = _extract_response_text(response)
        return _parse_ai_payload(raw_content), _extract_usage_metrics(response)

    def _validate_settings(self) -> None:
        if not self._settings.azure_openai_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is required for Azure OpenAI")
        if not self._settings.azure_openai_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is required for Azure OpenAI")
        if not self._settings.azure_openai_deployment:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT is required for Azure OpenAI")

    def _build_client(self) -> object:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ValueError("OpenAI SDK dependency is not installed") from exc

        endpoint = self._settings.azure_openai_endpoint.rstrip("/")
        base_url = f"{endpoint}/openai/v1/"
        return OpenAI(
            api_key=self._settings.azure_openai_api_key,
            base_url=base_url,
        )


class AzureOpenAIClientAdapter:
    pass


def create_document_intelligence_provider(
    provider_name: str | None = None,
    settings: AppSettings | None = None,
    client: object | None = None,
) -> DocumentIntelligenceProvider:
    resolved_settings = settings or get_settings()
    normalized = (provider_name or resolved_settings.ai_provider).lower()
    if normalized == "fake":
        return FakeSemanticDocumentIntelligence()
    if normalized == "openai":
        return OpenAIDocumentIntelligence()
    if normalized == "azure-openai":
        return AzureOpenAIDocumentIntelligence(resolved_settings, client=client)
    raise ValueError("Unsupported AI provider")


def _infer_component_name(line: str, date_start: int) -> str:
    prefix = line[:date_start].strip(" .:-")
    split_match = re.split(
        r"\b(is supported until|valid until|maintenance until|maintenance ends on|maintenance ends|end of maintenance|supported until|expires on|expiry|expiration|end of support)\b",
        prefix,
        maxsplit=1,
        flags=re.IGNORECASE,
    )

    candidate = split_match[0].strip(" .:-") if split_match else prefix
    if not candidate:
        return ""

    candidate = re.sub(r"\bis$", "", candidate, flags=re.IGNORECASE).strip(" .:-")
    return candidate.strip()


def _extract_vendor_support_table_findings(lines: list[str]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

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

        component_name = lines[cursor]
        date_values = _collect_following_full_dates(lines, cursor + 1, limit=3)
        if component_name and len(date_values) >= 2:
            findings.append(
                {
                    "nombre": component_name,
                    "fecha": date_values[0],
                    "hito": "End of Standard Vendor Support",
                }
            )
            findings.append(
                {
                    "nombre": component_name,
                    "fecha": date_values[1],
                    "hito": "End of Extended Vendor Support",
                }
            )

        operating_system_dates = _extract_following_operating_system_dates(lines, cursor + 1)
        if len(operating_system_dates) >= 1:
            findings.append(
                {
                    "nombre": "Operating System",
                    "fecha": operating_system_dates[0],
                    "hito": "End of Standard Vendor Support",
                }
            )
        if len(operating_system_dates) >= 2:
            findings.append(
                {
                    "nombre": "Operating System",
                    "fecha": operating_system_dates[1],
                    "hito": "End of Extended Vendor Support",
                }
            )

    return findings


def _extract_following_operating_system_dates(lines: list[str], start_index: int) -> list[str]:
    search_limit = min(len(lines), start_index + 24)

    for index in range(start_index, search_limit):
        normalized = lines[index].lower()
        if "operating system version" not in normalized:
            continue

        return _collect_previous_full_dates(lines, index - 1, limit=2)

    return []


def _collect_following_full_dates(lines: list[str], start_index: int, limit: int) -> list[str]:
    dates: list[str] = []
    search_limit = min(len(lines), start_index + 12)

    for index in range(start_index, search_limit):
        candidate = lines[index]
        if FULL_DATE_PATTERN.fullmatch(candidate):
            dates.append(candidate)
            if len(dates) == limit:
                break

    return dates


def _collect_previous_full_dates(lines: list[str], start_index: int, limit: int) -> list[str]:
    dates: list[str] = []
    search_start = max(0, start_index - 8)

    for index in range(start_index, search_start - 1, -1):
        candidate = lines[index]
        if FULL_DATE_PATTERN.fullmatch(candidate):
            dates.append(candidate)
            if len(dates) == limit:
                break

    return list(reversed(dates))


def _deduplicate_findings(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    deduplicated: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for finding in findings:
        key = (
            finding.get("nombre", "").strip(),
            finding.get("fecha", "").strip(),
            finding.get("hito", "").strip(),
        )
        if not key[0] or not key[1] or key in seen:
            continue

        seen.add(key)
        deduplicated.append({"nombre": key[0], "fecha": key[1], "hito": key[2]})

    return deduplicated


def _build_user_prompt(text: str) -> str:
    return (
        "Extract all SAP EWA maintenance or expiration dates from the document below.\n"
        "Use only component names that appear in the document text.\n"
        "Do not use instruction text, prompt text, or generic placeholders as component names.\n"
        "Ignore analysis windows, SQL statement dates, collection periods, CPU peak hours, and operational telemetry dates.\n"
        "If a date is present but no component can be identified from nearby document context, omit that item.\n"
        "When the document distinguishes End of Standard Vendor Support and End of Extended Vendor Support, set hito accordingly.\n"
        "Keep raw dates exactly as found.\n\n"
        "BEGIN_DOCUMENT\n"
        f"{text}\n"
        "END_DOCUMENT"
    )


def _extract_response_text(response: object) -> str:
    try:
        return response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise ValueError("Azure OpenAI response is not in the expected format") from exc


def _extract_usage_metrics(response: object) -> AiUsageMetrics | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    input_tokens = _coerce_usage_value(getattr(usage, "prompt_tokens", None))
    output_tokens = _coerce_usage_value(getattr(usage, "completion_tokens", None))
    total_tokens = _coerce_usage_value(getattr(usage, "total_tokens", None))
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None

    return AiUsageMetrics(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _coerce_usage_value(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _parse_ai_payload(content: str) -> list[dict[str, str]]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL).strip()

    json_candidate = _extract_json_object(cleaned)
    if json_candidate is not None:
        cleaned = json_candidate

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        recovered_items = _extract_complete_items_from_partial_json(cleaned)
        if recovered_items:
            return _normalize_ai_items(recovered_items)
        raise ValueError("Azure OpenAI response is not valid JSON") from exc

    items = payload.get("items", [])
    if not isinstance(items, list):
        raise ValueError("Azure OpenAI response does not contain a valid items list")

    return _normalize_ai_items(items)


def _normalize_ai_items(items: list[object]) -> list[dict[str, str]]:
    normalized_items: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre", "")).strip()
        fecha = str(item.get("fecha", "")).strip()
        hito = str(item.get("hito", "")).strip()
        if nombre and fecha:
            normalized_items.append({"nombre": nombre, "fecha": fecha, "hito": hito})

    return _deduplicate_findings(normalized_items)


def _extract_complete_items_from_partial_json(content: str) -> list[object]:
    items_key_index = content.find('"items"')
    if items_key_index == -1:
        return []

    array_start = content.find("[", items_key_index)
    if array_start == -1:
        return []

    decoder = json.JSONDecoder()
    cursor = array_start + 1
    items: list[object] = []

    while cursor < len(content):
        while cursor < len(content) and content[cursor] in " \n\r\t,":
            cursor += 1

        if cursor >= len(content) or content[cursor] == "]":
            break
        if content[cursor] != "{":
            cursor += 1
            continue

        try:
            item, cursor = decoder.raw_decode(content, cursor)
        except json.JSONDecodeError:
            break

        items.append(item)

    return items


def _extract_json_object(content: str) -> str | None:
    start = content.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(content)):
        char = content[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]

    return None
