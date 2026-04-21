# Backend Vencimientos SAP EWA

Componente FastAPI del proyecto `vencimientos-sap`.

## Desarrollo

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -e ".[dev]"
python -m pytest
python -m uvicorn app.main:app --reload
```

## OCR opcional

Para activar el fallback OCR con Tesseract en PDFs con poco texto o documentos Word con imagenes embebidas:

```bash
python -m pip install -e ".[ocr]"
```

Ademas, es necesario tener instalado el binario de Tesseract OCR en el equipo. Si no queda en `PATH`, se puede configurar con la variable `TESSERACT_CMD`.
