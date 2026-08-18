# Como se actualiza la app sola (sin volver a descargar)

La idea: **vos haces los ajustes y los subis; la computadora del administrativo
recibe la ultima version sola cada vez que abre la app.** El administrativo
nunca descarga nada a mano.

---

## Instalacion por unica vez (la haces vos en la PC del administrativo)

Esto se hace **una sola vez**. Despues, el administrativo solo abre `procesar.bat`.

1. **Instalar Python**
   - Descargar de https://www.python.org/downloads/
   - Durante la instalacion, **tildar "Add Python to PATH"**.

2. **Instalar Git**
   - Descargar de https://git-scm.com/download/win
   - Instalar con las opciones por defecto (Siguiente -> Siguiente).

3. **Descargar la app con Git** (esto es lo que permite las actualizaciones automaticas).
   Abrir la carpeta donde quieras que viva la app, clic derecho ->
   "Abrir en Terminal" (o abrir "CMD") y pegar:

   ```
   git clone https://github.com/mativainstein-jpg/Facturas.git
   ```

   Eso crea una carpeta `Facturas`. La app esta adentro (en la raiz de esa carpeta).

4. **Entrar a la carpeta `Facturas` y hacer doble clic en `primera_vez.bat`.**
   Instala las librerias necesarias. (Solo esta vez.)

5. Si usan Gmail, copiar el archivo `credentials.json` dentro de la carpeta `Facturas`.

Listo. A partir de aca, el administrativo **solo abre `procesar.bat`**.

---

## Uso diario (lo hace el administrativo)

- Doble clic en **`procesar.bat`**.
- La PRIMERA vez que se abre en el dia, busca la ultima version sola (unos
  segundos) y arranca. Si se vuelve a abrir despues, ese mismo dia, abre
  directo (ya chequeo hoy, no vuelve a tardar).
- Si no hay internet, abre igual con la ultima version que tenia. **No se traba.**

### ¿Necesitas que actualice YA, sin esperar a mañana?

Doble clic en **`forzar_actualizacion.bat`** en vez de `procesar.bat`. Hace lo
mismo pero siempre busca la ultima version, aunque ya se haya abierto la app
antes ese mismo dia. Util cuando le pediste a Claude un cambio y queres que
le llegue al administrativo en el momento.

---

## Cuando vos haces un cambio

1. Haces el ajuste (con Claude).
2. Se sube al repositorio.
3. La proxima vez que el administrativo abra `procesar.bat` **con internet**,
   ya tiene tu cambio. No descarga nada a mano.

> **Nota sobre las ramas:** no te preocupes por esto. Se usa una sola rama y
> Claude se encarga de probar los cambios antes de publicarlos. Vos nunca tenes
> que mover nada entre ramas.

---

## Preguntas frecuentes

**Necesita internet siempre?**
No. Solo para *recibir* tus cambios al abrir. Procesar facturas y escribir el
Excel funciona sin internet. (Gmail si necesita internet, obviamente.)

**Se pierden sus datos al actualizar?**
No. El Excel de facturas, el token de Gmail y el `credentials.json` son propios
de esa PC y la actualizacion no los toca.

**Y si no quiere instalar Git?**
La app funciona igual, pero no se actualiza sola: en ese caso le tenes que pasar
los cambios a mano (o instalas Git despues y ya queda automatico).
