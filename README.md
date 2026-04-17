# Vencimientos SAP EWA

Servicio FastAPI orientado a documentos Word SAP EarlyWatch Alert para detectar vencimientos mediante una capa de document intelligence y exportarlos a Excel.

## Flujo

`Word (.docx / .doc) -> extraccion de texto -> IA/document intelligence -> normalizacion -> Excel`

## Estructura

- `app/api/`: endpoint HTTP.
- `app/parsers/`: extraccion de texto desde Word.
- `app/services/document_intelligence.py`: interfaz y proveedores de IA.
- `app/services/ewa_analysis_service.py`: orquestacion del flujo.
- `app/services/excel_service.py`: exportacion Excel.
- `app/models/`: contratos de dominio.
- `app/utils/`: utilidades de normalizacion.
- `tests/unit/`: pruebas unitarias.
- `tests/integration/`: pruebas del endpoint.

## Desarrollo

1. Instalar dependencias:

```bash
python -m pip install -e ".[dev]"
```

2. Ejecutar pruebas:

```bash
python -m pytest
```

3. Levantar API:

```bash
python -m uvicorn app.main:app --reload
```

4. Configurar Azure OpenAI:

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
- Output: archivo Excel `.xlsx` descargable con columnas `Nombre` y `Fecha`

## Capa de IA

- El proveedor por defecto es `FakeSemanticDocumentIntelligence`.
- La interfaz esta desacoplada para permitir proveedores futuros como OpenAI o Azure OpenAI.
- La normalizacion de fechas y deduplicacion se realiza fuera del proveedor IA.
- Para usar Azure OpenAI real, el proveedor se selecciona por variables de entorno.

## Nota sobre Word legado

- Los archivos `.doc` se procesan solo en Windows.
- El equipo donde corre la API debe tener Microsoft Word instalado para convertir `.doc` a `.docx` de forma temporal.

## Trazabilidad

- Spec activa: `docs/sdd/wip/ewa-expiration-parser/spec.md`
- Commit sugerido SDD: `feature(ewa-parser): redefinir flujo Word a IA para analisis EWA`
- Commit sugerido implementacion: `feature(ewa-parser): implementar document intelligence para analisis EWA`
