#!/usr/bin/env python3
"""
Pruebas automáticas del lector de facturas (sin PDFs reales ni Excel).

Usa textos armados con el mismo formato que extrae pdfplumber de una factura
AFIP, y verifica que se lean bien los datos. Sirve para que un arreglo nuevo
no rompa lo que ya andaba.

Uso:
    python pruebas/test_parser_textos.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pdf_parser as P  # noqa: E402

FACTURA_A = """ORIGINAL
A
FACTURA
COD. 01
AGRO PROVEEDOR SA
Razón Social: AGRO PROVEEDOR SA
Punto de Venta: 00003 Comp. Nro: 00000096
Fecha de Emisión: 15/09/2026
CUIT: 30-71234567-1
Ingresos Brutos: 123
CUIT: 33708955499
Apellido y Nombre / Razón Social: NAIMAN SA
Código Producto / Servicio Cantidad U. Medida Precio Unit. % Bonif Subtotal Alícuota IVA Subtotal c/IVA
Harina de trigo 1.000,00 kilogramos 100,00 0,00 100.000,00 21% 121.000,00
Importe Neto Gravado: $ 100.000,00
IVA 27%: $ 0,00
IVA 21%: $ 21.000,00
IVA 10.5%: $ 0,00
Importe Otros Tributos: $ 0,00
Importe Total: $ 121.000,00
CAE N°: 76123456789012
"""

FACTURA_C = """ORIGINAL
C
FACTURA
COD. 011
JUAN PEREZ
Razón Social: JUAN PEREZ
Punto de Venta: 00002 Comp. Nro: 00000045
Fecha de Emisión: 01/10/2026
CUIT: 20-30164873-2
CUIT: 33708955499
Código Producto / Servicio Cantidad U. Medida Precio Unit. % Bonif Imp. Bonif. Subtotal
Flete 10,00 unidades 5.000,00 0,00 0,00 50.000,00
Subtotal: $ 50.000,00
Importe Otros Tributos: $ 0,00
Importe Total: $ 50.000,00
CAE N°: 76123456789013
"""


def _con(texto, viejo, nuevo):
    assert viejo in texto, viejo
    return texto.replace(viejo, nuevo)


FALLAS = []


def chequear(nombre, obtenido, esperado):
    ok = obtenido == esperado
    print(f'  {"OK " if ok else "MAL"}  {nombre}: {obtenido!r}' + ('' if ok else f'  (esperado {esperado!r})'))
    if not ok:
        FALLAS.append(nombre)


def parse(texto, nombre='f.pdf'):
    return P.parsear_factura(texto, nombre)


def test_tipos():
    print('\nTipos de comprobante')
    chequear('Factura A', parse(FACTURA_A)['tipo'], 'FCA')
    chequear('Factura C', parse(FACTURA_C)['tipo'], 'FCC')
    chequear('Nota de Crédito A (COD 03)',
             parse(_con(FACTURA_A, 'FACTURA\nCOD. 01', 'NOTA DE CREDITO\nCOD. 03'))['tipo'], 'NCA')
    chequear('Nota de Débito A (COD 02)',
             parse(_con(FACTURA_A, 'COD. 01', 'COD. 02'))['tipo'], 'NDA')
    chequear('Nota de Crédito C (COD 13)',
             parse(_con(FACTURA_C, 'COD. 011', 'COD. 013'))['tipo'], 'NCC')
    chequear('Nota de Débito C (COD 12)',
             parse(_con(FACTURA_C, 'COD. 011', 'COD. 012'))['tipo'], 'NDC')
    chequear('FCE MiPyME A (COD 201)',
             parse(_con(FACTURA_A, 'COD. 01', 'COD. 201'))['tipo'], 'FCA')
    chequear('Cód.: 11 con tilde (Contabilium)',
             parse(_con(FACTURA_C, 'COD. 011', 'Cód.: 11'))['tipo'], 'FCC')
    raro = _con(FACTURA_A, 'COD. 01', 'COD. 51')
    chequear('Código no conocido (51) → se lee pero tipo vacío (VERIFICAR)',
             (P.es_texto_valido(raro), parse(raro)['tipo']), (True, None))
    sin_cod_nc = _con(FACTURA_A, 'FACTURA\nCOD. 01', 'NOTA DE CREDITO')
    chequear('Sin código, letra A + "NOTA DE CREDITO"', parse(sin_cod_nc)['tipo'], 'NCA')
    sin_cod = _con(FACTURA_C, 'COD. 011\n', '')
    chequear('Sin código, letra C sola', parse(sin_cod)['tipo'], 'FCC')
    nc = parse(_con(FACTURA_C, 'COD. 011', 'COD. 013'))
    chequear('NC C: posición y monotributista como factura C',
             (nc['posicion'], nc['monotributista'], nc['tasa']), ('RM', 50000.0, 0))


def test_importes():
    print('\nImportes y línea de producto')
    a = parse(FACTURA_A)
    chequear('A: neto', a['neto_num'], 100000.0)
    chequear('A: IVA', a['iva_num'], 21000.0)
    chequear('A: total', a['total_num'], 121000.0)
    chequear('A: tasa', a['tasa'], 21)
    chequear('A: kilos con unidad "kilogramos"', a['kilos_num'], 1000.0)
    chequear('A: precio unitario', a['precio_unitario_num'], 100.0)
    c = parse(FACTURA_C)
    chequear('C: total', c['total_num'], 50000.0)
    chequear('C: cantidad', c['kilos_num'], 10.0)
    chequear('C: precio unitario', c['precio_unitario_num'], 5000.0)
    otras = _con(FACTURA_C, '10,00 unidades', '10,00 otras unidades')
    chequear('C: "otras unidades"', parse(otras)['kilos_num'], 10.0)


def test_precio_tabla():
    print('\nFila de tabla (pdfplumber): precio y subtotal')
    # Antes se tomaba el anteúltimo número: en la A era la alícuota (21)
    chequear('Fila factura A', P._precio_y_subtotal(' 100,00 0,00 100.000,00 21% 121.000,00'),
             ('100,00', '100.000,00'))
    chequear('Fila factura C', P._precio_y_subtotal(' 5.000,00 0,00 0,00 50.000,00'),
             ('5.000,00', '50.000,00'))
    chequear('Fila con %bonif marcado', P._precio_y_subtotal(' 80,00 5,00% 4,00 76,00'),
             ('80,00', '76,00'))


def test_copias_y_moneda():
    print('\nCopias del PDF y moneda')
    perc = _con(FACTURA_A, 'Importe Otros Tributos', 'Perc. IIBB Santa Fe (921) 1.500,00\nImporte Otros Tributos')
    triple = perc + perc.replace('ORIGINAL', 'DUPLICADO') + perc.replace('ORIGINAL', 'TRIPLICADO')
    chequear('IIBB con ORIGINAL+DUPLICADO+TRIPLICADO (no se triplica)',
             parse(triple)['percepcion_iibb_num'], 1500.0)
    dos_prov = _con(FACTURA_A, 'Importe Otros Tributos',
                    'Perc. IIBB Santa Fe (921) 1.500,00\nPerc. IIBB Entre Rios (908) 500,00\nImporte Otros Tributos')
    chequear('IIBB de dos provincias (se suman)', parse(dos_prov)['percepcion_iibb_num'], 2000.0)
    chequear('Factura en pesos', parse(FACTURA_A)['moneda_extranjera'], False)
    usd = FACTURA_A + ('El total de este comprobante ha sido expresado en Dólar Estadounidense '
                       'considerándose un tipo de cambio consignado de 1.050,50\n')
    d = parse(usd)
    chequear('Factura en dólares detectada', (d['moneda_extranjera'], d['tipo_cambio']), (True, 1050.5))
    chequear('"Moneda: USD"', parse(FACTURA_A + 'Moneda: USD\n')['moneda_extranjera'], True)


def test_clave():
    print('\nClave de duplicados')
    a = parse(FACTURA_A)
    chequear('Clave completa', a['clave'], 'FCA|30-71234567-1|3|96')
    chequear('Clave completa es válida', P.clave_completa(a['clave']), True)
    chequear('Clave con SIN_NUMERO no cuenta', P.clave_completa('FCA|30-71234567-1|3|SIN_NUMERO'), False)
    chequear('armar_clave', P.armar_clave('NCC', '20-30164873-2', '2', '45'), 'NCC|20-30164873-2|2|45')


def test_numeros():
    print('\nNúmeros')
    chequear('1.234,56 (AR)', P._num('1.234,56'), 1234.56)
    chequear('1,234.56 (US)', P._num('1,234.56'), 1234.56)
    chequear('100.000', P._num('100.000'), 100000.0)


def test_fila_excel():
    print('\nFila del Excel')
    try:
        import excel_manager as E
    except ImportError:
        print('  (sin openpyxl: se saltea)')
        return
    from config import COLS
    nc = parse(_con(FACTURA_C, 'COD. 011', 'COD. 013'))
    nc.update(gasto=1, rubro=1)
    fila, rojas = E._armar_fila_verificada(nc)
    chequear('NC con NC_EN_NEGATIVO=False: total positivo', fila[COLS['TOTAL'] - 1], 50000.0)
    E.NC_EN_NEGATIVO = True
    try:
        fila, rojas = E._armar_fila_verificada(nc)
    finally:
        E.NC_EN_NEGATIVO = False
    chequear('NC con NC_EN_NEGATIVO=True: total negativo', fila[COLS['TOTAL'] - 1], -50000.0)
    chequear('NC con NC_EN_NEGATIVO=True: total no queda en rojo', COLS['TOTAL'] in rojas, False)
    usd = parse(FACTURA_A + 'Moneda: USD\n')
    usd.update(gasto=1, rubro=1)
    fila, rojas = E._armar_fila_verificada(usd)
    chequear('Dólares: total en rojo pero con el número', (COLS['TOTAL'] in rojas, fila[COLS['TOTAL'] - 1]),
             (True, 121000.0))
    a = parse(FACTURA_A)
    a.update(gasto=1, rubro=1)
    fila, rojas = E._armar_fila_verificada(a)
    chequear('Factura A completa: sin celdas rojas salvo nombre no cruzado',
             rojas, [COLS['DENOMINACION']])


if __name__ == '__main__':
    test_tipos()
    test_importes()
    test_precio_tabla()
    test_copias_y_moneda()
    test_clave()
    test_numeros()
    test_fila_excel()
    print()
    if FALLAS:
        print(f'FALLARON {len(FALLAS)} prueba(s): {", ".join(FALLAS)}')
        sys.exit(1)
    print('Todas las pruebas OK')
