# Vencimientos SAP EWA

Servicio FastAPI orientado a documentos Word SAP EarlyWatch Alert para detectar vencimientos mediante una capa de document intelligence y exportarlos a Excel.

## Flujo

`Word (.docx / .doc) -> extraccion de texto -> IA/document intelligence -> normalizacion -> Excel`

## Estructura

- `backend/app/api/`: endpoint HTTP.
- `backend/app/parsers/`: extraccion de texto desde Word.
- `backend/app/services/document_intelligence.py`: interfaz y proveedores de IA.
- `backend/app/services/ewa_analysis_service.py`: orquestacion del flujo.
- `backend/app/services/excel_service.py`: exportacion Excel.
- `backend/app/models/`: contratos de dominio.
- `backend/app/utils/`: utilidades de normalizacion.
- `backend/tests/`: pruebas unitarias e integracion del backend.
- `backend/pyproject.toml`: configuracion del paquete y tooling Python.
- `frontend/`: interfaz Vue 3 para carga de EWAs y descarga del Excel.
- `docs/`: especificaciones SDD y arquitectura del proyecto.

## Desarrollo

1. Instalar dependencias:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

2. Ejecutar pruebas:

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

3. Levantar API:

```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

4. Levantar frontend:

```bash
cd frontend
npm install
npm run dev
```

5. Configurar Azure OpenAI:

```bash
cp .env.example .env
```

Completar en tu entorno o shell estas variables:

- `EWA_AI_PROVIDER=azure-openai`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`

## Endpoint

- `POST /ewa/analyze`
- Input principal: archivo `.docx` o `.doc`
- Output: archivo Excel `.xlsx` descargable con columnas `Seccion`, `Nombre` y `Fecha`

## Frontend

- UI Vue 3 standalone con Vite.
- Proxy local hacia `http://127.0.0.1:8000` para el endpoint `/ewa/analyze`.
- Flujo principal: seleccionar archivo, enviar, recibir Excel y disparar descarga.

Pruebas frontend:

```bash
cd frontend
npm test
```

La API carga `.env` tanto desde la raiz del repo como desde `backend/.env`.

## Capa de IA

- El proveedor por defecto es `FakeSemanticDocumentIntelligence`.
- La interfaz esta desacoplada para permitir proveedores futuros como OpenAI o Azure OpenAI.
- La normalizacion de fechas y deduplicacion se realiza fuera del proveedor IA.
- Para usar Azure OpenAI real, el proveedor se selecciona por variables de entorno.

## Nota sobre Word legado

- Los archivos `.doc` en formato Word 2003 XML se parsean directamente sin conversion externa.
- En Windows, los archivos `.doc` se convierten usando Microsoft Word.
- En macOS/Linux, los archivos `.doc` se convierten usando LibreOffice en modo headless.
- Si el equipo donde corre la API no tiene disponible el conversor correspondiente, el endpoint responde `400`.

## Trazabilidad

- Spec activa backend: `docs/sdd/wip/ewa-expiration-parser/spec.md`
- Spec activa frontend: `docs/sdd/wip/ewa-upload-ui/spec.md`
- Commit sugerido SDD: `feature(ewa-parser): redefinir flujo Word a IA para analisis EWA`
- Commit sugerido implementacion: `feature(ewa-parser): implementar document intelligence para analisis EWA`
