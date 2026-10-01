# Bot de Telegram — actualización automática de proveedores

## Cómo funciona hoy (lo que realmente está en uso)

El bot (@Proveedoresadminbot) corre en **Vercel** (proyecto `facturas`,
equipo Naiman). Su código **no está en `main`**: vive en la rama
**`bot-proveedores`** de este repositorio (carpeta `api/`). El
`BOT_PROVEEDORES.md` de esa rama tiene los detalles de configuración
(variables de entorno, cómo desplegarlo).

Telegram le avisa por *webhook* apenas llega un mensaje, así que no hay
demora. Cuando la persona autorizada le manda el Excel de proveedores
(columnas `cuit`, `nombre`, `codgasto`, `codrubro`), el bot:

1. Valida que el mensaje venga de Telegram y de la persona autorizada
   (ID numérico); ignora en silencio a cualquier otra.
2. Descarga el archivo y lo compara con los maestros: agrega los CUIT nuevos
   y corrige nombre / gasto / rubro si cambiaron.
3. Guarda el cambio directo, sin pull request y sin revisión, en:
   - **Facturas**: `cuit_nombre.xlsx` y `proveedores.xlsx` en `main` y en las
     ramas `claude/invoice-app-setup-ss5uwf` y
     `claude/bejerman-invoice-reader-do4scq`.
   - **Bejerman** (repo `facturas-bejerman`): solo `cuit_nombre.xlsx`, porque
     ese programa no usa gasto ni rubro. Se hace al final y por separado: si
     falla, Facturas igual queda actualizado.
4. Responde por Telegram con un resumen (o con el error, sin tocar nada, si el
   archivo no tiene la forma esperada o tiene muy pocas filas válidas).

Los programas de escritorio se actualizan solos (`actualizar.py`) la próxima
vez que se abren, así que bajan los maestros nuevos sin hacer nada.

## Por qué Vercel solo publica la rama `bot-proveedores`

Vercel está conectado a todo el repositorio, y cada vez que el bot guarda
proveedores en `main` o en las ramas `claude/...` intentaba "publicarlas".
Esas ramas son el programa de escritorio (no una web), así que fallaba con
"Preview deployment failed" y mandaba un mail de error cada vez. Se
configuró en Vercel (Settings → Git → Ignored Build Step) que solo construya
`bot-proveedores`. Si alguna vez hace falta publicar otra rama, hay que
cambiar esa regla.

## Si algo falla

- Escribirle `/estado` al bot por Telegram chequea al instante, sin cambiar
  nada, si el token de GitHub puede leer y escribir en Facturas y en
  Bejerman, y cuándo vence el token.
- Telegram avisa con ❌ (no se actualizó nada) o con ⚠ (se actualizó
  Facturas pero no Bejerman) y dice el motivo.
- Aviso ⚠ de Bejerman: el token de GitHub del bot (`GITHUB_TOKEN`, cargado en
  Vercel) tiene que tener permiso de escritura también sobre el repo
  `facturas-bejerman`, que es privado.
- Para dejar de actualizar Bejerman sin tocar código: poner la variable
  `BEJERMAN_REPO` vacía en Vercel y volver a desplegar.

## Versión anterior (desactivada, no usar)

`.github/workflows/bot-proveedores.yml` y `.github/scripts/bot_telegram.py`
son una versión anterior del bot que corría en GitHub Actions (revisando
Telegram cada 1 hora). Quedó **desactivada manualmente** el 26/08/2026 y se
conserva solo como respaldo. No hay que volver a activarla mientras el
webhook de Vercel esté en uso: Telegram no permite usar webhook y revisión
periódica a la vez, y fallaría. Además, esa versión no actualiza el
programa de Bejerman. `bot_state/last_update_id.txt` pertenece a esa versión.
