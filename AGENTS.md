# AGENTS

## Proposito

Este repositorio sigue un enfoque AI-First. Los agentes deben priorizar:

- trazabilidad de decisiones
- cumplimiento estricto de SDD y TDD
- separacion modular por capas
- cambios pequenos y verificables
- desacople entre extraccion de texto, IA y exportacion

## Comportamiento esperado

- no implementar codigo sin una spec vigente
- crear primero pruebas unitarias e integracion
- mantener una capa de document intelligence reemplazable
- evitar acoplar la API o la orquestacion a un proveedor IA concreto
- documentar decisiones relevantes en la spec, README y arquitectura
- resolver proveedor IA y credenciales por variables de entorno

## Convenciones de trabajo

- commits simulados con convencion `feature(...)` y `fix(...)`
- endpoint principal: `POST /ewa/analyze`
- flujo principal: `Word -> extraccion -> IA -> normalizacion -> Excel`
- salida esperada: Excel con columnas `Nombre` y `Fecha`
