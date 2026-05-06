# Arquitectura

## Flujo principal

`PDF -> structured extractor -> document intelligence -> normalizer -> Excel exporter`

Flujo consolidado:

`Multiples PDF + cliente + periodo -> extractor -> document intelligence -> normalizer -> consolidation -> consolidated Excel`

Flujo de dashboard actual:

`Dashboard frontend -> carga workbook .xlsx -> hoja Base -> agregaciones frontend -> metricas y graficos`

Flujo de dashboard previsto:

`Dashboard frontend -> dashboard adapter -> agregados desde Excel consolidado -> metricas y graficos`

## Capas

- Frontend UI: app Vue 3 standalone para carga de archivos, feedback de estado, descarga del Excel y dashboard de metricas/graficos.
- Backend API: vive en `backend/app/`, recibe el archivo y traduce errores de dominio a respuestas HTTP.
- Parsers: viven en `backend/app/parsers/` y extraen layout + tablas desde `.pdf` con capa de texto para preservar mejor headers y filas.
- Document intelligence: vive en `backend/app/services/` e interpreta semanticamente el contenido y devuelve hallazgos crudos `nombre` + `fecha`, con `hito` opcional cuando hay tipos de soporte diferenciados.
- Normalizer: vive en `backend/app/` y valida fechas, resuelve `MM.YYYY`, normaliza a ISO y elimina duplicados exactos.
- Section resolver: vive dentro de la orquestacion y asigna `Seccion` anclando por el bloque del componente resuelto (`nombre + fecha`) para evitar headings vecinos incorrectos.
- Excel exporter: vive en `backend/app/services/` y genera el workbook final con columnas `Seccion`, `Nombre`, `Hito` y `Fecha`.
- Component catalog: vive en `backend/app/services/` y normaliza nombres detectados a componentes canonicos para reportes mensuales.
- Consolidation service: vive en `backend/app/services/` y une hallazgos por cliente, periodo y fuente EWA sin acoplarse a un proveedor IA.
- Dashboard adapter frontend: vive en `frontend/src/lib/` y abstrae tanto la lectura local de workbook como la carga del endpoint futuro `/ewa/dashboard`, con fallback demo mientras no exista backend.
- Orchestrator service: une el flujo completo sin acoplar la API a un proveedor IA concreto.
- CI: GitHub Actions ejecuta la suite de backend y frontend en entornos limpios para detectar dependencias faltantes y regresiones antes del deploy.

## Abstraccion de IA

- La interfaz del proveedor de IA debe aceptar texto completo y devolver hallazgos estructurados.
- El proyecto debe soportar cambio de proveedor sin alterar API, parser, normalizador ni exportador.
- La implementacion por defecto sera local/fake para desarrollo y tests.
- El diseño debe admitir proveedores futuros para OpenAI y Azure OpenAI.
- La seleccion del proveedor y las credenciales deben resolverse por variables de entorno.

## Decisiones

- El frontend vive desacoplado del backend y usa proxy de Vite para desarrollo local.
- En deploy sobre Vercel Services, el frontend vive en `/` y el backend bajo `/api`; el cliente resuelve la base por entorno y el backend conserva un alias `/api/ewa/analyze` para compatibilidad de ruteo.
- La navegacion frontend separa `Exportar` y `Graficos` para agregar visualizacion sin tocar el flujo operativo actual de consolidacion.
- La pantalla `Graficos` prioriza un Excel local con hoja `Base` para construir sus agregados sin depender del backend.
- La pantalla de dashboard hoy puede leer un Excel local y resolver agregaciones en frontend, pero ese comportamiento debe permanecer encapsulado para poder migrar luego a un contrato HTTP sin rehacer la vista.
- Mientras el endpoint de dashboard no exista, la UI puede renderizar datos demo para validar layout, navegacion y componentes sin bloquear la evolucion del backend.
- La deteccion principal no depende de regex rigidas dentro de la orquestacion.
- La normalizacion de fechas queda fuera del proveedor IA para mantener trazabilidad y reglas auditables.
- La reconciliacion local debe preservar nombres especificos ya resueltos por document intelligence y reservar sus heuristicas para nombres genericos o ambiguos.
- La columna `Seccion` se deriva del bloque semantico del documento y no solo del heading mas cercano a una fecha repetida.
- Los hitos de soporte vendor se transportan como metadato de dominio para distinguir `Standard` y `Extended` en el Excel final.
- El adaptador de payload IA acepta JSON completo como camino principal; si Azure OpenAI corta una respuesta repetitiva, recupera solo objetos `items` completos y deduplica antes de pasar al normalizador.
- La orquestacion cruza contexto local de cada fecha para descartar timestamps operativos de tablas tecnicas, como `ReleaseDate`, `Deployment Date`, `Final assembly date` y `Support Package importdate`, aunque la IA haya propuesto un componente valido.
- El consolidado mensual mantiene dos vistas: `Base` en formato largo para Power BI y `VistaClientes` con una fila por cliente para lectura operativa.
- `VistaClientes` usa un set acotado de columnas default para componentes frecuentes y una columna `Otros componentes` para evitar proliferacion de columnas dinamicas.
- Los componentes no catalogados se exportan en una hoja dedicada para ampliar el catalogo despues de relevar mas clientes.
- Los documentos consolidados que no generan hallazgos se informan a la UI mediante metadata HTTP para preservar trazabilidad sin interrumpir el consolidado ni agregar hojas auxiliares al Excel.
