# Setup — Procesador de Facturas

## 1. Instalar (una sola vez por PC)

- **Windows:** doble clic en `primera_vez.bat`. Instala lo necesario.
- **Mac/Linux:** `pip install -r requirements.txt`.

## 2. Usarlo día a día

- **Windows:** doble clic en `procesar.bat`. Antes de abrir el programa, busca
  la última versión (si hay internet) y se actualiza solo.
- **Mac/Linux:** `python main.py`.

## 3. Archivos de la carpeta

| Archivo / carpeta | Qué es | ¿Se edita a mano? |
|---|---|---|
| `facturas.xlsx` | El Excel con las facturas cargadas (hojas FACTURAS, DUPLICADAS y ERRORES). | Sí: completar las celdas en ROJO. |
| `respaldos/` | Copia de `facturas.xlsx` antes de cada guardado (las últimas 30). | No. Sirve si el Excel se rompe. |
| `Facturas no leidas/` | Copia de cada PDF que el programa no pudo leer, y `MOTIVOS.txt` con el porqué. Botón "Ver no leídas". | No. Esas facturas se cargan a mano. |
| `proveedores.xlsx` | Maestro de proveedores: columna A = CUIT, B = código de gasto, D = código de rubro. | **No.** Lo mantiene el bot de Telegram y se pisa en cada actualización. |
| `cuit_nombre.xlsx` | Maestro de nombres: columna A = CUIT, B = nombre del proveedor. | **No.** Lo mantiene el bot de Telegram y se pisa en cada actualización. |
| `proveedores_locales.xlsx` | Proveedores que agrega el administrativo en ESTA PC (CUIT, nombre, gasto, rubro). Botón "Agregar proveedores". | Sí. La actualización no lo toca. |
| `estado.json`, `token.json` | Solo para Gmail (registro de lo ya procesado y autorización). | No. `token.json` no se comparte. |

Para agregar o corregir proveedores para TODAS las PC, mandarle el Excel de
proveedores al bot de Telegram (ver `BOT_PROVEEDORES.md`). Para algo puntual
de una sola PC, usar "Agregar proveedores".

## 4. Gmail (opcional, hoy no se usa)

El botón "Buscar en Gmail" necesita credenciales de Google. Solo hace falta si
se quiere usar:

1. Ir a https://console.cloud.google.com/ y crear un proyecto (o usar uno).
2. Habilitar la **Gmail API**: APIs y servicios → Biblioteca → "Gmail API" → Habilitar.
3. Crear credenciales: APIs y servicios → Credenciales → Crear credenciales →
   **ID de cliente OAuth 2.0**, tipo **Aplicación de escritorio**.
4. Descargar el JSON, renombrarlo a `credentials.json` y copiarlo en esta carpeta.

La primera vez que se apriete el botón se abre el navegador para autorizar;
después queda guardado en `token.json`. Sin `credentials.json` el resto del
programa funciona igual.
