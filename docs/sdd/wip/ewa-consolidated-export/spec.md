# EWA Consolidated Export Specification

## Objetivo

Agregar un flujo de consolidacion mensual para transformar multiples EWAs en una mini BBDD Excel apta para Power BI y seguimiento operativo.

El flujo debe reutilizar la deteccion existente de vencimientos y producir un archivo descargable donde:

1. cada EWA se asocia a un cliente y periodo mensual,
2. los vencimientos detectados se normalizan a componentes canonicos,
3. se genera una base tabular historizable,
4. se genera una vista ancha con una fila por cliente,
5. los componentes no catalogados quedan trazables para ampliar el catalogo.

## Alcance

### Incluido

- Nuevo endpoint `POST /ewa/consolidate` para recibir multiples archivos `.pdf`.
- Alias de deploy Vercel `POST /api/ewa/consolidate`.
- Metadata obligatoria por request:
  - `period`: periodo mensual en formato `YYYY-MM`.
  - `clients`: lista de clientes, uno por archivo y en el mismo orden.
  - `files`: lista de EWAs PDF.
- Reutilizacion del flujo existente `PDF -> extraccion -> document intelligence -> normalizacion`.
- Catalogo inicial de componentes canonicos importantes.
- Normalizacion de nombres detectados a componentes canonicos cuando haya equivalencias conocidas.
- Exportacion Excel con hojas:
  - `Base`
  - `VistaClientes`
  - `ComponentesNoCatalogados`
- La hoja `Base` mantiene formato largo para Power BI.
- La hoja `VistaClientes` mantiene una fila por cliente y columnas estables por componente.
- La hoja `ComponentesNoCatalogados` lista nombres detectados que no mapearon al catalogo.
- Si algun EWA no produce hallazgos de vencimiento, la API lo informa en metadata HTTP para que la app muestre un aviso.

### Excluido en esta iteracion

- Persistencia en base de datos.
- Historial server-side entre ejecuciones.
- Autenticacion, autorizacion y multitenancy.
- Inferencia automatica obligatoria del cliente desde el PDF.
- Power BI embebido o generacion de dashboards.

## Flujo principal

`Multiples PDF + cliente + periodo -> extraccion -> IA -> normalizacion -> consolidacion -> Excel`

## Contrato API

### `POST /ewa/consolidate`

Request `multipart/form-data`:

- `period`: string `YYYY-MM`.
- `clients`: lista repetida de strings.
- `files`: lista repetida de archivos `.pdf`.

Reglas:

- La cantidad de `clients` debe coincidir con la cantidad de `files`.
- Cada cliente debe tener nombre no vacio.
- El periodo debe tener formato mensual `YYYY-MM`.
- Todos los archivos deben ser `.pdf`.

Respuesta exitosa:

- Codigo `200`.
- Content-Type Excel `.xlsx`.
- Content-Disposition `attachment; filename=ewa-consolidated.xlsx`.
- Header opcional `X-EWA-No-Results` con JSON ASCII de EWAs sin vencimientos detectados.

Errores:

- Codigo `400` con mensaje claro si faltan archivos, cliente, periodo valido o si un archivo no es PDF.

## Excel consolidado

### Hoja `Base`

Columnas exactas:

`Cliente`, `Periodo`, `Componente`, `Hito`, `FechaVencimiento`, `Seccion`, `FuenteEWA`

Reglas:

- Una fila por vencimiento detectado.
- `Componente` usa el nombre canonico si el catalogo conoce el nombre detectado.
- Si el nombre no esta catalogado, `Componente` conserva el nombre detectado.
- `Hito` conserva valores como `End of Standard Vendor Support` y `End of Extended Vendor Support`.
- `FuenteEWA` conserva el nombre de archivo recibido.

### Hoja `VistaClientes`

Columnas exactas iniciales:

`Cliente`, `Periodo`, `SAP Product Version`, `SAP NetWeaver`, `SAP Solution Manager`, `SAP Fiori`, `SAP Kernel`, `Database`, `Operating System`, `Support Package Stack`, `Certificates`, `Otros componentes`

Reglas:

- Una fila por cliente y periodo.
- Cada columna de componente contiene la fecha detectada para ese componente.
- Si un componente no fue detectado para el cliente, la celda queda vacia.
- Si un componente tiene multiples hitos o fechas, la celda concatena valores con `; `, preservando el hito entre parentesis cuando exista.
- Las columnas se mantienen estables aunque haya componentes no catalogados.
- `Otros componentes` concatena componentes fuera del set default con formato `Componente: fecha` y agrega el hito entre parentesis cuando exista.

