import sys
from pathlib import Path

# Cuando corre como .exe (PyInstaller frozen), los archivos de datos
# van junto al ejecutable, no dentro del bundle comprimido.
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

CUIT_NAIMAN = '33708955499'
PUNTO_VENTA_FIJO = '4'   # todas las facturas se cargan con este punto de venta
LABEL_PROCESADO = 'Procesado'

EXCEL_FACTURAS   = BASE_DIR / 'facturas.xlsx'
EXCEL_PROVEEDORES = BASE_DIR / 'proveedores.xlsx'
JSON_ESTADO      = BASE_DIR / 'estado.json'
CREDENTIALS_FILE = BASE_DIR / 'credentials.json'
TOKEN_FILE       = BASE_DIR / 'token.json'

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Columnas del Excel (1-indexed), coinciden con Registro_de_facturas.xlsx
COLS = {
    'TIPO_COMPROBANTE':      1,   # A  - Tipo
    'NUMERO':                2,   # B  - Número Desde
    'PUNTO_VENTA':           3,   # C  - Punto de Venta
    'FECHA':                 4,   # D  - Fecha
    'DENOMINACION':          5,   # E  - Denominación
    'CUIT':                  6,   # F  - CUIT
    'NETO':                  7,   # G  - Neto gravado
    'IVA':                   8,   # H  - Iva
    'NO_GRAVADO':            9,   # I  - No gravado
    'IMP_INTERNOS':         10,   # J  - Imp. Internos
    'EXENTOS':              11,   # K  - Exentos
    'PERCEPCION_IVA':       12,   # L  - Percepción IVA
    'PERCEPCION_IIBB':      13,   # M  - Percepción IIBB
    'KILOS':                14,   # N  - Kilos
    'PRECIO_UNITARIO':      15,   # O  - Precio unitario
    'MONOTRIBUTISTA':       16,   # P  - Monotributista
    'PERCEPCION_GANANCIAS': 17,   # Q  - Percepción Ganancias
    'TOTAL':                18,   # R  - Total
    'TASA':                 19,   # S  - Tasa
    'GASTO':                20,   # T  - Gasto
    'RUBRO':                21,   # U  - Rubro
    'MES_IMPUTACION':       22,   # V  - Mes de imputación
    'ANIO_IMPUTACION':      23,   # W  - Año imputación
    'CODIGO_OPERACION':     24,   # X  - Código de operación
    'POSICION':             25,   # Y  - Posición
    #                       26    # Z  (vacío)
    'DESCRIPCION_GASTO':    27,   # AA - Descripción gasto
    'DESCRIPCION_RUBRO':    28,   # AB - Descripción rubro
    #                       29    # AC (vacío)
    # Columnas ocultas (sin encabezado visible) — solo para control de duplicados
    'NOMBRE_ADJUNTO':       30,   # AD
    'CLAVE_COMPROBANTE':    31,   # AE
}

NUM_COLS = 31

# Encabezados visibles de la hoja FACTURAS (cols 1-29, None = columna vacía)
HEADERS_FACTURAS = [
    'Tipo', 'Número Desde', 'Punto de Venta', 'Fecha',
    'Denominación', 'CUIT', 'Neto gravado', 'Iva', 'No gravado',
    'Imp. Internos', 'Exentos', 'Percepción IVA', 'Percepción IIBB',
    'Kilos', 'Precio unitario', 'Monotributista', 'Percepción Ganancias',
    'Total', 'Tasa', 'Gasto', 'Rubro', 'Mes de imputación', 'Año imputación',
    'Código de operación', 'Posición', None, 'Descripción gasto',
    'Descripción rubro', None,
]

