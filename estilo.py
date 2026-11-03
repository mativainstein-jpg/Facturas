"""
Tema visual de la app (claro con azul). Todos los colores y estilos están
acá: las pantallas solo marcan cada widget con una "variante" o propiedad.
"""
from PyQt5.QtGui import QColor, QFont, QPalette

FONDO          = '#F4F6FA'
TARJETA        = '#FFFFFF'
BORDE          = '#E3E7EE'
BORDE_CAMPO    = '#D0D5DD'
TEXTO          = '#1F2937'
TEXTO_2        = '#6B7280'
PRIMARIO       = '#2563EB'
PRIMARIO_HOVER = '#1D4ED8'
PRIMARIO_SUAVE = '#EFF4FF'
EXITO          = '#16A34A'
EXITO_HOVER    = '#15803D'
EXITO_SUAVE    = '#DCFCE7'
ROJO           = '#DC2626'
ROJO_SUAVE     = '#FEF2F2'
AMBAR_FONDO    = '#FEF3C7'
AMBAR_TEXTO    = '#92400E'
GRIS_SUAVE     = '#F3F4F6'
FONDO_VISOR    = '#E9ECF1'

FUENTES       = ['Segoe UI', 'Inter', 'Arial']
FUENTES_MONO  = ['Consolas', 'Cascadia Mono', 'DejaVu Sans Mono', 'Courier New']

QSS = f"""
QWidget {{ color: {TEXTO}; }}
QMainWindow, QDialog, QWidget#fondo {{ background: {FONDO}; }}

QFrame[tarjeta="true"] {{
    background: {TARJETA};
    border: 1px solid {BORDE};
    border-radius: 12px;
}}
QFrame[tarjeta="true"] QLabel {{ background: transparent; }}

QLabel#titulo {{ font-size: 20pt; font-weight: 600; }}
QLabel#subtitulo, QLabel[secundario="true"] {{ color: {TEXTO_2}; }}
QLabel#seccion {{
    color: {TEXTO_2}; font-size: 8pt; font-weight: 700;
}}
QLabel#paso_num {{
    background: {PRIMARIO_SUAVE}; color: {PRIMARIO};
    border-radius: 14px; font-weight: 700;
}}
QLabel#titulo_revision {{ font-size: 13pt; font-weight: 600; }}
QLabel#titulo_revision[estado="fin"] {{ color: {EXITO}; }}
QLabel#contador {{ color: {TEXTO_2}; font-weight: 600; }}

QLabel[campo="true"] {{ color: {TEXTO_2}; }}
QLabel[campo="true"][critico="true"] {{ color: {TEXTO}; font-weight: 600; }}

QLabel[chip="ok"], QLabel[chip="omit"], QLabel[chip="pend"] {{
    border-radius: 11px; padding: 3px 10px; font-weight: 600;
}}
QLabel[chip="ok"]   {{ background: {EXITO_SUAVE}; color: #166534; }}
QLabel[chip="omit"] {{ background: {GRIS_SUAVE}; color: #374151; }}
QLabel[chip="pend"] {{ background: {PRIMARIO_SUAVE}; color: {PRIMARIO}; }}

QLabel[banner="aviso"], QLabel[banner="error"] {{ border-radius: 8px; padding: 10px 12px; }}
QLabel[banner="aviso"] {{ background: {AMBAR_FONDO}; color: {AMBAR_TEXTO}; }}
QLabel[banner="error"] {{ background: {ROJO_SUAVE}; color: #991B1B; border: 1px solid #FECACA; }}

QLabel#badge_verificar {{
    background: {ROJO}; color: white; border-radius: 10px;
    padding: 3px 10px; font-weight: 700;
}}

QPushButton {{
    background: {TARJETA}; color: {TEXTO};
    border: 1px solid {BORDE_CAMPO}; border-radius: 8px;
    padding: 7px 16px;
}}
QPushButton:hover    {{ background: #F9FAFB; border-color: #B8C0CC; }}
QPushButton:pressed  {{ background: {GRIS_SUAVE}; }}
QPushButton:disabled {{ color: #9CA3AF; background: {GRIS_SUAVE}; border-color: #E5E7EB; }}
QPushButton:focus    {{ outline: none; }}

QPushButton[variante="primario"] {{
    background: {PRIMARIO}; color: white; border: none; font-weight: 600;
}}
QPushButton[variante="primario"]:hover    {{ background: {PRIMARIO_HOVER}; }}
QPushButton[variante="primario"]:disabled {{ background: #BFD0F5; color: white; }}

QPushButton[variante="exito"] {{
    background: {EXITO}; color: white; border: none; font-weight: 700;
}}
QPushButton[variante="exito"]:hover    {{ background: {EXITO_HOVER}; }}
QPushButton[variante="exito"]:disabled {{ background: #D1D5DB; color: #F9FAFB; }}

QPushButton[variante="enlace"] {{
    background: transparent; border: none; color: {PRIMARIO}; padding: 7px 8px;
}}
QPushButton[variante="enlace"]:hover {{ color: {PRIMARIO_HOVER}; background: {PRIMARIO_SUAVE}; }}
QPushButton[variante="enlace"]:disabled {{ color: #9CA3AF; background: transparent; }}

QPushButton[variante="peligro"] {{
    background: transparent; border: none; color: {ROJO}; padding: 7px 10px;
}}
QPushButton[variante="peligro"]:hover    {{ background: {ROJO_SUAVE}; }}
QPushButton[variante="peligro"]:disabled {{ color: #FCA5A5; background: transparent; }}

QPushButton[variante="icono"] {{
    min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px;
    padding: 0; border-radius: 15px; font-size: 13pt;
}}

QLineEdit {{
    background: {TARJETA}; border: 1px solid {BORDE_CAMPO};
    border-radius: 6px; padding: 5px 8px;
    selection-background-color: {PRIMARIO};
}}
QLineEdit:focus {{ border: 1px solid {PRIMARIO}; }}
QLineEdit[verificar="true"] {{ border: 2px solid {ROJO}; background: {ROJO_SUAVE}; }}
QLineEdit:read-only {{ background: {GRIS_SUAVE}; color: {TEXTO_2}; }}

QTextEdit#log {{
    background: #F9FAFB; border: 1px solid {BORDE}; border-radius: 8px;
    padding: 6px; color: #374151;
}}

QProgressBar {{
    border: none; background: #E5E7EB; border-radius: 3px;
    max-height: 6px; min-height: 6px;
}}
QProgressBar::chunk {{ background: {PRIMARIO}; border-radius: 3px; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollArea#visor_pdf {{ background: {FONDO_VISOR}; border-radius: 8px; }}
QScrollArea#visor_pdf > QWidget > QWidget {{ background: {FONDO_VISOR}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: #CBD2DC; border-radius: 3px; }}
QScrollBar::handle:hover {{ background: #9CA3AF; }}
QScrollBar::handle:vertical {{ min-height: 30px; }}
QScrollBar::handle:horizontal {{ min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background: transparent; width: 10px; }}

QToolTip {{
    background: {TEXTO}; color: white; border: none;
    border-radius: 6px; padding: 6px 8px;
}}

QMessageBox {{ background: {TARJETA}; }}
QMessageBox QPushButton {{ min-width: 90px; }}
"""


