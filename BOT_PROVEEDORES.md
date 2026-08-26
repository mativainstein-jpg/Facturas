# Bot de Telegram — actualización automática de proveedores

## Qué hace

Cuando la persona autorizada le manda el Excel de proveedores al bot de
Telegram (@Proveedoresadminbot), un workflow de **GitHub Actions**
(`.github/workflows/bot-proveedores.yml`) que corre cada 15 minutos:

1. Revisa si hay mensajes nuevos del bot (vía `getUpdates`).
2. Valida que el mensaje sea de la persona autorizada (ID numérico).
3. Descarga el archivo adjunto y lo parsea (columnas `cuit`, `nombre`,
   `codgasto`, `codrubro` — no importa el orden ni si hay otras columnas).
4. Compara contra `cuit_nombre.xlsx` y `proveedores.xlsx` de cada rama
   configurada (Facturas y Bejerman): agrega los CUIT nuevos, corrige
   nombre/gasto/rubro si cambiaron.
5. Sube el cambio directo a cada rama — sin pull request, sin revisión.
6. Responde por Telegram con un resumen (o un error, sin tocar nada, si el
   archivo no tiene la forma esperada).

No necesita ningún servidor externo (se dejó de usar Vercel: el entorno
donde corre Claude no tiene salida de red hacia servicios de terceros como
Vercel o Telegram, así que se resolvió con GitHub Actions, que sí corre con
acceso normal a internet).

## Configuración (una sola vez)

Cargar 2 secrets en GitHub: **Settings del repo → Secrets and variables →
Actions → New repository secret**:

| Secret | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN` | El token del bot (de @BotFather) |
| `AUTHORIZED_TELEGRAM_ID` | El ID numérico de Telegram autorizado a mandar el archivo |

Nada más. No hace falta cuenta de Vercel, ni desplegar nada a mano.

## Frecuencia

Corre cada 15 minutos. Si se necesita que procese al instante (sin esperar),
se puede disparar manualmente desde la pestaña **Actions** del repo (botón
"Run workflow" en "Bot proveedores (Telegram)"), o pedírselo a Claude.

## Seguridad

- Ignora en silencio cualquier mensaje que no venga del ID de Telegram
  autorizado.
- Si el archivo no tiene las columnas esperadas, o tiene muy pocas filas
  válidas, no toca ningún repositorio — solo avisa el error por Telegram.
- Los secrets nunca quedan expuestos en el código ni en los logs.
