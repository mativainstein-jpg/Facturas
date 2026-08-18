# Facturas

Procesador de facturas AFIP (Facturas A y C) que extrae los datos de los PDF
y los carga en un Excel, con revision manual factura por factura y cruce de
proveedores para Gasto/Rubro.

## Instalacion y uso

Ver **COMO_ACTUALIZAR.md** para el paso a paso de instalacion (una sola vez)
y el uso diario.

- `primera_vez.bat` — instalacion inicial (Python + dependencias + Git).
- `procesar.bat` — abre la app (busca la ultima version, pero solo una vez
  por dia — si ya se abrio antes hoy, abre directo sin tardar).
- `forzar_actualizacion.bat` — igual que `procesar.bat`, pero siempre busca
  la ultima version aunque ya se haya chequeado hoy. Usarlo cuando se sabe
  que hay un cambio nuevo y no se quiere esperar a manana.
