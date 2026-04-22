# EWA Expiration Parser Specification

## Objetivo

Construir un servicio backend en Python con FastAPI orientado principalmente a documentos Word SAP EarlyWatch Alert (`.docx` y `.doc`) que:

1. reciba el documento Word,
2. extraiga su texto,
3. lo envíe a una capa de document intelligence/IA desacoplada,
4. obtenga vencimientos y fechas relevantes normalizados,
5. devuelva un archivo Excel descargable con tres columnas: `Seccion`, `Nombre` y `Fecha`.

## Alcance

### Incluido

- Endpoint `POST /ewa/analyze` para recibir un archivo Word EWA.
- Extraccion de texto desde `.docx`.
- Procesamiento de `.doc` legado en formato Word 2003 XML mediante parseo directo, o conversion temporal en Windows / LibreOffice headless en macOS/Linux para `.doc` binario.
- Capa de IA/document intelligence desacoplada del resto de la aplicacion.
- Configuracion por variables de entorno para seleccionar el proveedor de IA y credenciales.
- Estructuracion de resultados de IA a una lista normalizada de objetos `nombre` + `fecha`.
- Normalizacion de fechas a formato ISO `YYYY-MM-DD`.
- Soporte para fechas expresadas como `DD.MM.YYYY`, `YYYY-MM-DD`, `YYYY/MM/DD` y `MM.YYYY`.
- Soporte para tablas de EWA con columnas de mantenimiento o soporte vendor como `End of Standard Vendor Support*` y `End of Extended Vendor Support*`.
- Fallback automatico con OCR para PDFs con poco texto extraible o documentos Word con imagenes embebidas cuando el extractor textual no sea suficiente.
- Generacion de un archivo Excel `.xlsx` con columnas `Seccion`, `Nombre` y `Fecha`.
- Formato visual del Excel para destacar vencimientos: amarillo suave para fechas ya vencidas y verde suave para fechas futuras o vigentes, manteniendo contraste legible.
- Eliminacion de duplicados exactos por `nombre + fecha`.
- Suite de pruebas unitarias e integracion.

### Excluido en esta iteracion

- Persistencia en base de datos.
- Integracion real con SAP, BTP, Azure DevOps o almacenamiento cloud.
- OCR como interpretacion visual avanzada del contenido; en esta iteracion solo se usara como fallback de extraccion textual.
- Autenticacion, autorizacion y multitenancy.
- Integracion productiva con OpenAI o Azure OpenAI; solo se dejara la abstraccion lista.

## Flujo principal

`Word (.docx / .doc) -> extraccion de texto -> document intelligence -> normalizacion -> Excel`

## Casos de uso

1. Un analista carga un `.docx` de EWA y obtiene un Excel con fechas de fin de mantenimiento, expiracion o soporte detectadas.
2. Un analista carga un `.doc` legado y el sistema lo procesa directamente si es Word 2003 XML; si es binario, intenta convertirlo y analizarlo. Si no hay soporte local para conversion, falla de forma controlada.
3. Un flujo automatizado usa el endpoint para transformar EWAs en un Excel consolidado de vencimientos.
4. La capa de document intelligence interpreta frases variadas como `valid until`, `maintenance until`, `supported until`, `end of maintenance` o `expires on`.
5. La capa de document intelligence interpreta tablas EWA que expresan soporte vendor mediante columnas como `End of Standard Vendor Support*` y `End of Extended Vendor Support*`, aunque no exista una frase narrativa del tipo `supported until`.
6. Si no se detectan hallazgos, el sistema no genera Excel y devuelve un mensaje claro al usuario indicando que el EWA no contiene fechas de vencimiento detectables.
7. Si un PDF tiene poco o nada de texto extraible, el sistema intenta OCR automaticamente antes de fallar.
8. Si un documento Word contiene imagenes embebidas, el sistema puede sumar el texto OCR detectado en esas imagenes al contexto enviado a IA.

## Criterios de aceptacion

