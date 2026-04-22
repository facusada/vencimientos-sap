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

El backend procesa exclusivamente archivos `.pdf` con texto extraible y usa `pdfplumber` para preservar layout y tablas antes de invocar la capa de document intelligence.
