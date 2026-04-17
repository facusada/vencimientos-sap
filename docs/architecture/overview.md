# Arquitectura

## Flujo principal

`Word (.docx / .doc) -> text extractor -> document intelligence -> normalizer -> Excel exporter`

## Capas

- API: recibe el archivo y traduce errores de dominio a respuestas HTTP.
- Parsers: extraen texto desde `.docx` o convierten `.doc` legado antes de extraer.
- Document intelligence: interpreta semanticamente el contenido y devuelve hallazgos crudos `nombre` + `fecha`.
- Normalizer: valida fechas, resuelve `MM.YYYY`, normaliza a ISO y elimina duplicados exactos.
- Excel exporter: genera el workbook final con columnas `Nombre` y `Fecha`.
- Orchestrator service: une el flujo completo sin acoplar la API a un proveedor IA concreto.

## Abstraccion de IA

- La interfaz del proveedor de IA debe aceptar texto completo y devolver hallazgos estructurados.
- El proyecto debe soportar cambio de proveedor sin alterar API, parser, normalizador ni exportador.
- La implementacion por defecto sera local/fake para desarrollo y tests.
- El diseño debe admitir proveedores futuros para OpenAI y Azure OpenAI.
- La seleccion del proveedor y las credenciales deben resolverse por variables de entorno.

## Decisiones

- La deteccion principal no depende de regex rigidas dentro de la orquestacion.
- La normalizacion de fechas queda fuera del proveedor IA para mantener trazabilidad y reglas auditables.
- `.doc` requiere Microsoft Word en Windows para conversion temporal.
