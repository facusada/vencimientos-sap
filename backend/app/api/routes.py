import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.models.expiration import EwaWithoutExpirationResults
from app.services.ai_usage_repository import AiUsageRepository
from app.services.ai_usage_repository import get_ai_usage_repository
from app.services.document_intelligence import DocumentIntelligenceProvider
from app.services.ewa_analysis_service import (
    analyze_ewa_file,
    analyze_ewa_files_for_consolidation,
    get_document_intelligence_provider,
)


router = APIRouter()


@router.post("/ewa/analyze")
@router.post("/api/ewa/analyze", include_in_schema=False)
async def analyze_ewa(
    file: UploadFile = File(...),
    provider: DocumentIntelligenceProvider = Depends(get_document_intelligence_provider),
) -> Response:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    try:
        payload = await file.read()
        workbook = analyze_ewa_file(file.filename, payload, provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    headers = {"Content-Disposition": "attachment; filename=ewa-expirations.xlsx"}
    return Response(
        content=workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/ewa/consolidate")
@router.post("/api/ewa/consolidate", include_in_schema=False)
async def consolidate_ewa(
    period: str = Form(...),
    clients: list[str] = Form(...),
    files: list[UploadFile] = File(...),
    provider: DocumentIntelligenceProvider = Depends(get_document_intelligence_provider),
    usage_repository: AiUsageRepository = Depends(get_ai_usage_repository),
) -> Response:
    file_payloads: list[tuple[str, bytes]] = []
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        file_payloads.append((file.filename, await file.read()))

    try:
        result = analyze_ewa_files_for_consolidation(
            file_payloads,
            clients,
            period,
            provider,
            usage_repository,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    headers = {"Content-Disposition": "attachment; filename=ewa-consolidated.xlsx"}
    if result.no_result_documents:
        headers["X-EWA-No-Results"] = _serialize_no_result_documents(result.no_result_documents)
    return Response(
        content=result.workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


def _serialize_no_result_documents(documents: list[EwaWithoutExpirationResults]) -> str:
    return json.dumps(
        [
            {
                "client": document.client,
                "period": document.period,
                "filename": document.source_filename,
                "reason": document.reason,
            }
            for document in documents
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    )
