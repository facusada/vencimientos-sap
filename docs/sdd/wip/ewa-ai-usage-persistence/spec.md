# EWA AI Usage Persistence Specification

## Objetivo

Persistir en PostgreSQL el consumo de tokens de IA por cada EWA procesado en el flujo consolidado, para dejar trazabilidad operativa sin depender del Excel generado.

## Alcance

### Incluido

- Persistencia server-side en PostgreSQL del consumo IA por EWA.
- Escritura durante `POST /ewa/consolidate`, porque ese flujo ya recibe `client` por archivo.
- Tabla nueva `ewa_ai_usage`.
- Resolucion de conexion por variable de entorno.
- Pruebas unitarias e integracion del backend para validar la persistencia.

### Excluido en esta iteracion

- Lectura de historico desde API.
- UI para listar consumos.
- Persistencia durante `POST /ewa/analyze`, porque ese endpoint no recibe `client`.
- Migraciones con Alembic.
- Calculo de costo monetario.

## Flujo principal

`Multiples PDF + client -> extraccion -> IA -> usage tokens -> persistencia PostgreSQL -> Excel`

## Tabla `ewa_ai_usage`

Columnas exactas:

- `id`
- `client`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `created_at`

Reglas:

- `id` debe ser clave primaria autoincremental.
- `client` es obligatorio.
- `input_tokens`, `output_tokens` y `total_tokens` admiten `NULL` cuando el proveedor no informa usage.
- `created_at` debe persistirse en UTC con default server-side al momento de insercion.
- Debe insertarse una fila por cada EWA recibido por `POST /ewa/consolidate`, incluso si el proveedor no informa tokens.

## Configuracion

Variables de entorno:

- `DATABASE_URL`: cadena de conexion PostgreSQL usada por el backend para persistir `ewa_ai_usage`.

## Criterios de aceptacion

1. `POST /ewa/consolidate` debe seguir devolviendo el mismo Excel descargable.
2. Por cada EWA procesado en el consolidado debe insertarse una fila en `ewa_ai_usage`.
3. Si el proveedor IA devuelve usage, deben persistirse `input_tokens`, `output_tokens` y `total_tokens`.
4. Si el proveedor IA no devuelve usage, la fila igual debe persistirse con tokens nulos.
5. `POST /ewa/analyze` no debe cambiar su contrato.
6. La configuracion de PostgreSQL debe resolverse por `DATABASE_URL`.
7. La capa de persistencia debe permanecer desacoplada del proveedor IA concreto.

## Decisiones

- La persistencia se engancha al consolidado porque es el primer flujo que ya conoce el `client` por archivo.
- Se persiste una tabla minima para auditar consumo antes de exponer lecturas o dashboards.
- En esta iteracion se crea la tabla de forma programatica con `CREATE TABLE IF NOT EXISTS` para evitar introducir Alembic sin necesidad inmediata.

## Trazabilidad

- Spec activa: `docs/sdd/wip/ewa-ai-usage-persistence/spec.md`
- Commit sugerido implementacion: `feature(ewa-usage): persistir consumo ia por cliente en postgres`
