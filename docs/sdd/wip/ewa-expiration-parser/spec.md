# EWA Expiration Parser Specification

## Objetivo

Construir un servicio backend en Python con FastAPI orientado a documentos SAP EarlyWatch Alert en formato `.pdf` con texto extraible que:

1. reciba el documento PDF,
2. extraiga texto util del PDF preservando layout y contexto tabular sin OCR,
3. lo envíe a una capa de document intelligence/IA desacoplada,
4. obtenga vencimientos y fechas relevantes normalizados,
5. devuelva un archivo Excel descargable con cuatro columnas: `Seccion`, `Nombre`, `Hito` y `Fecha`.

## Alcance

### Incluido

- Endpoint `POST /ewa/analyze` para recibir un archivo EWA `.pdf`.
- Extraccion estructurada desde PDFs con capa de texto util mediante parser PDF sin OCR.
- Capa de IA/document intelligence desacoplada del resto de la aplicacion.
- Configuracion por variables de entorno para seleccionar el proveedor de IA y credenciales.
- Estructuracion de resultados de IA a una lista normalizada de objetos `nombre` + `fecha`, con `hito` opcional cuando el documento distinga tipos de vencimiento.
- Normalizacion de fechas a formato ISO `YYYY-MM-DD`.
- Soporte para fechas expresadas como `DD.MM.YYYY`, `YYYY-MM-DD`, `YYYY/MM/DD` y `MM.YYYY`.
- Soporte para tablas de EWA con columnas de mantenimiento o soporte vendor como `End of Standard Vendor Support*` y `End of Extended Vendor Support*`.
- Generacion de un archivo Excel `.xlsx` con columnas `Seccion`, `Nombre`, `Hito` y `Fecha`.
- Formato visual del Excel para destacar vencimientos: amarillo suave para fechas ya vencidas y verde suave para fechas futuras o vigentes, manteniendo contraste legible.
- Eliminacion de duplicados exactos por `nombre + fecha`.
- Resolucion de `Seccion` usando el bloque semantico del componente detectado, priorizando anclas por `nombre + fecha` sobre headings aislados cercanos a una fecha.
- Suite de pruebas unitarias e integracion.

### Excluido en esta iteracion

- Persistencia en base de datos.
- Integracion real con SAP, BTP, Azure DevOps o almacenamiento cloud.
- Procesamiento de documentos escaneados o basados en imagen.
- Autenticacion, autorizacion y multitenancy.
- Integracion productiva con OpenAI o Azure OpenAI; solo se dejara la abstraccion lista.

## Flujo principal

`PDF -> extraccion estructurada (layout + tablas) -> document intelligence -> normalizacion -> Excel`

## Casos de uso

1. Un analista carga un `.pdf` de EWA con texto extraible y obtiene un Excel con fechas de fin de mantenimiento, expiracion o soporte detectadas.
2. Un flujo automatizado usa el endpoint para transformar EWAs PDF en un Excel consolidado de vencimientos.
3. La capa de document intelligence interpreta frases variadas como `valid until`, `maintenance until`, `supported until`, `end of maintenance` o `expires on`.
4. La capa de document intelligence interpreta tablas EWA que expresan soporte vendor mediante columnas como `End of Standard Vendor Support*` y `End of Extended Vendor Support*`, aunque no exista una frase narrativa del tipo `supported until`.
5. Cuando una tabla EWA contenga mas de un hito temporal para el mismo componente, el sistema conserva cada fecha y explicita en `Hito` si corresponde a `End of Standard Vendor Support` o `End of Extended Vendor Support`.
6. Si no se detectan hallazgos, el sistema no genera Excel y devuelve un mensaje claro al usuario indicando que el EWA no contiene fechas de vencimiento detectables.

## Criterios de aceptacion

