# Vencimientos SAP EWA

Servicio FastAPI orientado a documentos SAP EarlyWatch Alert en PDF para detectar vencimientos mediante extraccion de texto + document intelligence y exportarlos a Excel.

## Flujo

`PDF -> extraccion estructurada (layout + tablas) -> IA/document intelligence -> normalizacion -> Excel`

## Estructura

- `backend/app/api/`: endpoint HTTP.
- `backend/app/parsers/`: extraccion estructurada desde PDF con `pdfplumber`.
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
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -e ".[dev]"
```

2. Ejecutar pruebas:

```bash
cd backend
source .venv/Scripts/activate
python -m pytest
```

3. Levantar API:

```bash
cd backend
source .venv/Scripts/activate
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
cp .env.example backend/.env
```

Completar en tu entorno o shell estas variables:

- `EWA_AI_PROVIDER=azure-openai`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`

## Endpoint

- `POST /ewa/analyze`
- Alias de deploy Vercel: `POST /api/ewa/analyze`
- Input principal: archivo `.pdf` con texto extraible
- Output: archivo Excel `.xlsx` descargable con columnas `Seccion`, `Nombre`, `Hito` y `Fecha`

## Frontend

- UI Vue 3 standalone con Vite.
- En desarrollo consume `VITE_API_BASE_URL=/api` por defecto y Vite proxyea `/api` hacia `http://127.0.0.1:8000`.
- Flujo principal: seleccionar archivo, enviar, recibir Excel y disparar descarga.

## Deploy en Vercel

- El monorepo se despliega con `Services` y `vercel.json` en la raiz.
- `frontend` se publica en `/`.
- `backend` se publica bajo `/api`.
- El backend mantiene `POST /ewa/analyze` como endpoint principal y expone `POST /api/ewa/analyze` como alias compatible para Vercel.

Pruebas frontend:

```bash
cd frontend
npm test
```

La API carga `.env` desde `backend/.env` y tambien tolera ejecuciones que definan variables en el entorno del proceso.

## CI

- El repositorio incluye GitHub Actions en [`.github/workflows/ci.yml`](/Users/facusada/Documents/projects/vencimientos-app/vencimientos-sap/.github/workflows/ci.yml:1).
- El job `backend` instala el paquete desde `backend/` y ejecuta `python -m pytest`.
- El job `frontend` ejecuta `npm ci`, `npm test` y `npm run build`.
- En CI el backend fuerza `EWA_AI_PROVIDER=fake` para validar el flujo sin depender de credenciales externas.

## Capa de IA

- El proveedor por defecto es `FakeSemanticDocumentIntelligence`.
- La interfaz esta desacoplada para permitir proveedores futuros como OpenAI o Azure OpenAI.
- La normalizacion de fechas y deduplicacion se realiza fuera del proveedor IA.
- El parser PDF preserva mejor headers y contexto tabular serializando layout y filas de tabla antes de invocar document intelligence.
- La reconciliacion de `Nombre` prioriza nombres especificos ya devueltos por la IA y usa heuristicas locales sobre todo para corregir nombres genericos o ruidosos.
- La columna `Seccion` se resuelve en backend usando el bloque del componente detectado para reducir headings incorrectos como `SAP Kernel Release` en vencimientos de producto.
- La columna `Hito` distingue vencimientos como `End of Standard Vendor Support` y `End of Extended Vendor Support` cuando el documento los explicita.
- Para usar Azure OpenAI real, el proveedor se selecciona por variables de entorno.

## Trazabilidad

- Spec activa backend: `docs/sdd/wip/ewa-expiration-parser/spec.md`
- Spec activa frontend: `docs/sdd/wip/ewa-upload-ui/spec.md`
- Commit sugerido SDD: `feature(ewa-parser): redefinir flujo PDF a IA para analisis EWA`
- Commit sugerido implementacion: `feature(ewa-parser): implementar document intelligence para analisis EWA`