# Listados oficiales (Matriz de Gastos / Rubros de Compras de Naiman S.A.,
# emitidos 03/06/2026). Se usan para completar Descripción gasto/rubro sin
# depender de que proveedores.xlsx tenga ese texto cargado fila por fila
# (la mayoría de las filas no lo tenían).
GASTOS_DESC = {
    1: 'INSUMOS VARIOS', 2: 'GASTOS FINANCIEROS', 3: 'INS PLANT', 4: 'MIEL',
    5: 'SS MANTEN', 6: 'HONORARIO Y SS TECN', 7: 'SEMILLA', 8: 'POROTO NEGRO',
    9: 'SERIVICIOS VARIOS', 10: 'SERV SANT Y SENASA', 11: 'SS MONITOREO',
    12: 'FLETES TERRESTRES', 13: 'ENVS DOY PAC', 14: 'CARGAS FISCALES',
    15: 'INS OFICINA', 16: 'FLETE MARITIMO', 17: 'SERVICIO DE DISEÑO',
    18: 'COMIS POR COMPRA', 19: 'SEG SEMILLAS', 20: 'GTOS SEMILLAS',
    21: 'REPARAC Y MANT RODAD', 22: 'VIATICOS', 23: 'COMBUSTIBLES',
    24: 'SERV DE DESPACHANTE', 25: 'GASTOS PORTUARIOS', 26: 'LINO',
    27: 'DERECHOS DE EXPORTAC', 28: 'GAS Y GLP', 29: 'SS COSECHA',
    30: 'BIENES DE USO', 31: 'GIRASOL', 32: 'MUEBLES Y UTILES',
    33: 'ENCOMIENDAS Y CORREO', 34: 'PEAJE', 35: 'ARRENDAMIENTOS',
    36: 'SERVICIO DE BALANZA', 37: 'ANALISIS DE LABORATO', 38: 'CHIA',
    39: 'SEGUROS', 40: 'SICNEA', 41: 'LUZ-TELEF-INTERNET', 42: 'POROTO ROJO',
    43: 'CRISTAL ENVA', 44: 'SS HOSPEDAJE', 45: 'PARTICIPACIÓN FERIAS',
    46: 'INSUM AGRO', 47: 'GARBANZOS', 48: 'ZAPALLO', 49: 'CERTIFICACI',
    50: 'TAMBORES', 51: 'SS SIEMBRA', 52: 'COMISIION MIEL', 53: 'FUMIGACION',
    54: 'SERV. AGROPECUARIOS', 55: 'INDM, SEG/HIG,ALIMEN', 56: 'BOLSONES',
    57: 'MATERIALES Y FERRETE', 58: 'AUDITORIAS Y CERT', 59: 'BOLSONES',
    60: 'EXAMEN LABORAL', 61: 'GTO FERIAS INT', 62: 'SS ENBOL SEM',
    63: 'MATAFUEGOS', 64: 'POLEN', 65: 'TAMBORES ACOND', 66: 'VISITAS',
    67: 'ESPARCIMIENTO', 68: 'ART. LIMPIEZA', 69: 'ALIMENTOS', 70: 'SEGURO',
    71: 'EMBALAJES VARIOS', 72: 'GTO IMPORT', 73: 'FLETES AEREOS',
    74: 'COMISIONES DE VENTA', 75: 'CURSOS CAPACITACION', 76: 'REG EMPRESAE',
    77: 'LOCACIONES', 78: 'SOJA', 79: 'PIEDRA BASA', 80: 'ASES TECNIC',
    81: 'COSTAS JUDICIALES', 82: 'GTOS FCROSS$S', 83: 'JARABE DE FRUCTUOSA',
    84: 'DCHOS DE INVENCION', 85: 'ANALISIS DEL EX', 86: '1722 CAMION',
    87: 'SCANNIA', 88: 'ALOJAMIENTO', 89: 'ETIQUETAS', 90: 'JALEA REAL',
    91: 'GTO REPRESENTACION', 92: 'POROTO MUNG', 93: 'SERVICIOS PORTUARIOS',
    94: 'CORIANDRO', 95: 'DIFERENCIAS DE CAMBI', 96: 'REP Y MANT INMUEBLE',
    97: 'DERECHOS IMPO', 98: 'SUELDOS Y LEYES SOC', 99: 'FLETES TERR EXP- IMP',
    100: 'REP/MANT MAQ Y EQUIP', 101: 'POROTO BLANCO', 102: 'IMPUESTO AUTOMOTOR',
    103: 'INSUMOS AGROPECUARIO', 104: 'ANT IMP GAN EXPO', 105: 'CONSTRUCCION VARIAS',
    106: 'CERA', 107: 'SERVICIOS LOGÍSTICA', 108: 'GLIFOSATO',
    109: 'LIQUIDACION CUENTA Y...', 110: 'MAIZ', 111: 'DONACIONES', 112: 'ARVEJA',
}

RUBROS_DESC = {
    1: 'ADMINISTRACION', 2: 'LABORATORIO', 3: 'PLANTA DE MIEL',
    4: 'PLANTA DE ACOPIO', 5: 'GTOS DE EXPORTACION', 6: 'MERCADERIA',
    7: 'GASTOS AGROPECUARIOS', 8: 'AUTOMOVILES', 9: 'PLANTA ENVASADORA',
    10: 'NO USAR -FLETES MIEL', 11: 'NO USAR-FLETES CEREALES',
    12: 'NO USAR -FLETES COM EXT', 13: 'NO USAR -MERCADO INTERNO',
    14: 'GASTOS PERSONAL', 15: 'GTOS DE IMPORTACIONES', 16: 'GASTOS COMUNES',
    17: 'CAMIONES', 18: 'NO USAR -CAMION SCANNIA', 19: 'EXPORT. CUENTA Y ORDEN 3°',
}
