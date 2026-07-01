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
    'ESTADO':               30,   # AD - Estado
    'HORA_ESTADO':          31,   # AE - Estado (hora)
    'ERROR_GENERAL':        32,   # AF - Error general
    # Columnas ocultas — no tienen encabezado, solo para control de duplicados
    'NOMBRE_ADJUNTO':       33,   # AG
    'CLAVE_COMPROBANTE':    34,   # AH
}

NUM_COLS = 34

# Encabezados visibles de la hoja FACTURAS (cols 1-32, None = columna vacía)
HEADERS_FACTURAS = [
    'Tipo', 'Número Desde', 'Punto de Venta', 'Fecha',
    'Denominación', 'CUIT', 'Neto gravado', 'Iva', 'No gravado',
    'Imp. Internos', 'Exentos', 'Percepción IVA', 'Percepción IIBB',
    'Kilos', 'Precio unitario', 'Monotributista', 'Percepción Ganancias',
    'Total', 'Tasa', 'Gasto', 'Rubro', 'Mes de imputación', 'Año imputación',
    'Código de operación', 'Posición', None, 'Descripción gasto',
    'Descripción rubro', None, 'Estado', 'Estado', 'Error general. Revisar hoja ERRORES.',
]
