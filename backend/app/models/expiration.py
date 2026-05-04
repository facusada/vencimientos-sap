from dataclasses import dataclass
from dataclasses import field
from datetime import date


@dataclass(slots=True)
class RawExpirationFinding:
    name: str
    raw_date: str
    milestone: str = ""


@dataclass(slots=True)
class ExpirationRecord:
    source_section: str
    name: str
    expiration_date: str
    milestone: str = ""


@dataclass(slots=True)
class ParsedExpiration:
    name: str
    expiration_date: date


@dataclass(slots=True)
class AiUsageMetrics:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(slots=True)
class AnalyzedEwaDocument:
    client: str
    period: str
    filename: str
    records: list[ExpirationRecord]
    ai_usage: AiUsageMetrics | None = None


@dataclass(slots=True)
class ConsolidatedExpiration:
    client: str
    period: str
    component: str
    detected_name: str
    milestone: str
    expiration_date: str
    source_section: str
    source_filename: str
    is_cataloged: bool


@dataclass(slots=True)
class EwaWithoutExpirationResults:
    client: str
    period: str
    source_filename: str
    reason: str


@dataclass(slots=True)
class EwaAiUsage:
    client: str
    period: str
    source_filename: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(slots=True)
class ConsolidatedWorkbookData:
    clients: list[tuple[str, str]]
    records: list[ConsolidatedExpiration]
    ai_usages: list[EwaAiUsage] = field(default_factory=list)
    no_result_documents: list[EwaWithoutExpirationResults] = field(default_factory=list)


@dataclass(slots=True)
class ConsolidatedAnalysisResult:
    workbook: bytes
    no_result_documents: list[EwaWithoutExpirationResults] = field(default_factory=list)