def fuente(tamano=10, negrita=False, mono=False):
    f = QFont()
    familias = FUENTES_MONO if mono else FUENTES
    if hasattr(f, 'setFamilies'):
        f.setFamilies(familias)
    else:
        f.setFamily(familias[0])
    f.setPointSize(tamano)
    f.setBold(negrita)
    return f


def aplicar(app):
    app.setStyle('Fusion')
    app.setFont(fuente(10))
    paleta = QPalette()
    paleta.setColor(QPalette.Window, QColor(FONDO))
    paleta.setColor(QPalette.Base, QColor(TARJETA))
    paleta.setColor(QPalette.AlternateBase, QColor(GRIS_SUAVE))
    paleta.setColor(QPalette.Text, QColor(TEXTO))
    paleta.setColor(QPalette.WindowText, QColor(TEXTO))
    paleta.setColor(QPalette.ButtonText, QColor(TEXTO))
    paleta.setColor(QPalette.Button, QColor(TARJETA))
    paleta.setColor(QPalette.Highlight, QColor(PRIMARIO))
    paleta.setColor(QPalette.HighlightedText, QColor('white'))
    paleta.setColor(QPalette.ToolTipBase, QColor(TEXTO))
    paleta.setColor(QPalette.ToolTipText, QColor('white'))
    app.setPalette(paleta)
    app.setStyleSheet(QSS)


def marcar(widget, **props):
    """Pone propiedades de estilo (ej. variante='primario') y repinta."""
    for k, v in props.items():
        widget.setProperty(k, v)
    # unpolish/polish actualiza los colores pero no los márgenes (el relleno
    # del QSS): cambiar la hoja propia del widget fuerza a recalcular todo.
    widget.setStyleSheet('/**/' if widget.styleSheet() == '/* */' else '/* */')
    return widget


def tarjeta(frame):
    """Marca un QFrame como tarjeta blanca con borde redondeado."""
    frame.setProperty('tarjeta', True)
    return frame
