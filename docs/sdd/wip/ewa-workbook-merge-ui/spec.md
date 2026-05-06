# EWA Workbook Merge UI Specification

## Objetivo

Agregar una nueva pantalla frontend para unir 2 o mas excels EWA ya generados, sin tocar los flujos actuales de exportacion ni dashboard.

La pantalla debe:

1. convivir con `Exportar` y `Graficos`,
2. mantener el lenguaje visual actual del proyecto,
3. trabajar sobre el contrato estable de la hoja `Base`,
4. permanecer desacoplada de la implementacion backend del merge.

## Alcance

### Incluido

- Nueva vista `Merge` dentro de la app Vue 3 existente.
- Seleccion de multiples archivos `.xlsx`.
- Validacion minima del tipo de archivo.
- Merge frontend de workbooks EWA sobre hoja `Base`.
- Descarga del workbook merged resultante.
- Empty state y resumen visual del merge.
- Suite de pruebas frontend para navegacion y flujo principal.

### Excluido en esta iteracion

- Endpoint HTTP para merge.
- Persistencia de merges.
- Deduplicacion semantica de filas.
- Preview tabular completa del workbook resultante.

## Flujo principal

`Pantalla Merge -> seleccionar 2+ excels -> leer hoja Base -> concatenar filas -> descargar workbook merged`

## Contrato de entrada

Cada workbook debe cumplir:

- Extension `.xlsx`
- Hoja `Base`
- Columnas exactas:
  - `Cliente`
  - `Componente`
  - `FechaVencimiento`

## Contrato de salida

El resultado descargable debe conservar:

- Hoja `Base`
- Columnas:
  - `Cliente`
  - `Componente`
  - `FechaVencimiento`

## Casos de uso

1. Un analista une excels de varios clientes sin reprocesar PDFs.
2. El usuario descarga una unica base consolidada para usar luego en la pantalla `Graficos`.
3. Un endpoint futuro puede reemplazar la implementacion local sin cambiar la UI.

## Criterios de aceptacion

1. La app debe ofrecer una navegacion explicita a la vista `Merge`.
2. La vista `Merge` debe iniciar con empty state.
3. El usuario debe poder cargar multiples `.xlsx`.
4. El boton principal debe requerir al menos 2 excels.
5. La UI debe descargar un workbook merged al completar el proceso.
6. La logica de merge debe vivir fuera del componente visual.
7. La pantalla debe verse correctamente en desktop y mobile.

## Edge cases

- Menos de 2 excels seleccionados.
- Archivo con extension no soportada.
- Workbook sin hoja `Base`.
- Workbook con header incorrecto.
- Filas vacias al final de una hoja.

## Impacto tecnico

### Arquitectura

- Se agrega un componente de vista dedicado en `frontend/src/components/`.
- El merge vive en un modulo propio reutilizable desde frontend.
- La UI no debe acoplarse a la estrategia final backend/local del merge.

### Calidad

- Desarrollo guiado por TDD para navegacion, validacion y descarga del merged workbook.

## Trazabilidad

- Spec activa: `docs/sdd/wip/ewa-workbook-merge-ui/spec.md`
- Commit sugerido implementacion: `feature(ewa-workbook-merge-ui): agregar pantalla de merge de excels`
