"""
Estilo visual de la app (colores, botones, tarjetas). Todo lo "de diseño"
está acá, para no repetir colores sueltos en cada pantalla.

Uso:
    from estilo import aplicar_estilo
    aplicar_estilo(app)          # una vez, en main.py

Botones: se elige la variante con  boton.setProperty('variante', 'primario')
  primario  → ámbar, texto blanco (la acción principal de la pantalla)
  exito     → verde (guardar)
  fantasma  → transparente con borde (acciones secundarias)
  peligro   → texto rojo (omitir, cancelar)
  enlace    → solo texto ámbar, sin borde (acciones poco usadas)
"""
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import (
    QColor, QFont, QFontDatabase, QIcon, QLinearGradient, QPainter,
    QPainterPath, QPalette, QPixmap,
)
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QStyleFactory, QVBoxLayout

# ---------------------------------------------------------------------------
# Colores
# ---------------------------------------------------------------------------
FONDO         = '#FBF8F3'   # crema muy claro
TARJETA       = '#FFFFFF'
BORDE         = '#ECE4D6'
BORDE_FUERTE  = '#DCCFB8'
TEXTO         = '#2B2620'
TEXTO_SUAVE   = '#7A7064'
AMBAR         = '#D98E04'
AMBAR_HOVER   = '#B87503'
AMBAR_CLARO   = '#FDF0D5'
VERDE         = '#2E7D32'
VERDE_HOVER   = '#256628'
VERDE_CLARO   = '#E6F2E6'
ROJO          = '#C62828'
ROJO_CLARO    = '#FDECEC'
AVISO_FONDO   = '#FFF4D6'
AVISO_TEXTO   = '#8A5A00'
GRIS_PDF      = '#E9E4DC'

# Por tipo de chip / banner: (fondo, texto, franja)
_TIPOS = {
    'neutro':  ('#F3EEE6', TEXTO_SUAVE, BORDE_FUERTE),
    'ambar':   (AMBAR_CLARO, AVISO_TEXTO, AMBAR),
    'aviso':   (AVISO_FONDO, AVISO_TEXTO, AMBAR),
    'exito':   (VERDE_CLARO, VERDE, VERDE),
    'error':   (ROJO_CLARO, ROJO, ROJO),
    'info':    ('#EEF3F8', '#2F4A66', '#6C8EB0'),
}


def _familia_fuente():
    disponibles = set(QFontDatabase().families())
    for nombre in ('Segoe UI', 'Inter', 'Noto Sans', 'DejaVu Sans', 'Arial'):
        if nombre in disponibles:
            return nombre
    return QFont().defaultFamily()


