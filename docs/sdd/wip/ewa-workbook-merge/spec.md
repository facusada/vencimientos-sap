# EWA Workbook Merge Specification

## Objetivo

Agregar un servicio backend dedicado exclusivamente a unir filas provenientes de 2 o mas excels ya generados por el flujo EWA, sin depender de extraccion de PDF, document intelligence ni consolidacion desde documentos fuente.

El servicio debe:

1. aceptar workbooks `.xlsx` con el formato actual del proyecto,
2. leer la hoja `Base`,
3. concatenar sus filas en orden estable,
4. producir un nuevo workbook `.xlsx` con el mismo schema,
5. permanecer desacoplado del resto del pipeline EWA.

## Alcance

### Incluido

- Servicio backend puro para merge de excels EWA ya generados.
- Lectura de 2 o mas workbooks `.xlsx`.
- Validacion de hoja `Base`.
- Validacion de columnas requeridas.
- Generacion de un nuevo workbook merged con hoja `Base`.
- Suite de pruebas unitarias del servicio.

### Excluido en esta iteracion

- Endpoint HTTP para merge de excels.
- Integracion con frontend.
- Dedupe semantico de filas repetidas.
- Relectura de PDFs o reprocesamiento IA.
- Persistencia en base de datos.

## Flujo principal

`2+ excels EWA -> leer hoja Base -> validar contrato -> concatenar filas -> exportar workbook merged`

## Contrato de entrada

Cada workbook de entrada debe cumplir:

- Extension logica `.xlsx`.
- Hoja `Base`.
- Columnas exactas:
  - `Cliente`
  - `Componente`
  - `FechaVencimiento`

## Contrato de salida

El workbook merged debe contener:

- Hoja `Base`
- Columnas exactas:
  - `Cliente`
  - `Componente`
  - `FechaVencimiento`

Reglas:

- Una fila de salida por cada fila valida de cada workbook de entrada.
- El orden debe preservar primero el orden de los workbooks recibidos y luego el orden de filas dentro de cada workbook.
- No debe eliminar duplicados en esta iteracion.
- Filas totalmente vacias pueden ignorarse.

## Casos de uso

1. Un analista ya tiene excels generados para varios clientes y necesita unificarlos sin volver a procesar PDFs.
2. El frontend de dashboards necesita una fuente tabular unica armada a partir de multiples excels existentes.
3. Un proceso futuro expone un endpoint que reutiliza este servicio para subir varios `.xlsx`.

## Criterios de aceptacion

1. El servicio debe rechazar menos de 2 workbooks.
2. El servicio debe rechazar workbooks sin hoja `Base`.
3. El servicio debe rechazar workbooks con columnas distintas a `Cliente`, `Componente`, `FechaVencimiento`.
4. El servicio debe devolver un workbook `.xlsx` merged con hoja `Base`.
5. El merge no debe modificar el flujo actual `POST /ewa/analyze`.
6. El merge no debe modificar el flujo actual `POST /ewa/consolidate`.
7. La logica de merge debe vivir aislada de la orquestacion PDF -> IA.

## Edge cases

- Workbook con una sola hoja pero nombre distinto a `Base`.
- Workbook con header correcto y filas vacias al final.
- Workbook con celdas vacias en una fila intermedia.
- Workbook con valores duplicados entre archivos.
- Lista de workbooks vacia o con un solo archivo.

## Impacto tecnico

### Arquitectura

- Se agrega un servicio dedicado de merge de workbooks en `backend/app/services/`.
- La lectura de excels ya generados no debe acoplarse a `ewa_analysis_service.py`.
- El contrato de merge se apoya en el schema estable de la hoja `Base`.

### Calidad

- TDD con pruebas unitarias sobre merge, validacion y workbook de salida.

## Decisiones

- El merge concatena filas y no deduplica porque esa decision depende del caso de uso consumidor.
- El schema de salida replica `Base` para que frontend y procesos futuros no necesiten adapters adicionales.
- La capacidad de merge se mantiene separada del consolidado desde PDFs porque resuelve una necesidad posterior del flujo, no el analisis base.

## Trazabilidad

- Spec activa: `docs/sdd/wip/ewa-workbook-merge/spec.md`
- Commit sugerido SDD: `feature(ewa-workbook-merge): especificar merge backend de excels`
- Commit sugerido implementacion: `feature(ewa-workbook-merge): agregar servicio de merge de workbooks`