1. El flujo principal debe procesar correctamente documentos `.pdf` con texto extraible.
2. El sistema debe rechazar archivos que no sean `.pdf`.
3. La deteccion de vencimientos debe pasar por una capa de IA/document intelligence desacoplada del parser de texto.
4. La capa de IA debe devolver una estructura equivalente a una lista de objetos con `nombre` y `fecha`, y puede incluir `hito` cuando el documento explicite el tipo de vencimiento.
5. Las fechas detectadas deben normalizarse a formato ISO `YYYY-MM-DD`.
6. Si una fecha viene como `MM.YYYY`, debe normalizarse al ultimo dia de ese mes.
7. Fechas invalidas o imposibles no deben exportarse.
8. Duplicados exactos de `nombre + fecha` no deben exportarse.
9. El Excel final debe contener exactamente cuatro columnas: `Seccion`, `Nombre`, `Hito` y `Fecha`.
10. El endpoint `POST /ewa/analyze` debe responder con codigo `200` y un archivo Excel descargable cuando el archivo sea valido.
11. Si no hay vencimientos detectados, el sistema debe responder con error controlado `400` y un mensaje claro para el usuario, sin generar un Excel vacio.
12. Si el documento no puede procesarse o no es PDF, el endpoint debe responder con error `400`.
13. El sistema debe exportar fechas de soporte vendor detectadas en tablas EWA aunque el componente aparezca antes o despues de las fechas dentro del bloque tabular extraido.
14. Si un mismo componente tiene fechas diferentes para `End of Standard Vendor Support` y `End of Extended Vendor Support`, ambas deben exportarse y distinguirse en la columna `Hito`.
15. El Excel debe resaltar visualmente cada fila segun el estado de la fecha normalizada: amarillo suave si la fecha ya vencio y verde suave si la fecha aun no vencio.
16. La columna `Seccion` debe derivarse del bloque documental del hallazgo; no debe asignar `SAP Kernel Release` a vencimientos de producto o plataforma si el componente resuelto pertenece a otra seccion.
17. La extraccion PDF debe preservar headings y filas de tablas en una representacion textual estructurada para mejorar la interpretacion posterior.

## Edge cases

- PDFs con capa de texto pobre o fragmentada.
- Componentes con nombres no identicos entre secciones.
- Bloques tabulares donde el componente de sistema operativo aparece despues de las fechas de soporte vendor.
- Multiples fechas para un mismo bloque funcional.
- Multiples hitos de soporte para el mismo componente dentro de una misma tabla.
- Fechas vencidas y futuras en una misma seccion.
- Componentes repetidos.
- Texto tecnico mezclado con recomendaciones narrativas del EWA.
- Fechas repetidas en varias secciones donde un heading cercano puede no pertenecer al componente resuelto.
- Fechas embebidas en frases largas.
- Componentes sin la palabra `expiry` explicita pero con frases como `maintenance until`.
- Fechas `MM.YYYY`.
- PDFs sin texto extraible o dañados.

## Impacto tecnico

### Arquitectura

- `backend/app/api/` expondra el endpoint FastAPI.
- `backend/app/parsers/` se enfocara en extraccion estructurada desde PDFs, preservando layout y serializando filas de tabla.
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
- La cobertura debe incluir extraccion PDF, interpretacion de salida de IA, normalizacion de fechas, generacion de Excel y endpoint API.
- El repositorio debe validar backend y frontend automaticamente en GitHub Actions ante `push` y `pull_request`.

## Decisiones de diseño iniciales

- El parser de documento se encarga de extraer texto y contexto tabular del PDF; no decide vencimientos.
- La deteccion principal vive en una capa de IA/document intelligence.
- El proveedor por defecto sera una implementacion fake/heuristica semanticamente orientada para desarrollo local y tests.
- Azure OpenAI sera el proveedor externo objetivo para entornos reales.
- La normalizacion y validacion de fechas se realiza fuera del proveedor de IA para mantener contratos simples y auditables.
- Los nombres especificos devueltos por la IA deben preservarse por defecto; las heuristicas locales deben enfocarse en corregir nombres genericos, headers o ruido.
- La seccion exportada se resuelve con heuristicas trazables basadas en el bloque del componente y no solo en el heading mas cercano a la fecha.
- Los hitos de soporte vendor deben mantenerse separados y trazables mediante una columna `Hito`.

## Trazabilidad

- Spec activa: `docs/sdd/wip/ewa-expiration-parser/spec.md`
- Commit sugerido para esta etapa: `feature(ewa-parser): redefinir flujo PDF a IA para analisis EWA`
