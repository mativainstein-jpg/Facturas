import io
import re
import pdfplumber
from config import CUIT_NAIMAN, NOMBRE_NAIMAN, COLS, PUNTO_VENTA_FIJO


# ---------------------------------------------------------------------------
# Extracción de texto
# ---------------------------------------------------------------------------

def extraer_texto(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        paginas = [p.extract_text() or '' for p in pdf.pages]
    return '\n'.join(paginas)


# Etiqueta "Cód." del tipo de comprobante: algunos generadores (ej. Contabilium)
# la escriben con tilde ("Cód.") y/o con dos puntos ("Cód.: 11") en vez del
# "COD. 11" plano de AFIP.
_COD_TIPO = r'C[oó]d\.?\s*:?\s*0*1'


def es_texto_valido(texto):
    # Reusa _detectar_tipo (más abajo) para que cualquier mejora ahí
    # (nuevos formatos) también sirva acá, sin mantener 2 regex distintas.
    return bool(texto) and len(texto) > 100 and _detectar_tipo(texto) != ''


# ---------------------------------------------------------------------------
# Parser principal
# ---------------------------------------------------------------------------

def parsear_factura(texto, nombre_adjunto, indice_proveedores=None, pdf_bytes=None,
                    indice_nombres=None):
    tipo = _detectar_tipo(texto)
    linea = _extraer_linea_producto(texto, pdf_bytes)

    numero      = _campo(texto, r'Comp\.\s*Nro\.?:\s*0*(\d+)')   # ".?" tolera "Nro.:"
    punto_venta = PUNTO_VENTA_FIJO
    punto_venta_factura = _campo(texto, r'Punto\s*de\s*Venta:\s*0*(\d+)')
    if not numero or not punto_venta_factura:
        # Fallback: otros generadores (ej. Contabilium) no separan "Punto de
        # Venta" y "Comp. Nro" en dos campos, traen todo junto como
        # "Nº: 0008-00022470" o "NUMERO:0013 - 00002765".
        m = re.search(r'(?:NUMERO|N[°ºo]\.?|Factura\s*de\s*venta)\s*:?\s*0*(\d+)\s*-\s*0*(\d+)', texto, re.I)
        if m:
            if not punto_venta_factura:
                punto_venta_factura = m.group(1)
            if not numero:
                numero = m.group(2)
    if not punto_venta_factura:
        # Fallback: los PDF descargados de AFIP/ARCA se llaman
        # cuit_tipo_puntoventa_numero.pdf (ej. 20301648732_001_00003_00000096.pdf)
        m = re.search(r'\d{11}_\d{3}_0*(\d+)_\d{8}', nombre_adjunto or '')
        if m:
            punto_venta_factura = m.group(1)
    # Acepta también d/m/aaaa (algunos emisores no completan con ceros) y
    # espacios sueltos alrededor de las barras (ej. "1/ 7/2026", texto mal
    # justificado en el PDF original).
    _RE_FECHA = r'(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})'
    m = re.search(r'Fecha\s*de\s*Emisi[oó]n:\s*' + _RE_FECHA, texto, re.I)
    if not m:
        # Fallback: otros generadores usan "Fecha:" a secas (sin "de Emisión").
        # El \s* pegado a los ":" evita agarrar "Fecha Vto. CAE:" o similares.
        m = re.search(r'\bFecha\s*:\s*' + _RE_FECHA, texto, re.I)
    fecha = f'{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}' if m else ''

    denominacion_pdf = _extraer_denominacion(texto)
    cuit             = _extraer_cuit_emisor(texto)
    denominacion, denominacion_cruzada = _resolver_denominacion(
        cuit, denominacion_pdf, indice_nombres)

    # ":?" tolera "Subtotal 862.290,13" (algunos generadores no ponen ":")
    subtotal = _campo(texto, r'Subtotal\s*:?\s*\$?\s*([\d.,]+)') or _subtotal_linea(linea)
    neto     = _campo(texto, r'Importe\s*Neto\s*Gravado:\s*\$?\s*([\d.,]+)')
    if not neto:
        # Fallback: otros generadores no dicen "Importe Neto Gravado", solo
        # "Subtotal" (mismo concepto: el neto antes de IVA).
        neto = subtotal

    # Las 5 alícuotas de IVA que puede traer una factura A. "I\.?V\.?A\.?"
    # tolera tanto "IVA" como "I.V.A" (con puntos entre cada letra).
    # "[^\d\n]{0,30}" tolera texto corto entre el % y el monto (ej.
    # "IVA 21% Venta de Bs. 181.080,93"), sin permitir saltar de más.
    _IVA = r'I\.?V\.?A\.?\s*'
    # El monto capturado tiene que EMPEZAR con un dígito (\d[\d.,]*), para
    # no agarrar de "monto" un punto suelto de alguna abreviatura en el
    # medio (ej. "Bs." en "IVA 21% Venta de Bs. 181.080,93").
    _HASTA_MONTO = r'[^\d\n]{0,30}?\$?\s*(\d[\d.,]*)'
    iva25  = _campo(texto, _IVA + r'2[.,]5%' + _HASTA_MONTO)
    iva5   = _campo(texto, _IVA + r'5%' + _HASTA_MONTO)
    iva105 = _campo(texto, _IVA + r'10[.,]5%' + _HASTA_MONTO)
    iva21  = _campo(texto, _IVA + r'21%' + _HASTA_MONTO)
    iva27  = _campo(texto, _IVA + r'27%' + _HASTA_MONTO)
    otros  = _campo(texto, r'Importe\s*de\s*Otros\s*Tributos:\s*\$?\s*([\d.,]+)')

    total = _campo(texto, r'Importe\s*Total(?:\s*del\s*Comprobante)?:\s*\$?\s*([\d.,]+)')
    if not total:
        # Fallback: otros generadores usan "TOTAL:" a secas, o "MONTO TOTAL"
        # sin dos puntos. \b evita que "TOTAL:" "matchee" dentro de "SUBTOTAL:".
        total = _campo(texto, r'\bTOTAL:\s*\$?\s*([\d.,]+)') \
             or _campo(texto, r'MONTO\s*TOTAL\s*\$?\s*([\d.,]+)')
    if not total and tipo == 'FCC':
        total = _subtotal_linea(linea)

    # Campos de percepción e impuestos adicionales
    no_gravado     = _campo(texto, r'Importe\s*No\s*Gravado:\s*\$?\s*([\d.,]+)')
    imp_internos   = _campo(texto, r'Impuestos?\s*Internos?:\s*\$?\s*([\d.,]+)')
    exentos        = _campo(texto, r'Importe\s*Exento[s]?:\s*\$?\s*([\d.,]+)')
    perc_iva       = _campo(texto, r'Percepci[oó]n\s*(?:de\s*)?IVA\s*(?:[\d.,]+\s*%)?\s*:?\s*\$?\s*([\d.,]+)')
    perc_iibb      = _campo(texto, r'Percepci[oó]n\s*(?:de\s*)?(?:Ingresos?\s*Brutos?|IIBB)\s*(?:[\d.,]+\s*%)?\s*:?\s*\$?\s*([\d.,]+)')
    if not perc_iibb:
        # Fallback: "Perc. IIBB <Provincia> (código) monto", que puede
        # repetirse varias veces (una por jurisdicción) — se suman todas.
        perc_iibb = _campo_suma(texto, r'Perc\.?\s*IIBB\s*[A-Za-zÀ-ÿ\s]*?\(\d+\)\s*([\d.,]+)')
    perc_ganancias = _campo(texto, r'Percepci[oó]n\s*(?:de\s*)?Ganancias?\s*(?:[\d.,]+\s*%)?\s*:?\s*\$?\s*([\d.,]+)')

    kilos      = _kilos_linea(linea)
    precio_raw = _precio_unitario_linea(linea) or _campo(texto, r'Precio\s*Unit\.?\s+([\d.,]+)')

    # None = no encontrado en el PDF (mostrar VERIFICAR en la UI)
    # 0.0  = encontrado pero es cero (dato real)
    kilos_num    = _num_o_none(kilos)
    neto_num     = _num_o_none(neto) if tipo == 'FCA' else 0.0
    subtotal_num = _num(subtotal)
    ivas = [(2.5, _num(iva25)), (5, _num(iva5)), (10.5, _num(iva105)),
            (21, _num(iva21)), (27, _num(iva27))]
    iva_num      = sum(monto for _, monto in ivas) or (None if tipo == 'FCA' else 0.0)
    total_num    = _num_o_none(total)
    precio_num   = _num(precio_raw)

    # Tasa de IVA: monotributista (FCC) siempre 0; en factura A, la única
    # alícuota con importe > 0. Si hay varias (factura mixta) o ninguna,
    # queda None → VERIFICAR, en vez de elegir una en silencio.
    if tipo == 'FCC':
        tasa = 0
    elif tipo == 'FCA':
        con_importe = [alicuota for alicuota, monto in ivas if monto > 0]
        tasa = con_importe[0] if len(con_importe) == 1 else None
    else:
        tasa = None

    if precio_num and precio_num > 0:
        precio_unitario_num = precio_num
    elif tipo == 'FCC' and kilos_num and kilos_num > 0 and subtotal_num > 0:
        precio_unitario_num = subtotal_num / kilos_num
    elif tipo == 'FCA' and kilos_num and kilos_num > 0 and neto_num and neto_num > 0:
        precio_unitario_num = neto_num / kilos_num
    else:
        precio_unitario_num = None

    partes_fecha = fecha.split('/') if fecha else []
    mes  = int(partes_fecha[1]) if len(partes_fecha) > 1 else None
    anio = int(partes_fecha[2]) if len(partes_fecha) > 2 else None

    # Cruce con proveedores para gasto / rubro
    prov = None
    if indice_proveedores and cuit:
        cuit_num = re.sub(r'\D', '', cuit)
        prov = indice_proveedores.get(cuit_num)

    gasto      = prov['gasto']      if prov else None
    rubro      = prov['rubro']      if prov else None
    desc_gasto = prov['desc_gasto'] if prov else None
    desc_rubro = prov['desc_rubro'] if prov else None

    posicion       = 'RM' if tipo == 'FCC' else ('RI' if tipo == 'FCA' else '')
    # En factura C (monotributista) no se discrimina IVA: en esta columna va
    # el importe total. En factura A queda vacía.
    monotributista = total_num if tipo == 'FCC' else None

    # El punto de venta REAL distingue facturas de un mismo proveedor con
    # igual número pero distinto PV (con el fijo se marcaban como duplicadas
    # y la segunda no se cargaba).
    clave = '|'.join([
        tipo or 'SIN_TIPO',
        cuit or 'SIN_CUIT',
        punto_venta_factura or punto_venta or 'SIN_PV',
        numero or 'SIN_NUMERO',
    ])

    return {
        'tipo':                    tipo   or None,
        'numero':                  numero or None,
        'punto_venta':             punto_venta,   # default '4' si no se extrae
        'punto_venta_factura':     punto_venta_factura or None,  # el que trae la factura
        'fecha':                   fecha  or None,
        'denominacion':            denominacion or None,
        'denominacion_cruzada':    denominacion_cruzada,  # True si vino del cruce CUIT->nombre
        'cuit':                    cuit   or None,
        'neto_num':                neto_num,
        'iva_num':                 iva_num,
        'otros_tributos_num':      _num_o_none(otros),
        'no_gravado_num':          _num_o_none(no_gravado),
        'imp_internos_num':        _num_o_none(imp_internos),
        'exentos_num':             _num_o_none(exentos),
        'percepcion_iva_num':      _num_o_none(perc_iva),
        'percepcion_iibb_num':     _num_o_none(perc_iibb),
        'percepcion_ganancias_num': _num_o_none(perc_ganancias),
        'kilos_num':               kilos_num,
        'precio_unitario_num':     precio_unitario_num,
        'monotributista':          monotributista,
        'total_num':               total_num,
        'tasa':                    tasa,
        'gasto':                   gasto,
        'rubro':                   rubro,
        'mes':                     mes,
        'anio':                    anio,
        'codigo_operacion':        '',
        'posicion':                posicion,
        'descripcion_gasto':       desc_gasto,
        'descripcion_rubro':       desc_rubro,
        'nombre_adjunto':          nombre_adjunto,
        'clave':                   clave,
    }


# ---------------------------------------------------------------------------
# Extracción de línea de producto — cascada de 3 estrategias
# ---------------------------------------------------------------------------

def _extraer_linea_producto(texto, pdf_bytes=None):
    # 1. pdfplumber table extraction (best for structured AFIP tables)
    if pdf_bytes:
        result = _extraer_de_tablas(pdf_bytes)
        if result:
            return result

    # 2. Single-line regex (works when pdfplumber reconstructs row layout)
    result = _extraer_linea_single(texto)
    if result:
        return result

    # 3. Multi-line anchor-based search (fallback for column-per-line layouts)
    return _extraer_multilinea(texto)


def _extraer_de_tablas(pdf_bytes):
    """Use pdfplumber table detection to find the product row."""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                for table in (page.extract_tables() or []):
                    for row in table:
                        if not row:
                            continue
                        cells = [str(c).strip() if c else '' for c in row]
                        row_str = ' '.join(cells)
                        m = re.search(r'([\d.,]+)\s*(kg|kilos|unidad(?:es)?)', row_str, re.I)
                        if not m:
                            continue
                        cantidad = m.group(1)
                        raw_unit = m.group(2).lower()
                        unidad   = 'kg' if 'kg' in raw_unit or 'kilo' in raw_unit else 'unidades'
                        nums     = re.findall(r'[\d.,]+', row_str)
                        # Last two numbers are typically unit price and line total
                        precio   = nums[-2] if len(nums) >= 3 else (nums[-1] if len(nums) >= 2 else '')
                        subtotal = nums[-1] if len(nums) >= 2 else ''
                        return {
                            'descripcion':     '',
                            'cantidad':        cantidad,
                            'unidad':          unidad,
                            'precio_unitario': precio,
                            'subtotal':        subtotal,
                        }
    except Exception:
        pass
    return None


def _extraer_linea_single(texto):
    """Single-line regex — works when pdfplumber merges table columns into one line."""
    for linea in texto.splitlines():
        linea = linea.strip()

        m = re.match(
            r'(.+?)\s+([\d.,]+)\s+(kg|kilos|unidad(?:es)?)'
            r'\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)%\s+([\d.,]+)',
            linea, re.I
        )
        if m:
            return {
                'descripcion':     m.group(1).strip(),
                'cantidad':        m.group(2),
                'unidad':          m.group(3).lower(),
                'precio_unitario': m.group(4),
                'subtotal':        m.group(6),
            }

        m = re.match(
            r'(.+?)\s+([\d.,]+)\s+(kg|kilos|unidad(?:es)?)'
            r'\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)',
            linea, re.I
        )
        if m:
            return {
                'descripcion':     m.group(1).strip(),
                'cantidad':        m.group(2),
                'unidad':          m.group(3).lower(),
                'precio_unitario': m.group(4),
                'subtotal':        m.group(7),
            }

    return None


def _extraer_multilinea(texto):
    """
    Anchor-based fallback for PDFs where each table column appears on its own line.

    Uses "Precio Unit." as anchor:
      - scan BACKWARD → first standalone number = quantity
      - scan FORWARD  → first standalone number = unit price

    This handles both orderings found in the wild:
      Layout A: quantity … "Precio Unit." … price  (BUZZATTO / ALASINO)
      Layout B: quantity   "Precio Unit."   price   (LEFFLER)
    """
    lineas = [l.strip() for l in texto.splitlines()]

    precio_unitario   = ''
    cantidad          = ''
    unidad_encontrada = 'kg'

    # Find "Precio Unit." line
    precio_idx = -1
    for i, linea in enumerate(lineas):
        m = re.match(r'^Precio\s*Unit\.?\s*([\d.,]+)?$', linea, re.I)
        if m:
            precio_idx = i
            if m.group(1):
                precio_unitario = m.group(1)
            break

    if precio_idx < 0:
        return None

    # Scan backward for quantity (skip labels, take first standalone number)
    for j in range(precio_idx - 1, max(precio_idx - 15, -1), -1):
        cand = lineas[j]
        if re.match(r'^[\d.,]+$', cand) and _num(cand) > 0:
            cantidad = cand
            break

    # Scan forward for price if not already on the same line
    if not precio_unitario:
        for j in range(precio_idx + 1, min(precio_idx + 8, len(lineas))):
            if re.match(r'^[\d.,]+$', lineas[j]) and _num(lineas[j]) > 0:
                precio_unitario = lineas[j]
                break

    # Detect unit (scan nearby lines for kg / unidades)
    search_start = max(0, precio_idx - 15)
    search_end   = min(len(lineas), precio_idx + 10)
    for linea in lineas[search_start:search_end]:
        if re.match(r'^(kg|kilos)$', linea, re.I):
            unidad_encontrada = 'kg'
            break
        if re.match(r'^unidad(?:es)?$', linea, re.I):
            unidad_encontrada = 'unidades'
            break
        m = re.search(r'([\d.,]+)\s+(kg|kilos|unidad(?:es)?)', linea, re.I)
        if m:
            raw = m.group(2).lower()
            unidad_encontrada = 'kg' if 'kg' in raw or 'kilo' in raw else 'unidades'
            if not cantidad:
                cantidad = m.group(1)
            break

    if not cantidad and not precio_unitario:
        return None

    return {
        'descripcion':     '',
        'cantidad':        cantidad,
        'unidad':          unidad_encontrada,
        'precio_unitario': precio_unitario,
        'subtotal':        '',
    }


# ---------------------------------------------------------------------------
# Helpers secundarios
# ---------------------------------------------------------------------------

def _kilos_linea(linea):
    if not linea:
        return ''
    return linea['cantidad'] if linea['unidad'] in ('kg', 'kilos', 'unidad', 'unidades') else ''


def _precio_unitario_linea(linea):
    return linea['precio_unitario'] if linea else ''


def _subtotal_linea(linea):
    return linea['subtotal'] if linea else ''


def _detectar_tipo(texto):
    if re.search(_COD_TIPO + r'1', texto, re.I):      return 'FCC'   # ...11
    if re.search(_COD_TIPO + r'(?!1)', texto, re.I):  return 'FCA'   # ...1 (no 11)

    # Fallback: cuando el PDF tiene columnas superpuestas (ej. GRECA S.A.),
    # pdfplumber puede desordenar "CODIGO" y el número "01"/"11" a varias
    # líneas de distancia, rompiendo el patrón de arriba. La letra grande
    # del recuadro (obligatoria por ley en toda factura A/B/C) suele quedar
    # pegada a la palabra "FACTURA" — se busca solo cerca del inicio del
    # documento para no confundirla con una A/C suelta en el cuerpo.
    m = re.search(r'\b([AC])\b\s*FACTURA|FACTURA\s*\b([AC])\b', texto[:400], re.I)
    if m:
        letra = (m.group(1) or m.group(2)).upper()
        return 'FCA' if letra == 'A' else 'FCC'

    # Fallback: otros generadores (ej. "Factura de venta") ponen el título
    # y la letra en líneas separadas por otro texto en el medio (no pegados
    # como arriba). Se busca una línea que sea SOLO "A" o "C" cerca del
    # inicio del documento.
    m = re.search(r'^\s*([AC])\s*$', texto[:400], re.M)
    if m:
        letra = m.group(1).upper()
        return 'FCA' if letra == 'A' else 'FCC'

    return ''


def _extraer_denominacion(texto):
    # Algunos generadores (ej. Contabilium) usan "Razón Social:" para el
    # RECEPTOR (nosotros mismos), no para el proveedor. Si el primer match
    # es NAIMAN, se descarta y se sigue buscando otro (o se cae al fallback
    # de letterhead más abajo).
    for m in re.finditer(r'Raz[oó]n\s*Social:\s*([A-ZÁÉÍÓÚÑ0-9 .,\-]+)', texto, re.I):
        nombre = _limpiar_texto(m.group(1))
        if NOMBRE_NAIMAN.upper() not in nombre.upper():
            return nombre

    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    for i, linea in enumerate(lineas):
        if re.match(r'^(ORIGINAL|DUPLICADO|TRIPLICADO)$', linea, re.I):
            nombre = lineas[i + 1] if i + 1 < len(lineas) else ''
            siguiente = lineas[i + 2] if i + 2 < len(lineas) else ''
            if siguiente and not re.match(
                r'^\d|CUIT|Condici[oó]n|Domicilio|Contado|Cuenta|Entre R[ií]os|Santa Fe|Buenos Aires',
                siguiente, re.I
            ):
                nombre += ' ' + siguiente
            return _limpiar_texto(nombre)

    return ''


def _extraer_cuit_emisor(texto):
    for m in re.finditer(r'\b\d{2}-\d{8}-\d\b', texto):
        limpio = re.sub(r'\D', '', m.group())
        if limpio != CUIT_NAIMAN:
            return _normalizar_cuit(limpio)

    for m in re.finditer(r'\b\d{11}\b', texto):
        if m.group() != CUIT_NAIMAN:
            return _normalizar_cuit(m.group())

    return ''


def _resolver_denominacion(cuit, denominacion_pdf, indice_nombres):
    """
    Devuelve (nombre, cruzada):
      - Primero cruza el CUIT contra cuit_nombre.xlsx. Si lo encuentra,
        usa ESE nombre (cruzada=True).
      - Si no está en el cruce, usa el nombre leído de la factura
        (cruzada=False → se marca en rojo en el Excel).
    """
    if indice_nombres and cuit:
        cuit_num = re.sub(r'\D', '', cuit)
        nombre = indice_nombres.get(cuit_num)
        if nombre:
            return nombre, True
    return (denominacion_pdf or ''), False


def _campo(texto, patron):
    m = re.search(patron, texto, re.I)
    return m.group(1).strip() if m else ''


def _campo_suma(texto, patron):
    """Como _campo, pero suma TODOS los montos que matcheen (para importes
    que se repiten varias veces en la misma factura, ej. percepción de
    IIBB discriminada por provincia)."""
    valores = [_num(m.group(1)) for m in re.finditer(patron, texto, re.I)]
    # Formato fijo a 2 decimales: el float "crudo" (ej. 30180.160000000003,
    # error de coma flotante) hace que _num() lo confunda con separador de
    # miles y lo multiplique por mil millones.
    return f'{sum(valores):.2f}' if valores else ''


def _num_o_none(s):
    """Like _num() but returns None when the string is absent/empty."""
    if not s or str(s).strip() == '':
        return None
    return _num(s)


def _num(s):
    if not s:
        return 0.0
    s = str(s).replace(' ', '').replace('$', '').strip()
    if not s:
        return 0.0

    if '.' in s and ',' in s:
        # El separador DECIMAL es el que aparece último: formato AR
        # ("1.234,56", coma al final) o formato US ("1,234.56", punto al
        # final) — algunos generadores (ej. GRECA S.A.) usan el segundo.
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')   # AR: 1.234,56 -> 1234.56
        else:
            s = s.replace(',', '')                     # US: 1,234.56 -> 1234.56
    elif ',' in s:
        s = s.replace(',', '.')
    elif '.' in s:
        partes = s.split('.')
        if len(partes) > 2 or len(partes[-1]) >= 3:
            s = s.replace('.', '')

    try:
        return float(s)
    except ValueError:
        return 0.0


def _normalizar_cuit(cuit):
    c = re.sub(r'\D', '', str(cuit))
    return f'{c[:2]}-{c[2:10]}-{c[10]}' if len(c) == 11 else cuit


def _limpiar_texto(texto):
    if not texto:
        return ''
    texto = re.sub(r'\s+', ' ', str(texto))
    # Cortar en cualquier campo AFIP que aparezca pegado al nombre. Se busca
    # por tokens SIN acento ("Fecha", "Condici") en vez de "Emisión"/"Condición",
    # para que el corte funcione aunque el acento venga codificado distinto
    # (tilde combinada) — que es lo que dejaba "Fecha de Emisión" en el nombre.
    texto = re.sub(r'\s*Fecha\b.*',            '', texto, flags=re.I)
    texto = re.sub(r'\s*CUIT.*',               '', texto, flags=re.I)
    texto = re.sub(r'\s*Condici.*',            '', texto, flags=re.I)
    texto = re.sub(r'\s*Domicilio.*',          '', texto, flags=re.I)
    texto = re.sub(r'\s*Punto\s*de\s*Venta.*', '', texto, flags=re.I)
    texto = re.sub(r'\s*Ingresos\s*Brutos.*',  '', texto, flags=re.I)
    return texto.strip(' .,-')