_QSS = """
QWidget {{
    color: {TEXTO};
    font-size: 10pt;
}}
QMainWindow, QDialog {{
    background: {FONDO};
}}
QToolTip {{
    background: {TEXTO};
    color: white;
    border: none;
    padding: 6px 8px;
    border-radius: 6px;
}}

/* ---------- Botones ---------- */
QPushButton {{
    background: {TARJETA};
    border: 1px solid {BORDE_FUERTE};
    border-radius: 8px;
    padding: 8px 16px;
    min-height: 20px;
}}
QPushButton:hover {{
    background: #F7F1E7;
    border-color: {AMBAR};
}}
QPushButton:pressed {{
    background: {AMBAR_CLARO};
}}
QPushButton:disabled {{
    color: #B5ADA2;
    background: #F4F0EA;
    border-color: {BORDE};
}}
QPushButton:focus {{
    outline: none;
}}

QPushButton[variante="primario"] {{
    background: {AMBAR};
    color: white;
    border: 1px solid {AMBAR};
    font-weight: 600;
}}
QPushButton[variante="primario"]:hover {{
    background: {AMBAR_HOVER};
    border-color: {AMBAR_HOVER};
}}
QPushButton[variante="primario"]:disabled {{
    background: #EAD9B8;
    border-color: #EAD9B8;
    color: #FFFFFF;
}}

QPushButton[variante="exito"] {{
    background: {VERDE};
    color: white;
    border: 1px solid {VERDE};
    font-weight: 600;
}}
QPushButton[variante="exito"]:hover {{
    background: {VERDE_HOVER};
    border-color: {VERDE_HOVER};
}}
QPushButton[variante="exito"]:disabled {{
    background: #E3E0DA;
    border-color: #E3E0DA;
    color: #A39C92;
}}

QPushButton[variante="fantasma"] {{
    background: transparent;
    border: 1px solid {BORDE_FUERTE};
    color: {TEXTO};
}}
QPushButton[variante="fantasma"]:hover {{
    background: {TARJETA};
    border-color: {AMBAR};
}}
QPushButton[variante="fantasma"]:disabled {{
    background: transparent;
    color: #C4BCB0;
    border-color: {BORDE};
}}

QPushButton[variante="peligro"] {{
    background: transparent;
    border: 1px solid #E8C4C4;
    color: {ROJO};
}}
QPushButton[variante="peligro"]:hover {{
    background: {ROJO_CLARO};
    border-color: {ROJO};
}}
QPushButton[variante="peligro"]:disabled {{
    background: transparent;
    color: #D9B8B8;
    border-color: #F0DEDE;
}}

QPushButton[variante="enlace"] {{
    background: transparent;
    border: none;
    color: {AMBAR_HOVER};
    padding: 8px 10px;
}}
QPushButton[variante="enlace"]:hover {{
    background: {AMBAR_CLARO};
}}
QPushButton[variante="enlace"]:disabled {{
    color: #C4BCB0;
    background: transparent;
}}

QPushButton[variante="redondo"] {{
    background: {TARJETA};
    border: 1px solid {BORDE_FUERTE};
    border-radius: 14px;
    padding: 0px;
    min-width: 28px;  max-width: 28px;
    min-height: 28px; max-height: 28px;
    font-weight: 600;
}}
QPushButton[variante="redondo"]:hover {{
    border-color: {AMBAR};
    color: {AMBAR_HOVER};
}}

/* ---------- Campos ---------- */
QLineEdit {{
    background: {TARJETA};
    border: 1px solid {BORDE_FUERTE};
    border-radius: 7px;
    padding: 6px 9px;
    selection-background-color: {AMBAR};
}}
QLineEdit:focus {{
    border: 2px solid {AMBAR};
    padding: 5px 8px;
}}
QLineEdit[estado="verificar"] {{
    background: {ROJO_CLARO};
    border: 2px solid {ROJO};
    padding: 5px 8px;
}}
QLineEdit[readOnly="true"] {{
    background: #F4F0EA;
    color: #9A9186;
    border-color: {BORDE};
}}

QTextEdit {{
    background: transparent;
    border: none;
    selection-background-color: {AMBAR};
}}

/* ---------- Barra de progreso ---------- */
QProgressBar {{
    background: #EFE8DC;
    border: none;
    border-radius: 5px;
    min-height: 10px;
    max-height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {AMBAR};
    border-radius: 5px;
}}

/* ---------- Scroll ---------- */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #D8CCB8;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {AMBAR};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #D8CCB8;
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {AMBAR};
}}
QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {{
    width: 0px; height: 0px; background: none;
}}

QSplitter::handle {{
    background: transparent;
    width: 10px;
}}

/* ---------- Tarjetas y textos ---------- */
QFrame[clase="tarjeta"] {{
    background: {TARJETA};
    border: 1px solid {BORDE};
    border-radius: 12px;
}}
QFrame[clase="encabezado"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #E9A21B, stop:1 {AMBAR_HOVER});
    border: none;
    border-radius: 12px;
}}
QFrame[clase="pdf"] {{
    background: {GRIS_PDF};
    border: 1px solid {BORDE};
    border-radius: 12px;
}}
QLabel[clase="titulo_tarjeta"] {{
    font-size: 11pt;
    font-weight: 600;
    color: {TEXTO};
    background: transparent;
}}
QLabel[clase="suave"] {{
    color: {TEXTO_SUAVE};
    background: transparent;
}}
QLabel[clase="etiqueta"] {{
    color: {TEXTO_SUAVE};
    font-size: 9pt;
    background: transparent;
}}

QMessageBox {{
    background: {FONDO};
}}
QMessageBox QPushButton {{
    min-width: 90px;
}}
"""


def aplicar_estilo(app):
    """Estilo general de la app. Llamar una sola vez, antes de crear ventanas."""
    app.setStyle(QStyleFactory.create('Fusion'))

    fuente = QFont(_familia_fuente(), 10)
    app.setFont(fuente)

    paleta = QPalette()
    paleta.setColor(QPalette.Window, QColor(FONDO))
    paleta.setColor(QPalette.Base, QColor(TARJETA))
    paleta.setColor(QPalette.AlternateBase, QColor('#F7F2EA'))
    paleta.setColor(QPalette.Text, QColor(TEXTO))
    paleta.setColor(QPalette.WindowText, QColor(TEXTO))
    paleta.setColor(QPalette.ButtonText, QColor(TEXTO))
    paleta.setColor(QPalette.Button, QColor(TARJETA))
    paleta.setColor(QPalette.Highlight, QColor(AMBAR))
    paleta.setColor(QPalette.HighlightedText, QColor('white'))
    paleta.setColor(QPalette.ToolTipBase, QColor(TEXTO))
    paleta.setColor(QPalette.ToolTipText, QColor('white'))
    app.setPalette(paleta)

    app.setStyleSheet(_QSS.format(**globals()))
    app.setWindowIcon(icono_app())


