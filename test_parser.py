#!/usr/bin/env python3
"""
Prueba el parser sobre PDFs locales sin escribir nada en Excel.

Uso:
    python test_parser.py factura1.pdf [factura2.pdf ...]

Regresión (para comprobar que un cambio no rompe facturas que ya andaban):
    python test_parser.py --guardar esperado.json factura1.pdf ...
        Graba lo que lee hoy de cada factura.
    python test_parser.py --comparar esperado.json factura1.pdf ...
        Muestra solo lo que cambió respecto de lo grabado (sale con código 1
        si hubo diferencias).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pdf_parser import extraer_texto, es_texto_valido, parsear_factura
from excel_manager import cargar_indice_proveedores, cargar_indice_nombres

_CAMPOS = [
    ('tipo',                'Tipo comprobante'),
    ('punto_venta',         'Tipo (fijo)'),
    ('numero',              'Número'),
    ('punto_venta_factura', 'Punto de Venta (factura)'),
    ('fecha',               'Fecha'),
    ('denominacion',        'Denominación'),
    ('cuit',                'CUIT'),
    ('neto_num',            'Neto gravado'),
    ('iva_num',             'IVA'),
    ('otros_tributos_num',  'Otros tributos'),
    ('kilos_num',           'Kilos / Cantidad'),
    ('precio_unitario_num', 'Precio unitario'),
    ('total_num',           'Total'),
    ('tasa',                'Tasa IVA'),
    ('monotributista',      'Monotributista'),
    ('posicion',            'Posición'),
    ('mes',                 'Mes'),
    ('anio',                'Año'),
    ('gasto',               'Gasto (cruce proveedores)'),
    ('descripcion_gasto',   'Descripción gasto'),
    ('rubro',               'Rubro (cruce proveedores)'),
    ('descripcion_rubro',   'Descripción rubro'),
    ('clave',               'Clave comprobante'),
]

# Campos críticos que se marcan con ⚠ si están vacíos
_CRITICOS = {
    'tipo', 'punto_venta_factura', 'denominacion', 'cuit', 'fecha', 'neto_num',
    'iva_num', 'kilos_num', 'precio_unitario_num', 'total_num', 'gasto', 'rubro',
}


def _fmt(val):
    if val is None or val == '':
        return '—'
    if isinstance(val, float):
        return f'{val:,.2f}'
    return str(val)


def _parsear(ruta: Path, indice_proveedores: dict, indice_nombres: dict = None):
    """Devuelve (datos, None) o (None, mensaje de error)."""
    try:
        pdf_bytes = ruta.read_bytes()
    except Exception as e:
        return None, f'No se pudo leer el archivo: {e}'
    try:
        texto = extraer_texto(pdf_bytes)
    except Exception as e:
        return None, f'Error extrayendo texto del PDF: {e}'
    if not es_texto_valido(texto):
        return None, ('Texto insuficiente o tipo de comprobante no reconocido '
                      '(el PDF puede ser imagen escaneada o no ser una factura AFIP)')
    try:
        return parsear_factura(texto, ruta.name, indice_proveedores,
                               pdf_bytes=pdf_bytes, indice_nombres=indice_nombres), None
    except Exception as e:
        return None, f'Error al parsear: {e}'


def _resultado(ruta, indice_proveedores, indice_nombres):
    datos, error = _parsear(ruta, indice_proveedores, indice_nombres)
    if error:
        return {'error': error}
    return {key: datos.get(key) for key, _ in _CAMPOS}


def guardar(destino: Path, rutas, indice_proveedores, indice_nombres):
    esperado = {r.name: _resultado(r, indice_proveedores, indice_nombres) for r in rutas}
    destino.write_text(json.dumps(esperado, ensure_ascii=False, indent=1, default=str),
                       encoding='utf-8')
    print(f'Grabado lo leído de {len(esperado)} PDF(s) en {destino}')


def comparar(origen: Path, rutas, indice_proveedores, indice_nombres):
    esperado = json.loads(origen.read_text(encoding='utf-8'))
    etiquetas = dict(_CAMPOS)
    n_dif = 0
    for r in rutas:
        if r.name not in esperado:
            print(f'  ?  {r.name}: no está en {origen.name}')
            continue
        # Pasar por JSON para comparar con los mismos tipos que lo grabado.
        actual = json.loads(json.dumps(_resultado(r, indice_proveedores, indice_nombres),
                                       default=str))
        antes = esperado[r.name]
        difs = [(k, antes.get(k), actual.get(k)) for k in sorted(set(antes) | set(actual))
                if antes.get(k) != actual.get(k)]
        if difs:
            n_dif += 1
            print(f'\n  ✗ {r.name}')
            for k, a, b in difs:
                print(f'      {etiquetas.get(k, k):<26} {_fmt(a)}  →  {_fmt(b)}')
    print(f'\n{len(rutas) - n_dif}/{len(rutas)} PDF(s) sin cambios.')
    return n_dif == 0


def analizar(ruta: Path, indice_proveedores: dict, indice_nombres: dict = None):
    print(f'\n{"─" * 64}')
    print(f'  {ruta.name}')
    print(f'{"─" * 64}')

    datos, error = _parsear(ruta, indice_proveedores, indice_nombres)
    if error:
        print(f'  ✗ {error}')
        return

    n_problemas = 0
    for key, label in _CAMPOS:
        val = datos.get(key)
        texto_val = _fmt(val)
        # None/'' = no encontrado (VERIFICAR). 0.0 es un valor real (ej. IVA de un
        # monotributista), no "vacío" — misma semántica que excel_manager/reconciliacion.
        vacio = val is None or val == ''
        critico = key in _CRITICOS and vacio
        marca = '  ⚠' if critico else ''
        if critico:
            n_problemas += 1
        print(f'  {label:<22} {texto_val}{marca}')

    print()
    if n_problemas == 0:
        print('  ✅  Todos los campos críticos OK')
    else:
        print(f'  ⚠   {n_problemas} campo(s) crítico(s) sin valor — se marcarán VERIFICAR en Excel')


if __name__ == '__main__':
    args = sys.argv[1:]
    modo = archivo_json = None
    if args and args[0] in ('--guardar', '--comparar'):
        if len(args) < 2:
            print(__doc__)
            sys.exit(1)
        modo, archivo_json, args = args[0], Path(args[1]), args[2:]

    if not args:
        print(__doc__)
        sys.exit(1)

    rutas = [Path(a) for a in args]
    faltantes = [r for r in rutas if not r.exists()]
    if faltantes:
        for r in faltantes:
            print(f'Archivo no encontrado: {r}')
        sys.exit(1)

    try:
        indice_proveedores = cargar_indice_proveedores()
        if indice_proveedores:
            print(f'Índice de proveedores cargado: {len(indice_proveedores)} entradas')
    except Exception:
        indice_proveedores = {}

    try:
        indice_nombres = cargar_indice_nombres()
        if indice_nombres:
            print(f'Índice de nombres cargado: {len(indice_nombres)} entradas')
    except Exception:
        indice_nombres = {}

    if modo == '--guardar':
        guardar(archivo_json, rutas, indice_proveedores, indice_nombres)
        sys.exit(0)
    if modo == '--comparar':
        sys.exit(0 if comparar(archivo_json, rutas, indice_proveedores, indice_nombres) else 1)

    for ruta in rutas:
        analizar(ruta, indice_proveedores, indice_nombres)

    print(f'\n{"─" * 64}')
    print(f'  {len(rutas)} PDF(s) analizados')
    print(f'{"─" * 64}\n')
