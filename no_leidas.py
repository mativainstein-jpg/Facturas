"""
Carpeta "Facturas no leidas": cada PDF que el programa no pudo leer se COPIA
acá (el original queda donde estaba), junto con una línea en MOTIVOS.txt que
dice cuándo, por qué y de dónde vino. Así cualquiera ve qué falta cargar a
mano.

Nada de lo de acá puede cortar el procesamiento: si no se puede copiar
(disco lleno, permisos), se sigue igual y la función devuelve None.
"""
import os
import subprocess
import sys
from datetime import datetime

from config import BASE_DIR

NOMBRE_CARPETA    = 'Facturas no leidas'
CARPETA_NO_LEIDAS = BASE_DIR / NOMBRE_CARPETA
ARCHIVO_MOTIVOS   = 'MOTIVOS.txt'


def _motivo_simple(motivo):
    """El motivo técnico, dicho en palabras simples."""
    m = (motivo or '').lower()
    if 'insuficiente' in m or 'no reconocido' in m:
        return ('No tiene texto legible (puede ser una foto o un escaneo) o no '
                'es una factura/nota A o C de AFIP.')
    return motivo or 'Error desconocido al leer el PDF.'


def _destino_libre(carpeta, nombre, contenido):
    """
    Devuelve (ruta, ya_estaba): ruta donde guardar la copia. Si ya hay un
    archivo idéntico con ese nombre (o con un sufijo " (n)"), no se copia de
    nuevo. Si hay uno distinto con el mismo nombre, se usa "nombre (2).pdf",
    "(3)", etc.
    """
    base, ext = os.path.splitext(nombre)
    n = 1
    while True:
        candidato = carpeta / (nombre if n == 1 else f'{base} ({n}){ext}')
        if not candidato.exists():
            return candidato, False
        try:
            if candidato.read_bytes() == contenido:
                return candidato, True
        except OSError:
            pass
        n += 1


def guardar_no_leida(nombre, motivo, ruta=None, contenido=None, carpeta=None):
    """
    Copia el PDF que no se pudo leer a la carpeta de no leídas.
      nombre:    nombre del archivo (ej. "Factura.pdf")
      motivo:    por qué no se pudo leer
      ruta:      dónde está el PDF original (flujo normal), o
      contenido: los bytes del PDF (cuando vino de Gmail y no hay archivo)
    Devuelve la ruta de la copia, o None si no se pudo copiar.
    """
    carpeta = carpeta or CARPETA_NO_LEIDAS
    try:
        if contenido is None:
            contenido = ruta.read_bytes()
        carpeta.mkdir(parents=True, exist_ok=True)
        destino, ya_estaba = _destino_libre(carpeta, nombre or 'sin_nombre.pdf', contenido)
        if not ya_estaba:
            destino.write_bytes(contenido)
        origen = str(ruta) if ruta else 'Gmail'
        with open(carpeta / ARCHIVO_MOTIVOS, 'a', encoding='utf-8') as f:
            f.write(f'{datetime.now():%d/%m/%Y %H:%M}  |  {destino.name}  |  '
                    f'{_motivo_simple(motivo)}  |  Original: {origen}\n')
        return destino
    except Exception:
        return None


def abrir_carpeta_no_leidas(carpeta=None):
    """Crea la carpeta si falta y la abre en el Explorador de archivos.
    Devuelve False si no se pudo abrir (para avisar dónde está)."""
    carpeta = carpeta or CARPETA_NO_LEIDAS
    try:
        carpeta.mkdir(parents=True, exist_ok=True)
        if sys.platform == 'win32':
            os.startfile(str(carpeta))
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(carpeta)])
        else:
            subprocess.run(['xdg-open', str(carpeta)])
        return True
    except Exception:
        return False
