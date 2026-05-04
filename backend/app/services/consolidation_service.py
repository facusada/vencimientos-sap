from app.models.expiration import AnalyzedEwaDocument
from app.models.expiration import ConsolidatedExpiration
from app.models.expiration import ConsolidatedWorkbookData
from app.models.expiration import EwaAiUsage
from app.models.expiration import EwaWithoutExpirationResults
from app.services.component_catalog import normalize_component_name

NO_EXPIRATION_RESULTS_REASON = "Sin vencimientos detectados"


def consolidate_ewa_documents(documents: list[AnalyzedEwaDocument]) -> ConsolidatedWorkbookData:
    clients: list[tuple[str, str]] = []
    seen_clients: set[tuple[str, str]] = set()
    records: list[ConsolidatedExpiration] = []
    ai_usages: list[EwaAiUsage] = []
    no_result_documents: list[EwaWithoutExpirationResults] = []

    for document in documents:
        client_key = (document.client, document.period)
        if client_key not in seen_clients:
            seen_clients.add(client_key)
            clients.append(client_key)

        ai_usage = document.ai_usage
        ai_usages.append(
            EwaAiUsage(
                client=document.client,
                period=document.period,
                source_filename=document.filename,
                input_tokens=ai_usage.input_tokens if ai_usage else None,
                output_tokens=ai_usage.output_tokens if ai_usage else None,
                total_tokens=ai_usage.total_tokens if ai_usage else None,
            )
        )

        if not document.records:
            no_result_documents.append(
                EwaWithoutExpirationResults(
                    client=document.client,
                    period=document.period,
                    source_filename=document.filename,
                    reason=NO_EXPIRATION_RESULTS_REASON,
                )
            )
            continue

        for record in document.records:
            component_match = normalize_component_name(record.name)
            records.append(
                ConsolidatedExpiration(
                    client=document.client,
                    period=document.period,
                    component=component_match.canonical_name or record.name,
                    detected_name=record.name,
                    milestone=record.milestone,
                    expiration_date=record.expiration_date,
                    source_section=record.source_section,
                    source_filename=document.filename,
                    is_cataloged=component_match.is_cataloged,
                )
            )

    return ConsolidatedWorkbookData(
        clients=clients,
        records=records,
        ai_usages=ai_usages,
        no_result_documents=no_result_documents,
    )
