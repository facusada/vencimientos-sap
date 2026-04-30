# EWA Upload UI Specification

## Objetivo

Construir un frontend en Vue 3 para el flujo de analisis EWA que:

1. permita cargar archivos `.pdf`,
2. invoque `POST /ewa/analyze`,
3. muestre estados de carga, error y exito,
4. descargue el Excel generado por el backend,
5. mantenga una experiencia simple, moderna y orientada a analistas funcionales.

## Alcance

### Incluido

- Aplicacion Vue 3 standalone dentro del mismo repositorio.
- Pantalla unica para carga por click o drag-and-drop.
- Validacion basica de extension `.pdf`.
- Eliminacion de archivos seleccionados antes de enviar el analisis o consolidado.
- Llamada HTTP al endpoint `POST /ewa/analyze`.
- Descarga del archivo `.xlsx` devuelto por la API.
- Estados visibles de `idle`, `uploading`, `success` y `error`.
- Mensajes de ayuda sobre formatos soportados.
- Suite de pruebas unitarias del frontend para el flujo principal.

### Excluido en esta iteracion

- Autenticacion y autorizacion.
- Historial de cargas.
- Persistencia de resultados.
- Preview del contenido del documento.
- Tabla de resultados embebida en la UI.

## Flujo principal

`Seleccion de archivo -> POST /ewa/analyze -> respuesta Excel -> descarga`

## Casos de uso

1. Un analista arrastra un `.pdf`, ejecuta el analisis y descarga el Excel.
2. Si el archivo no es valido, la UI informa el error antes de enviar.
3. Si la API devuelve `400`, la UI muestra el mensaje funcional del backend.

## Criterios de aceptacion

1. La UI debe permitir seleccionar un archivo por input y por drag-and-drop.
2. Solo deben aceptarse `.pdf`.
3. El boton principal debe quedar deshabilitado mientras no haya archivo o mientras haya una carga en curso.
4. Durante la carga debe mostrarse un estado visual inequívoco.
5. Al responder `200`, la UI debe descargar el Excel sin pasos manuales adicionales.
6. Al responder con error, la UI debe mostrar el detalle devuelto por la API.
7. La UI debe verse correctamente en desktop y mobile.
8. El frontend debe ejecutarse en desarrollo con Vite y proxy hacia la API local.
9. Cada EWA seleccionado debe poder eliminarse antes del envio.

## Edge cases

- Archivo con extension en mayusculas.
- Reemplazo del archivo seleccionado por otro.
- Error de red sin cuerpo JSON.
- Respuesta no JSON en error.
- Usuario que intenta enviar sin archivo.

## Impacto tecnico

### Arquitectura

- Se agrega carpeta `frontend/` con app Vue 3 + Vite y backend Python separado en `backend/`.
- La UI consume el backend existente sin acoplarse a la implementacion interna de IA.
- El desarrollo local usara proxy de Vite para evitar configuracion adicional de CORS.
- La URL base de la API debe poder resolverse por entorno para soportar despliegue con frontend en `/` y backend montado bajo `/api` en Vercel, sin alterar el endpoint funcional `POST /ewa/analyze`.

### Calidad

- Desarrollo guiado por TDD para validacion de UI, request y manejo de errores.
- La documentacion del repositorio debe incluir comandos de frontend y backend.

## Trazabilidad

- Spec activa frontend: `docs/sdd/wip/ewa-upload-ui/spec.md`
- Commit sugerido implementacion: `feature(ewa-ui): agregar interfaz Vue para carga y descarga EWA`
