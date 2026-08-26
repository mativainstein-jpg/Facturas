# Bot de Telegram — actualización automática de proveedores

Rama dedicada, aislada del resto del repositorio (no toca ni afecta la app
de Facturas ni la de Bejerman). Vive acá porque es donde se pudo escribir
sin necesitar una cuenta nueva — Vercel se conecta directo a esta rama.

## Qué hace

Cuando la persona autorizada le manda el Excel de proveedores al bot de
Telegram, el webhook (`api/telegram-webhook.js`):

1. Valida que el mensaje venga de Telegram (header secreto) y de la persona
   autorizada (ID numérico).
2. Descarga el archivo adjunto y lo parsea (columnas `cuit`, `nombre`,
   `codgasto`, `codrubro` — no importa el orden ni si hay otras columnas).
3. Compara contra `cuit_nombre.xlsx` y `proveedores.xlsx` de cada rama
   configurada: agrega los CUIT nuevos, corrige nombre/gasto/rubro si
   cambiaron.
4. Sube el cambio directo (commit atómico vía Git Data API) a cada rama —
   sin pull request, sin revisión.
5. Responde por Telegram con un resumen (o un error, sin tocar nada, si el
   archivo no tiene la forma esperada).

## Cómo desplegarlo en Vercel (una sola vez)

1. Entrar a **vercel.com** → **Add New... → Project**.
2. Importar el repositorio **Facturas** de GitHub.
3. En "Configure Project":
   - **Root Directory**: dejar como está (raíz).
   - **Branch a desplegar**: `bot-proveedores` (en Project Settings → Git,
     después de crear el proyecto, si no lo pide antes).
4. Antes de darle "Deploy", agregar estas variables de entorno
   (Settings → Environment Variables):

   | Variable | Valor |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | (el token del bot, de @BotFather) |
   | `TELEGRAM_SECRET_TOKEN` | (secreto generado — lo tiene Claude) |
   | `AUTHORIZED_TELEGRAM_ID` | (ID numérico de Telegram autorizado) |
   | `GITHUB_TOKEN` | (Personal Access Token con permiso de escritura) |
   | `GITHUB_OWNER` | `mativainstein-jpg` |
   | `GITHUB_REPO` | `Facturas` |
   | `TARGET_BRANCHES` | `main,claude/invoice-app-setup-ss5uwf,claude/bejerman-invoice-reader-do4scq` |

5. Deploy. Vercel da una URL (algo como
   `https://bot-proveedores-facturas.vercel.app`).
6. Pasarle esa URL a Claude — falta un último paso (registrar la URL en
   Telegram) que Claude hace directo por API, sin necesitar acceso a Vercel.

## Seguridad

- El bot ignora en silencio cualquier mensaje que no venga del ID de
  Telegram autorizado.
- Valida un header secreto en cada pedido, para que nadie pueda simular ser
  Telegram mandando pedidos directo a la URL del webhook.
- Si el archivo no tiene las columnas esperadas, o tiene muy pocas filas
  válidas, no toca el repositorio — solo avisa el error por Telegram.