### Hoja `ComponentesNoCatalogados`

Columnas exactas:

`NombreDetectado`, `Cliente`, `Periodo`, `FechaVencimiento`, `FuenteEWA`

Reglas:

- Lista solo componentes que no mapearon al catalogo inicial.
- Sirve como insumo de relevamiento para ampliar defaults despues de analizar mas clientes.

## Catalogo inicial

Componentes canonicos:

- `SAP Product Version`
- `SAP NetWeaver`
- `SAP Fiori`
- `SAP Solution Manager`
- `SAP Kernel`
- `Database`
- `Operating System`
- `Support Package Stack`
- `Certificates`

Equivalencias iniciales:

- `SAP Kernel Release`, `Kernel`, `SAP Kernel 7.x` -> `SAP Kernel`
- `SAP NetWeaver Version`, `SAP NETWEAVER` -> `SAP NetWeaver`
- `SAP Fiori Front-End Server`, `SAP_UI`, `Fiori` -> `SAP Fiori`
- `Database Version`, `HANA Database`, `SAP HANA` -> `Database`
- `Operating System`, `Operating System Version`, `OS Vendor Support` -> `Operating System`
- `Support Package Stack`, `Current Support Package Stack` -> `Support Package Stack`
- `Certificate`, `Certificates` -> `Certificates`

## Criterios de aceptacion

1. `POST /ewa/analyze` debe seguir funcionando sin cambios de contrato.
2. `POST /ewa/consolidate` debe aceptar multiples PDFs con clientes y periodo.
3. El backend debe rechazar request con cantidad desigual de archivos y clientes.
4. El backend debe rechazar periodos que no cumplan `YYYY-MM`.
5. El backend debe rechazar clientes vacios.
6. El Excel consolidado debe incluir las tres hojas definidas.
7. La hoja `Base` debe contener una fila por hallazgo detectado con cliente, periodo y fuente.
8. La hoja `VistaClientes` debe contener una fila por cliente, aunque ese cliente no tenga un componente catalogado especifico.
9. Componentes ausentes para un cliente deben quedar con celda vacia.
10. Componentes no catalogados deben quedar en la hoja `ComponentesNoCatalogados`.
11. EWAs sin vencimientos detectados deben quedar informados por la API para que la UI muestre un aviso.
12. La normalizacion de componentes debe vivir fuera de la capa IA.
13. La API y la UI no deben acoplarse a un proveedor IA concreto.
14. Fechas operativas de tablas tecnicas, como `ReleaseDate`, `Deployment Date`, `Final assembly date` o `Support Package importdate`, no deben exportarse como vencimientos aunque la IA las asocie a un componente conocido.

## TDD

- Pruebas unitarias de catalogo de componentes.
- Pruebas unitarias de consolidacion.
- Pruebas unitarias de exportacion Excel consolidada.
- Pruebas de integracion para `POST /ewa/consolidate`.
- Pruebas frontend para metadata, envio multipart y descarga.

## Decisiones

- El Excel consolidado no reemplaza al Excel individual; agrega una salida orientada a historico y Power BI.
- Se usa formato largo en `Base` porque escala mejor para Power BI que columnas dinamicas por componente.
- Se agrega `VistaClientes` para cubrir la necesidad operativa de una fila por cliente.
- No se infiere cliente desde el EWA en esta iteracion; se recibe explicitamente para evitar errores silenciosos.
- El catalogo inicial es conservador y los no catalogados quedan visibles para relevamiento.
- Si Azure OpenAI devuelve un JSON truncado por una salida repetitiva, la capa de document intelligence recupera solo objetos `items` completos, descarta el fragmento incompleto y deduplica combinaciones `nombre` + `fecha` + `hito` antes de la normalizacion.
- Los EWAs sin hallazgos no fallan el consolidado mensual; quedan informados en la app para que el analista distinga ausencia real de vencimientos versus falta de extraccion sin contaminar el Excel.
- La orquestacion debe descartar fechas operativas de tablas tecnicas de HANA y support packages cuando no haya evidencia local de vencimiento real, para evitar falsos positivos repetidos en `Database`.

## Trazabilidad

- Spec activa: `docs/sdd/wip/ewa-consolidated-export/spec.md`
- Commit sugerido SDD: `feature(ewa-consolidation): especificar export mensual para power bi`
- Commit sugerido implementacion: `feature(ewa-consolidation): agregar excel consolidado por cliente`