1. El flujo principal debe procesar correctamente documentos `.docx`.
2. El sistema debe procesar `.doc` Word 2003 XML sin conversion, e intentar procesar `.doc` binario en Windows con Microsoft Word o en macOS/Linux con LibreOffice, fallando de forma controlada si no hay conversion disponible.
3. La deteccion de vencimientos debe pasar por una capa de IA/document intelligence desacoplada del parser de texto.
4. La capa de IA debe devolver una estructura equivalente a una lista de objetos con `nombre` y `fecha`.
5. Las fechas detectadas deben normalizarse a formato ISO `YYYY-MM-DD`.
6. Si una fecha viene como `MM.YYYY`, debe normalizarse al ultimo dia de ese mes.
7. Fechas invalidas o imposibles no deben exportarse.
8. Duplicados exactos de `nombre + fecha` no deben exportarse.
9. El Excel final debe contener exactamente tres columnas: `Seccion`, `Nombre` y `Fecha`.
10. El endpoint `POST /ewa/analyze` debe responder con codigo `200` y un archivo Excel descargable cuando el archivo sea valido.
11. Si no hay vencimientos detectados, el sistema debe responder con error controlado `400` y un mensaje claro para el usuario, sin generar un Excel vacio.
12. Si el documento no puede procesarse, el endpoint debe responder con error `400`.
13. El sistema debe exportar fechas de soporte vendor detectadas en tablas EWA aunque el componente aparezca antes o despues de las fechas dentro del bloque tabular extraido.
14. El Excel debe resaltar visualmente cada fila segun el estado de la fecha normalizada: amarillo suave si la fecha ya vencio y verde suave si la fecha aun no vencio.
15. El sistema debe activar OCR automaticamente cuando detecte PDFs con muy poco texto extraible o imagenes embebidas en documentos Word y el OCR este disponible.

## Edge cases

- Texto Word con muchas tablas o saltos de linea fragmentados.
- Componentes con nombres no identicos entre secciones.
- Bloques tabulares donde el componente de sistema operativo aparece despues de las fechas de soporte vendor.
- Multiples fechas para un mismo bloque funcional.
- Fechas vencidas y futuras en una misma seccion.
- Componentes repetidos.
- Texto tecnico mezclado con recomendaciones narrativas del EWA.
- Fechas embebidas en frases largas.
- Componentes sin la palabra `expiry` explicita pero con frases como `maintenance until`.
- Fechas `MM.YYYY`.
- Documentos Word sin texto extraible.
- `.doc` en una maquina sin Microsoft Word ni LibreOffice disponibles para conversion.

## Impacto tecnico

### Arquitectura

- `backend/app/api/` expondra el endpoint FastAPI.
- `backend/app/parsers/` se enfocara en extraer texto desde Word.
- `backend/app/services/document_intelligence.py` definira la interfaz y proveedores de IA.
- `backend/app/services/ewa_analysis_service.py` orquestara extraccion, IA, normalizacion, deduplicacion y Excel.
- `backend/app/services/excel_service.py` seguira dedicado a la exportacion.
- `backend/app/utils/` alojara utilidades de normalizacion de fechas.
- `backend/app/models/` definira contratos de dominio para hallazgos crudos y normalizados, incluyendo la seccion fuente cuando pueda derivarse del documento.

### Integracion futura

- La capa de IA debe poder reemplazarse por OpenAI, Azure OpenAI u otra implementacion sin romper el resto del flujo.
- Debe existir una implementacion fake/mock para pruebas.
- Azure OpenAI debe configurarse mediante variables de entorno y no con valores hardcodeados.
- La capa de servicio debe mantenerse desacoplada para futura persistencia en PostgreSQL y trazabilidad hacia Azure DevOps.

### Calidad

- El desarrollo seguira TDD: primero pruebas unitarias e integracion, luego implementacion minima y refactor.
- La cobertura debe incluir extraccion Word, interpretacion de salida de IA, normalizacion de fechas, generacion de Excel y endpoint API.

## Decisiones de diseño iniciales

- El parser de documento solo extrae texto; no decide vencimientos.
- La deteccion principal vive en una capa de IA/document intelligence.
- El proveedor por defecto sera una implementacion fake/heuristica semanticamente orientada para desarrollo local y tests.
- Azure OpenAI sera el proveedor externo objetivo para entornos reales.
- La normalizacion y validacion de fechas se realiza fuera del proveedor de IA para mantener contratos simples y auditables.
- `.doc` legado dependera de conversion temporal con Microsoft Word en Windows o LibreOffice headless en macOS/Linux.

## Trazabilidad

- Spec activa: `docs/sdd/wip/ewa-expiration-parser/spec.md`
- Commit sugerido para esta etapa: `feature(ewa-parser): redefinir flujo Word a IA para analisis EWA`
