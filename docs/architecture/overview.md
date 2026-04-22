# Arquitectura

## Flujo principal

`Word/PDF -> OCR + text extractor -> document intelligence -> normalizer -> Excel exporter`

## Capas

- Frontend UI: app Vue 3 standalone para carga de archivos, feedback de estado y descarga del Excel.
- Backend API: vive en `backend/app/`, recibe el archivo y traduce errores de dominio a respuestas HTTP.
- Parsers: viven en `backend/app/parsers/`, ejecutan OCR y extraen texto desde `.pdf` y `.docx`, parsean `.doc` Word XML cuando aplica, o convierten `.doc` binario legado antes de extraer segun las capacidades del sistema operativo.
- Document intelligence: vive en `backend/app/services/` e interpreta semanticamente el contenido y devuelve hallazgos crudos `nombre` + `fecha`.
- Normalizer: vive en `backend/app/` y valida fechas, resuelve `MM.YYYY`, normaliza a ISO y elimina duplicados exactos.
- Excel exporter: vive en `backend/app/services/` y genera el workbook final con columnas `Nombre` y `Fecha`.
- Orchestrator service: une el flujo completo sin acoplar la API a un proveedor IA concreto.

## Abstraccion de IA

- La interfaz del proveedor de IA debe aceptar texto completo y devolver hallazgos estructurados.
- El proyecto debe soportar cambio de proveedor sin alterar API, parser, normalizador ni exportador.
- La implementacion por defecto sera local/fake para desarrollo y tests.
- El diseño debe admitir proveedores futuros para OpenAI y Azure OpenAI.
- La seleccion del proveedor y las credenciales deben resolverse por variables de entorno.
- El OCR corre antes de la capa de document intelligence para enriquecer el contexto textual enviado al proveedor IA.

## Decisiones

- El frontend vive desacoplado del backend y usa proxy de Vite para desarrollo local.
- La deteccion principal no depende de regex rigidas dentro de la orquestacion.
- La normalizacion de fechas queda fuera del proveedor IA para mantener trazabilidad y reglas auditables.
- `.doc` Word 2003 XML se parsea de forma directa; `.doc` binario usa Microsoft Word en Windows y LibreOffice headless en macOS/Linux para conversion temporal.
