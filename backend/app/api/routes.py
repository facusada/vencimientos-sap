from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.services.document_intelligence import DocumentIntelligenceProvider
from app.services.ewa_analysis_service import (
    analyze_ewa_file,
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
