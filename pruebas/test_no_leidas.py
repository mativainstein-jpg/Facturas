#!/usr/bin/env python3
"""
Pruebas de la carpeta "Facturas no leidas" (copia de los PDF que no se
pudieron leer). Usa carpetas temporales: no toca nada del programa.

Uso:
    python pruebas/test_no_leidas.py
"""
import os
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import no_leidas as N  # noqa: E402

FALLAS = []


def chequear(nombre, obtenido, esperado):
    ok = obtenido == esperado
    print(f'  {"OK " if ok else "MAL"}  {nombre}: {obtenido!r}' + ('' if ok else f'  (esperado {esperado!r})'))
    if not ok:
        FALLAS.append(nombre)


def main():
    tmp = Path(tempfile.mkdtemp())
    origen = tmp / 'origen'
    origen.mkdir()
    carpeta = tmp / 'Facturas no leidas'
    pdf = origen / 'Factura.pdf'
    pdf.write_bytes(b'%PDF-1.4 uno')

    print('\nCopia de un PDF no leído')
    copia = N.guardar_no_leida('Factura.pdf', 'Texto PDF insuficiente o tipo de comprobante no reconocido',
                               ruta=pdf, carpeta=carpeta)
    chequear('se copia a la carpeta', copia, carpeta / 'Factura.pdf')
    chequear('la copia tiene el mismo contenido', copia.read_bytes(), b'%PDF-1.4 uno')
    chequear('el original sigue en su lugar', pdf.exists(), True)
    motivos = (carpeta / 'MOTIVOS.txt').read_text(encoding='utf-8')
    chequear('MOTIVOS.txt explica el motivo en simple', 'foto o un escaneo' in motivos, True)
    chequear('MOTIVOS.txt dice de dónde vino', str(pdf) in motivos, True)

    print('\nRepetidos')
    otra_vez = N.guardar_no_leida('Factura.pdf', 'x', ruta=pdf, carpeta=carpeta)
    chequear('el mismo PDF otra vez no se duplica', (otra_vez, sorted(p.name for p in carpeta.glob('*.pdf'))),
             (carpeta / 'Factura.pdf', ['Factura.pdf']))
    pdf2 = origen / 'otra' / 'Factura.pdf'
    pdf2.parent.mkdir()
    pdf2.write_bytes(b'%PDF-1.4 dos')
    copia2 = N.guardar_no_leida('Factura.pdf', 'x', ruta=pdf2, carpeta=carpeta)
    chequear('otro PDF con el mismo nombre queda como "(2)"', copia2, carpeta / 'Factura (2).pdf')

    print('\nDesde Gmail (bytes, sin archivo)')
    copia3 = N.guardar_no_leida('adjunto.pdf', 'error', contenido=b'%PDF bytes', carpeta=carpeta)
    chequear('se guarda desde los bytes', copia3.read_bytes(), b'%PDF bytes')

    print('\nFallas que no deben cortar nada')
    chequear('PDF que ya no existe → None', N.guardar_no_leida('no.pdf', 'x', ruta=origen / 'no.pdf',
                                                                carpeta=carpeta), None)
    if os.name != 'nt' and os.geteuid() != 0:
        bloqueada = tmp / 'bloqueada'
        bloqueada.mkdir()
        os.chmod(bloqueada, stat.S_IREAD | stat.S_IEXEC)
        chequear('carpeta sin permiso de escritura → None',
                 N.guardar_no_leida('Factura.pdf', 'x', ruta=pdf, carpeta=bloqueada / 'sub'), None)
    else:
        malo = tmp / 'es_un_archivo'
        malo.write_text('x')
        chequear('no se puede crear la carpeta → None',
                 N.guardar_no_leida('Factura.pdf', 'x', ruta=pdf, carpeta=malo / 'sub'), None)


if __name__ == '__main__':
    main()
    print()
    if FALLAS:
        print(f'FALLARON {len(FALLAS)} prueba(s): {", ".join(FALLAS)}')
        sys.exit(1)
    print('Todas las pruebas OK')
