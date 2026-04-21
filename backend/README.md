# Backend Vencimientos SAP EWA

Componente FastAPI del proyecto `vencimientos-sap`.

## Desarrollo

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
python -m uvicorn app.main:app --reload
```
