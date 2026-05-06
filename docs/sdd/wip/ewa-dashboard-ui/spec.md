# EWA Dashboard UI Specification

## Objetivo

Construir una nueva pantalla frontend para visualizar graficos y metricas a partir del resultado consolidado de EWAs, sin alterar el flujo actual de carga y exportacion Excel.

La nueva pantalla debe:

1. convivir con la pantalla actual de exportacion,
2. reutilizar el lenguaje visual existente,
3. permitir cargar un Excel consolidado real desde el browser,
4. quedar preparada para consumir un endpoint futuro desacoplado del backend actual,
5. soportar una fuente temporal de datos demo mientras ese endpoint no exista.

## Alcance

### Incluido

- Nueva pantalla de dashboard dentro de la app Vue 3 existente.
- Navegacion simple entre `Exportar` y `Graficos`.
- Componentes visuales para metricas resumen y graficos.
- Carga local de archivos `.xlsx` para leer la hoja `Base`.
- Adaptador frontend para un endpoint futuro de dashboard.
- Fallback a datos demo locales cuando el endpoint no este disponible.
- Suite de pruebas frontend para navegacion, render y carga de datos.

### Excluido en esta iteracion

- Desarrollo del endpoint backend para dashboard.
- Lectura real del Excel desde backend.
- Persistencia de filtros o vistas.
- Drill-down por cliente o componente.
- Exportacion de imagenes o PDF de los graficos.

## Flujo principal

`Pantalla Graficos -> carga Excel local -> hoja Base -> agregaciones frontend -> metricas + graficos`

Flujo alternativo previsto:

`Pantalla Graficos -> adapter frontend -> endpoint futuro dashboard -> respuesta agregada -> metricas + graficos`

Flujo temporal mientras no exista backend:

`Pantalla Graficos -> adapter frontend -> fallback demo local -> metricas + graficos`

## Casos de uso

1. Un analista navega desde la pantalla de exportacion a la pantalla de graficos sin perder el flujo actual.
2. Un analista carga un Excel consolidado y la pantalla arma metricas y graficos a partir de la hoja `Base`.
3. La pantalla de graficos muestra un resumen por cliente, componente y proximidad de vencimiento.
4. Si no se cargo Excel y el endpoint futuro no esta disponible, la UI sigue siendo util con datos demo claramente identificados.
5. El usuario puede refrescar la vista para reintentar cargar desde el endpoint futuro.

## Contrato frontend esperado

El frontend debe quedar preparado para consumir un recurso HTTP desacoplado del backend de exportacion. El contrato esperado para una primera version es:

- Metodo: `GET`
- Path esperado: `/ewa/dashboard`
- Alias de deploy previsto: `/api/ewa/dashboard`
- Query opcional: `period=YYYY-MM`

Respuesta JSON esperada:

```json
{
  "period": "2026-05",
  "source": "api",
  "summary": {
    "totalClients": 12,
    "totalExpirations": 28,
    "expiringIn90Days": 7,
    "uniqueComponents": 9
  },
  "expirationsByMonth": [
    { "month": "2026-05", "count": 3 },
    { "month": "2026-06", "count": 5 }
  ],
  "expirationsByComponent": [
    { "component": "SAP ERP", "count": 8 },
    { "component": "SAP Solution Manager", "count": 5 }
  ],
  "clientsAtRisk": [
    {
      "client": "Cliente A",
      "expirations": 4,
      "nextExpiration": "2026-05-21"
    }
  ]
}
```

Contrato esperado del Excel local:

- Extension: `.xlsx`
- Hoja requerida: `Base`
- Columnas requeridas: `Cliente`, `Componente`, `FechaVencimiento`
- `FechaVencimiento` debe resolverse como fecha ISO `YYYY-MM-DD` o valor parseable equivalente

## Criterios de aceptacion

1. La pantalla actual de exportacion debe seguir funcionando sin cambios de comportamiento.
2. La app debe ofrecer una navegacion explicita entre `Exportar` y `Graficos`.
3. La pantalla `Graficos` debe mantener el estilo visual actual del proyecto.
4. La pantalla `Graficos` debe mostrar al menos:
   - metricas resumen,
   - un grafico temporal por mes,
   - un grafico por componente,
   - una tabla o lista de clientes con mayor riesgo.
5. La pantalla `Graficos` debe permitir seleccionar un archivo `.xlsx` y priorizar esa fuente sobre demo o endpoint.
6. La logica de lectura y agregacion del Excel debe vivir fuera del componente visual.
7. Si el endpoint falla o no esta disponible, la UI debe renderizar datos demo y comunicarlo al usuario.
8. El periodo debe poder controlarse desde la UI y formar parte de la carga de datos.
9. La solucion debe verse correctamente en desktop y mobile.

## Edge cases

- Respuesta vacia del endpoint.
- Excel sin hoja `Base`.
- Excel sin columnas requeridas.
- Archivo con extension no soportada.
- Error de red durante la carga del dashboard.
- `period` invalido.
- Dashboard con cero vencimientos.
- Componentes o clientes con nombres extensos.

## Impacto tecnico

### Arquitectura

- La app Vue mantiene el flujo de exportacion existente y agrega una segunda vista frontend.
- La capa visual del dashboard no debe conocer detalles de lectura de Excel ni del proveedor IA.
- La lectura del workbook y sus agregaciones deben encapsularse en modulos propios para luego poder reemplazar la fuente por backend sin reescribir la vista.
- La comunicacion con el endpoint futuro debe encapsularse en un modulo de acceso a datos.
- Los datos demo deben quedar en un modulo separado para reemplazo posterior.

### Calidad

- Desarrollo guiado por TDD para navegacion, carga del dashboard y preservacion del flujo actual.
- Documentacion del repositorio y arquitectura actualizadas con la nueva extension frontend.

## Trazabilidad

- Spec activa dashboard frontend: `docs/sdd/wip/ewa-dashboard-ui/spec.md`
- Commit sugerido implementacion: `feature(ewa-dashboard-ui): agregar pantalla de graficos para vencimientos`
