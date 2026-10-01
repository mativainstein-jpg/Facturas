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
5. Después actualiza también el programa de **Bejerman** (repo
   `facturas-bejerman`), pero **solo `cuit_nombre.xlsx`** (ese programa no
   usa gasto ni rubro). Va aparte y al final: si falla (ej. el token no
   tiene acceso a ese repo), Facturas igual queda actualizado y el aviso
   por Telegram lo dice.
6. Responde por Telegram con un resumen (o un error, sin tocar nada, si el
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
| `BEJERMAN_REPO` | *(opcional)* repo del programa de Bejerman. Por defecto `facturas-bejerman`; vacío = no actualizarlo |
| `BEJERMAN_BRANCH` | *(opcional)* rama de ese repo. Por defecto `main` |

El `GITHUB_TOKEN` tiene que tener permiso de escritura también sobre el repo
de Bejerman (es privado). Si no lo tiene, el bot avisa por Telegram y sigue
actualizando Facturas con normalidad.

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

## Comando /estado

Escribiéndole `/estado` al bot por Telegram (solo responde a la persona
autorizada), chequea sin cambiar nada del repositorio:

- Si el token de GitHub puede **leer y escribir** en Facturas y en Bejerman.
- Si existen las ramas configuradas en `TARGET_BRANCHES`.
- Cuándo **vence** el token (avisa si faltan 14 días o menos, o si ya venció).

Para comprobar el permiso de escritura crea un objeto de prueba suelto en
GitHub (no queda en ninguna rama ni en el historial, no genera commits ni
dispara nada). Sirve para confirmar, por ejemplo, que el token tiene acceso
al repo privado de Bejerman antes de mandar un Excel.