# Mismo nombre que usaba la versión anterior del estilo.
aplicar = aplicar_estilo


# ---------------------------------------------------------------------------
# Ícono (gota de miel dibujada, sin archivos de imagen)
# ---------------------------------------------------------------------------

def icono_app():
    icono = QIcon()
    for lado in (16, 24, 32, 48, 64, 128, 256):
        icono.addPixmap(_dibujar_gota(lado))
    return icono


def _dibujar_gota(lado):
    pix = QPixmap(lado, lado)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    s = lado / 64.0
    camino = QPainterPath()
    camino.moveTo(32 * s, 4 * s)
    camino.cubicTo(32 * s, 4 * s, 10 * s, 30 * s, 10 * s, 41 * s)
    camino.cubicTo(10 * s, 53 * s, 20 * s, 61 * s, 32 * s, 61 * s)
    camino.cubicTo(44 * s, 61 * s, 54 * s, 53 * s, 54 * s, 41 * s)
    camino.cubicTo(54 * s, 30 * s, 32 * s, 4 * s, 32 * s, 4 * s)
    grad = QLinearGradient(QPointF(0, 0), QPointF(0, lado))
    grad.setColorAt(0, QColor('#F2B533'))
    grad.setColorAt(1, QColor(AMBAR_HOVER))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawPath(camino)
    p.setBrush(QColor(255, 255, 255, 150))
    p.drawEllipse(QPointF(24 * s, 42 * s), 4.5 * s, 7 * s)
    p.end()
    return pix


# ---------------------------------------------------------------------------
# Piezas reutilizables
# ---------------------------------------------------------------------------

def variante(boton, nombre):
    """Aplica una variante de botón (ver arriba) y refresca el estilo."""
    boton.setProperty('variante', nombre)
    boton.style().unpolish(boton)
    boton.style().polish(boton)
    return boton


def tarjeta(titulo=None, margen=16, espacio=10):
    """QFrame blanco con bordes redondeados. Devuelve (frame, layout)."""
    frame = QFrame()
    frame.setProperty('clase', 'tarjeta')
    lo = QVBoxLayout(frame)
    lo.setContentsMargins(margen, margen - 2, margen, margen)
    lo.setSpacing(espacio)
    if titulo:
        lbl = QLabel(titulo)
        lbl.setProperty('clase', 'titulo_tarjeta')
        lo.addWidget(lbl)
    return frame, lo


def estilo_chip(tipo='neutro', negrita=True):
    fondo, texto, _ = _TIPOS.get(tipo, _TIPOS['neutro'])
    return (f'background: {fondo}; color: {texto}; border-radius: 11px; '
            f'padding: 3px 11px; font-size: 9pt; '
            f'font-weight: {600 if negrita else 400};')


def chip(texto, tipo='neutro'):
    """Etiqueta en forma de píldora."""
    lbl = QLabel(texto)
    lbl.setStyleSheet(estilo_chip(tipo))
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


def estilo_banner(tipo='aviso'):
    fondo, texto, franja = _TIPOS.get(tipo, _TIPOS['aviso'])
    return (f'background: {fondo}; color: {texto}; '
            f'border-left: 4px solid {franja}; border-radius: 8px; '
            f'padding: 10px 12px;')


def banner(tipo='aviso'):
    """Aviso con franja de color a la izquierda (QLabel con word wrap)."""
    lbl = QLabel()
    lbl.setWordWrap(True)
    lbl.setStyleSheet(estilo_banner(tipo))
    return lbl


def numero_paso(n):
    """Círculo ámbar con el número de paso."""
    lbl = QLabel(str(n))
    lbl.setFixedSize(28, 28)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        f'background: {AMBAR}; color: white; border-radius: 14px; '
        f'font-weight: 700; font-size: 10pt;'
    )
    return lbl


def fila(*widgets, espacio=8, stretch_final=False):
    lo = QHBoxLayout()
    lo.setSpacing(espacio)
    for w in widgets:
        if w is None:
            lo.addStretch()
        else:
            lo.addWidget(w)
    if stretch_final:
        lo.addStretch()
    return lo
