"""
Diálogo de conciliación: revisa y edita cada factura una por una antes de
escribir en Excel. Vista PDF al costado del formulario editable.
"""
import re

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QShortcut, QSplitter,
    QVBoxLayout, QWidget,
)

import estilo
from no_leidas import NOMBRE_CARPETA

try:
    import fitz as _fitz
    _PDF_OK = True
except ImportError:
    _PDF_OK = False

from pdf_parser import _num as _parsear_numero_flexible, armar_clave, _normalizar_cuit


# ---------------------------------------------------------------------------
# Definición de campos del formulario
# (key, label, crítico)
# ---------------------------------------------------------------------------
_CAMPOS = [
    ('tipo',                    'Tipo comprobante',   True),
    ('punto_venta',             'Tipo (fijo)',        False),
    ('numero',                  'Número',             True),
    ('punto_venta_factura',     'Punto de Venta',     True),
    ('fecha',                   'Fecha',              True),
    ('denominacion',            'Denominación',       True),
    ('cuit',                    'CUIT',               True),
    ('neto_num',                'Neto gravado',       True),
    ('iva_num',                 'IVA',                True),
    ('no_gravado_num',          'No gravado',         False),
    ('imp_internos_num',        'Imp. Internos',      False),
    ('exentos_num',             'Exentos',            False),
    ('percepcion_iva_num',      'Percepción IVA',     False),
    ('percepcion_iibb_num',     'Percepción IIBB',    False),
    ('percepcion_ganancias_num','Perc. Ganancias',    False),
    ('kilos_num',               'Kilos',              True),
    ('precio_unitario_num',     'Precio unitario',    True),
    ('total_num',               'Total',              True),
    ('monotributista',          'Monotributista',     False),
    ('posicion',                'Posición',           False),
    ('mes',                     'Mes',                False),
    ('anio',                    'Año',                False),
    ('tasa',                    'Tasa',               True),
    ('gasto',                   'Gasto',              True),
    ('rubro',                   'Rubro',              True),
    ('codigo_operacion',        'Cód. Operación',     False),
    ('descripcion_gasto',       'Descripción gasto',  False),
    ('descripcion_rubro',       'Descripción rubro',  False),
]

# 'monotributista' ya no es 'SI'/'' sino un importe (el total en facturas C),
# así que se muestra y relee como número igual que los campos *_num.
_NUM_KEYS = {k for k, *_ in _CAMPOS if k.endswith('_num')} | {'monotributista'}
_INT_KEYS = {'mes', 'anio', 'gasto', 'rubro'}

# Campos que siempre son VERIFICAR si están vacíos
_CRITICOS = {k for k, _, crit in _CAMPOS if crit}

# Tarjetas del formulario: (título, campos). Cada campo se muestra en la
# tarjeta de su grupo, en 2 columnas.
_GRUPOS = [
    ('Comprobante',  ['tipo', 'punto_venta', 'numero', 'punto_venta_factura', 'fecha']),
    ('Proveedor',    ['denominacion', 'cuit']),
    ('Importes',     ['neto_num', 'iva_num', 'tasa', 'no_gravado_num', 'imp_internos_num',
                      'exentos_num', 'percepcion_iva_num', 'percepcion_iibb_num',
                      'percepcion_ganancias_num', 'monotributista', 'total_num']),
    ('Cantidades',   ['kilos_num', 'precio_unitario_num']),
    ('Contabilidad', ['gasto', 'rubro', 'descripcion_gasto', 'descripcion_rubro',
                      'mes', 'anio', 'posicion', 'codigo_operacion']),
]
# Campos que ocupan las 2 columnas (textos largos)
_ANCHO_COMPLETO = {'denominacion', 'total_num'}
assert sorted(k for _, ks in _GRUPOS for k in ks) == sorted(k for k, *_ in _CAMPOS)


# ---------------------------------------------------------------------------
# Conversión valor ↔ texto
# ---------------------------------------------------------------------------

def _a_texto(key, val):
    """Convierte un valor del dict a texto para mostrar en el input."""
    if val is None:
        return ''
    if key == 'tasa':
        # Puede ser 0 (monotributista) o tener decimales (10,5%): no usar la
        # regla de _INT_KEYS (que trata 0 como vacío y trunca los decimales).
        return f'{float(val):g}'.replace('.', ',')
    if key in _NUM_KEYS:
        f = float(val)
        if f == 0.0:
            return '0'
        # Formato AR (punto de miles, coma decimal): es el que _num() espera
        # al releer el campo, aunque el usuario no lo haya editado (línea 507
        # llama get_valor() para todos los campos siempre).
        texto_us = f'{f:,.2f}'  # '1,234.56'
        return texto_us.replace(',', '@').replace('.', ',').replace('@', '.')
    if key in _INT_KEYS:
        return str(int(val)) if val else ''
    return str(val)


def _de_texto(key, text):
    """Convierte el texto del input al tipo correcto para el dict."""
    text = text.strip()
    if not text:
        return None
    if key == 'tasa' or key in _NUM_KEYS:
        # Acepta formato US (1234.56) y AR (1.234,56); rechaza texto no numérico
        # en lugar de adivinar (evita guardar un valor falso silenciosamente).
        if not re.match(r'^-?[\d.,]+$', text):
            return None
        return _parsear_numero_flexible(text)
    if key in _INT_KEYS:
        try:
            return int(text)
        except ValueError:
            return None
    return text


def _es_verificar(key, text):
    """¿Este campo debería mostrar cartel VERIFICAR?"""
    return key in _CRITICOS and not text.strip()


# ---------------------------------------------------------------------------
# Widget de un campo con cartel VERIFICAR
# ---------------------------------------------------------------------------

class _CampoInput(QWidget):
    """Etiqueta arriba + campo de texto + píldora VERIFICAR si falta."""

    def __init__(self, key, is_critical, label=''):
        super().__init__()
        self.key = key
        self.is_critical = is_critical

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(4)

        cab = QHBoxLayout()
        cab.setSpacing(6)
        texto = label
        if is_critical:
            texto += f'  <span style="color:{estilo.AMBAR}">●</span>'
        self.lbl = QLabel(texto)
        self.lbl.setProperty('clase', 'etiqueta')
        cab.addWidget(self.lbl)
        cab.addStretch()
        self.badge = QLabel('VERIFICAR')
        self.badge.setStyleSheet(
            f'background: {estilo.ROJO}; color: white; border-radius: 8px; '
            f'padding: 1px 8px; font-size: 8pt; font-weight: 700; letter-spacing: 1px;'
        )
        self.badge.setVisible(False)
        cab.addWidget(self.badge)
        col.addLayout(cab)

        self.edit = QLineEdit()
        self.edit.setMinimumWidth(120)
        col.addWidget(self.edit)

        self.edit.textChanged.connect(self._actualizar)

    def _set_estado(self, estado):
        if self.edit.property('estado') != estado:
            self.edit.setProperty('estado', estado)
            self.edit.style().unpolish(self.edit)
            self.edit.style().polish(self.edit)

    def _actualizar(self, text=''):
        if not text:
            text = self.edit.text()
        verificar = _es_verificar(self.key, text) and not self.edit.isReadOnly()
        self._set_estado('verificar' if verificar else '')
        self.badge.setVisible(verificar)

    def set_valor(self, val):
        text = _a_texto(self.key, val)
        self.edit.blockSignals(True)
        self.edit.setText(text)
        self.edit.blockSignals(False)
        self._actualizar(text)

    def get_valor(self):
        return _de_texto(self.key, self.edit.text())

    def set_readonly(self, readonly):
        self.edit.setReadOnly(readonly)
        self.edit.style().unpolish(self.edit)
        self.edit.style().polish(self.edit)
        self._actualizar()


# ---------------------------------------------------------------------------
# Diálogo principal de conciliación
# ---------------------------------------------------------------------------

class ReconciliacionDialog(QDialog):
    """
    Abre cada factura una por una:
      - izquierda: visor PDF
      - derecha:   formulario editable con carteles VERIFICAR
    Al confirmar todos, habilita el botón "Escribir en Excel".
    """

    def __init__(self, resultados, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Conciliación de Facturas')
        self.setMinimumSize(980, 600)
        self.showMaximized()   # arranca en pantalla completa
        self._zoom = 2.5       # zoom inicial del PDF

        self._todos   = resultados
        # Solo las facturas con datos parseados pasan por conciliación manual
        self._items   = [r for r in resultados if r['datos'] and not r['error']]
        self._idx     = 0
        self._decisiones = {}  # idx → {'omitida': bool, 'datos': dict}
        self._inputs  = {}     # key → _CampoInput

        self._construir_ui()
        if self._items:
            self._cargar(0)
        else:
            self._lbl_titulo.setText('No hay facturas para conciliar.')

        # PDFs que no se pudieron leer: no pasan por la revisión, así que se
        # avisa al abrir (si no, desaparecían sin que nadie lo note).
        fallidos = [r for r in resultados if r['error'] or not r['datos']]
        if fallidos:
            lista = '\n'.join(f'  • {r["filename"]}: {r["error"] or "sin datos"}'
                              for r in fallidos[:15])
            if len(fallidos) > 15:
                lista += f'\n  … y {len(fallidos) - 15} más'
            copiados = any(r.get('copia_no_leida') for r in fallidos)
            donde = (f'Quedó una copia en la carpeta "{NOMBRE_CARPETA}" '
                     '(botón "Ver no leídas" en la ventana principal).\n\n'
                     if copiados else '')
            QTimer.singleShot(300, lambda: QMessageBox.warning(
                self, 'PDFs que no se pudieron leer',
                f'{len(fallidos)} PDF(s) no se pudieron leer y NO se van a cargar '
                f'(quedan anotados en la hoja ERRORES):\n\n{lista}\n\n'
                f'{donde}Cargalos a mano si corresponde.'))

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _construir_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        # ── Barra superior: título, progreso de la revisión y contadores ─
        top = QHBoxLayout()
        top.setSpacing(12)
        titulos = QVBoxLayout()
        titulos.setSpacing(2)
        self._lbl_titulo = QLabel()
        self._lbl_titulo.setStyleSheet('font-size: 14pt; font-weight: 700;')
        self._lbl_archivo = QLabel()
        self._lbl_archivo.setProperty('clase', 'suave')
        titulos.addWidget(self._lbl_titulo)
        titulos.addWidget(self._lbl_archivo)
        top.addLayout(titulos, 1)
        self._chip_ok   = estilo.chip('', 'exito')
        self._chip_omit = estilo.chip('', 'error')
        self._chip_pend = estilo.chip('', 'neutro')
        for c in (self._chip_ok, self._chip_omit, self._chip_pend):
            top.addWidget(c, 0, Qt.AlignVCenter)
        root.addLayout(top)

        self._barra_revision = QProgressBar()
        self._barra_revision.setMaximumHeight(6)
        self._barra_revision.setStyleSheet('QProgressBar { min-height: 6px; max-height: 6px; border-radius: 3px; }'
                                           'QProgressBar::chunk { border-radius: 3px; }')
        root.addWidget(self._barra_revision)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Panel PDF ───────────────────────────────────────────────────
        pdf_panel = QFrame()
        pdf_panel.setProperty('clase', 'pdf')
        pdf_lo    = QVBoxLayout(pdf_panel)
        pdf_lo.setContentsMargins(12, 10, 12, 12)
        pdf_lo.setSpacing(8)

        pdf_top = QHBoxLayout()
        lbl_pdf = QLabel('Factura original')
        lbl_pdf.setProperty('clase', 'titulo_tarjeta')
        pdf_top.addWidget(lbl_pdf, 1)

        btn_zoom_out = QPushButton('−')
        estilo.variante(btn_zoom_out, 'redondo')
        btn_zoom_out.setToolTip('Reducir')
        btn_zoom_out.clicked.connect(self._zoom_out)
        pdf_top.addWidget(btn_zoom_out)

        self._lbl_zoom = QLabel('100%')
        self._lbl_zoom.setFixedWidth(58)
        self._lbl_zoom.setAlignment(Qt.AlignCenter)
        self._lbl_zoom.setStyleSheet(estilo.estilo_chip('neutro'))
        pdf_top.addWidget(self._lbl_zoom)

        btn_zoom_in = QPushButton('+')
        estilo.variante(btn_zoom_in, 'redondo')
        btn_zoom_in.setToolTip('Ampliar')
        btn_zoom_in.clicked.connect(self._zoom_in)
        pdf_top.addWidget(btn_zoom_in)

        pdf_lo.addLayout(pdf_top)

        self._pdf_scroll = QScrollArea()
        self._pdf_scroll.setWidgetResizable(False)
        self._pdf_scroll.setAlignment(Qt.AlignHCenter)
        self._pdf_lbl = QLabel('Cargando...')
        self._pdf_lbl.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self._pdf_lbl.setStyleSheet(
            f'background: white; border: 1px solid {estilo.BORDE_FUERTE}; color: {estilo.TEXTO_SUAVE};')
        self._pdf_scroll.setWidget(self._pdf_lbl)
        pdf_lo.addWidget(self._pdf_scroll, 1)
        splitter.addWidget(pdf_panel)

        # ── Panel formulario ────────────────────────────────────────────
        form_panel = QWidget()
        form_lo    = QVBoxLayout(form_panel)
        form_lo.setContentsMargins(0, 0, 0, 0)
        form_lo.setSpacing(10)

        self._lbl_aviso = QLabel()
        self._lbl_aviso.setWordWrap(True)
        self._lbl_aviso.setVisible(False)
        form_lo.addWidget(self._lbl_aviso)

        form_scroll  = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_widget  = QWidget()
        tarjetas_lo  = QVBoxLayout(form_widget)
        tarjetas_lo.setContentsMargins(0, 0, 6, 0)
        tarjetas_lo.setSpacing(10)

        etiquetas = {k: label for k, label, _ in _CAMPOS}
        criticos  = {k: crit for k, _, crit in _CAMPOS}
        for titulo_grupo, claves in _GRUPOS:
            frame, lo = estilo.tarjeta(titulo_grupo, margen=14, espacio=8)
            grilla = QGridLayout()
            grilla.setHorizontalSpacing(12)
            grilla.setVerticalSpacing(10)
            grilla.setColumnStretch(0, 1)
            grilla.setColumnStretch(1, 1)
            fila_g = col_g = 0
            for key in claves:
                inp = _CampoInput(key, criticos[key], etiquetas[key])
                self._inputs[key] = inp
                if key in _ANCHO_COMPLETO:
                    if col_g == 1:
                        fila_g, col_g = fila_g + 1, 0
                    grilla.addWidget(inp, fila_g, 0, 1, 2)
                    fila_g += 1
                else:
                    grilla.addWidget(inp, fila_g, col_g)
                    col_g += 1
                    if col_g == 2:
                        fila_g, col_g = fila_g + 1, 0
            lo.addLayout(grilla)
            tarjetas_lo.addWidget(frame)
        tarjetas_lo.addStretch()

        form_scroll.setWidget(form_widget)
        form_lo.addWidget(form_scroll, 1)

        leyenda = QLabel(f'<span style="color:{estilo.AMBAR}">●</span> dato obligatorio  ·  '
                         'Enter confirma  ·  Re Pág / Av Pág para moverse')
        leyenda.setProperty('clase', 'etiqueta')
        form_lo.addWidget(leyenda)

        splitter.addWidget(form_panel)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 5)
        root.addWidget(splitter, 1)

        # ── Barra inferior: navegación + guardado ───────────────────────
        barra = QFrame()
        barra.setProperty('clase', 'tarjeta')
        nav = QHBoxLayout(barra)
        nav.setContentsMargins(12, 10, 12, 10)
        nav.setSpacing(10)

        self._btn_ant = QPushButton('←  Anterior')
        estilo.variante(self._btn_ant, 'fantasma')
        self._btn_ant.setEnabled(False)
        self._btn_ant.clicked.connect(self._ir_anterior)
        nav.addWidget(self._btn_ant)

        self._btn_omitir = QPushButton('Omitir')
        estilo.variante(self._btn_omitir, 'peligro')
        self._btn_omitir.setToolTip('No cargar esta factura en Excel')
        self._btn_omitir.clicked.connect(self._omitir)
        nav.addWidget(self._btn_omitir)

        self._lbl_conteo = QLabel()
        self._lbl_conteo.setProperty('clase', 'suave')
        self._lbl_conteo.setAlignment(Qt.AlignCenter)
        nav.addWidget(self._lbl_conteo, 1)

        self._lbl_resumen = QLabel()   # se conserva (texto de resumen), oculto
        self._lbl_resumen.setVisible(False)

        self._btn_confirmar = QPushButton('Confirmar y continuar  →')
        estilo.variante(self._btn_confirmar, 'primario')
        self._btn_confirmar.setDefault(True)
        self._btn_confirmar.setMinimumHeight(40)
        self._btn_confirmar.setCursor(Qt.PointingHandCursor)
        self._btn_confirmar.clicked.connect(self._confirmar)
        nav.addWidget(self._btn_confirmar)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f'background: {estilo.BORDE};')
        nav.addWidget(sep)

        self._btn_escribir = QPushButton('✓  Guardar en Excel')
        estilo.variante(self._btn_escribir, 'exito')
        self._btn_escribir.setMinimumHeight(40)
        self._btn_escribir.setEnabled(False)
        self._btn_escribir.setCursor(Qt.PointingHandCursor)
        self._btn_escribir.clicked.connect(self.accept)
        nav.addWidget(self._btn_escribir)

        btn_cancelar = QPushButton('Cancelar todo')
        estilo.variante(btn_cancelar, 'fantasma')
        btn_cancelar.clicked.connect(self._cancelar_todo)
        nav.addWidget(btn_cancelar)

        root.addWidget(barra)

        QShortcut(QKeySequence(Qt.Key_PageDown), self,
                  activated=lambda: self._btn_confirmar.isEnabled() and self._confirmar())
        QShortcut(QKeySequence(Qt.Key_PageUp), self,
                  activated=lambda: self._btn_ant.isEnabled() and self._ir_anterior())

    def _mostrar_aviso(self, texto, tipo):
        self._lbl_aviso.setText(texto)
        self._lbl_aviso.setStyleSheet(estilo.estilo_banner(tipo))
        self._lbl_aviso.setVisible(True)

    def _confirmar_cancelar(self):
        resp = QMessageBox.question(
            self, 'Cancelar todo',
            'Si cancelás, se pierde toda la revisión y no se guarda ninguna '
            'factura.\n\n¿Seguro?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        return resp == QMessageBox.Yes

    def reject(self):
        # La tecla Esc llama a reject() directo (sin pasar por closeEvent):
        # también tiene que pedir confirmación, si no se perdía toda la
        # revisión con un solo toque.
        if self._confirmar_cancelar():
            super().reject()

    def _cancelar_todo(self):
        self.reject()

    def closeEvent(self, event):
        # La X de la ventana también pide confirmación (evita perder trabajo).
        # Al guardar (accept) la ventana se cierra sin preguntar.
        if self.result() == QDialog.Accepted or self._confirmar_cancelar():
            event.accept()
        else:
            event.ignore()

    # ------------------------------------------------------------------
    # Carga de una factura en el formulario
    # ------------------------------------------------------------------

    def _cargar(self, idx):
        if idx < 0 or idx >= len(self._items):
            return
        self._idx = idx
        r = self._items[idx]
        total = len(self._items)

        self._lbl_titulo.setText(f'Factura {idx + 1} de {total}')
        self._lbl_titulo.setStyleSheet('font-size: 14pt; font-weight: 700;')
        self._lbl_archivo.setText(r['filename'])

        # Usar decisión guardada si existe (al retroceder)
        if idx in self._decisiones:
            datos = self._decisiones[idx]['datos'] or r['datos']
        else:
            datos = r['datos']

        for key, *_ in _CAMPOS:
            self._inputs[key].set_valor(datos.get(key))

        # Avisos de duplicado / error / moneda extranjera
        es_dup = r['dup_clave']
        if es_dup:
            self._mostrar_aviso(
                '⚠  Esta factura ya existe en el Excel (duplicada). '
                'Solo podés omitirla.', 'aviso')
        elif r['error']:
            self._mostrar_aviso(f'✗  Error al parsear: {r["error"]}', 'error')
        else:
            avisos = []
            if datos.get('moneda_extranjera'):
                tc = datos.get('tipo_cambio')
                avisos.append(
                    '💲  Factura en MONEDA EXTRANJERA: los importes NO están en pesos'
                    + (f' (tipo de cambio en la factura: {tc:g})' if tc else '') + '.')
            if r.get('dup_nombre'):
                avisos.append(
                    'ℹ  Ya se cargó antes un PDF con este mismo nombre de archivo. '
                    'Si los datos son de otra factura, confirmala normal.')
            if avisos:
                self._mostrar_aviso('\n'.join(avisos), 'aviso')
            else:
                self._lbl_aviso.setVisible(False)

        readonly = es_dup or bool(r['error'])
        for inp in self._inputs.values():
            inp.set_readonly(readonly)

        self._btn_confirmar.setEnabled(not readonly)
        self._btn_omitir.setEnabled(True)   # se deshabilita en _mostrar_fin
        self._btn_ant.setEnabled(idx > 0)

        # Renderizar PDF con breve delay para que la UI no se congele
        QTimer.singleShot(60, lambda r=r: self._renderizar(r))
        self._refrescar_contadores()

    # ------------------------------------------------------------------
    # Renderizado PDF
    # ------------------------------------------------------------------

    def _zoom_in(self):
        self._zoom = min(self._zoom + 0.5, 7.5)  # máximo 300%
        if self._items:
            self._renderizar(self._items[self._idx])

    def _zoom_out(self):
        self._zoom = max(self._zoom - 0.5, 1.25)  # mínimo 50%
        if self._items:
            self._renderizar(self._items[self._idx])

    def _renderizar(self, r):
        if not _PDF_OK:
            self._pdf_lbl.setText(
                '⚠  Vista previa no disponible.\n\n'
                'Para activarla:\n'
                '   pip install pymupdf'
            )
            self._pdf_lbl.setAlignment(Qt.AlignCenter)
            return
        try:
            pdf_bytes = r['ruta'].read_bytes()
            doc  = _fitz.open(stream=pdf_bytes, filetype='pdf')
            page = doc[0]
            mat  = _fitz.Matrix(3.0, 3.0)  # alta resolución base
            pix  = page.get_pixmap(matrix=mat, alpha=False)
            png  = pix.tobytes('png')
            doc.close()

            pixmap = QPixmap()
            pixmap.loadFromData(png)

            # zoom=2.5 → 100% (ajusta al ancho disponible)
            # zoom>2.5 → más grande, aparece scroll horizontal
            ancho_disponible = self._pdf_scroll.viewport().width() - 32   # margen gris
            if ancho_disponible > 50:
                ancho_objetivo = int(ancho_disponible * self._zoom / 2.5)
                pixmap = pixmap.scaledToWidth(ancho_objetivo, Qt.SmoothTransformation)

            self._pdf_lbl.setPixmap(pixmap)
            self._pdf_lbl.resize(pixmap.width(), pixmap.height() + 24)   # + márgenes
            self._lbl_zoom.setText(f'{int(self._zoom / 2.5 * 100)}%')
        except Exception as e:
            self._pdf_lbl.setText(f'Error al renderizar:\n{e}')
            self._pdf_lbl.setAlignment(Qt.AlignCenter)

    # ------------------------------------------------------------------
    # Acciones de navegación
    # ------------------------------------------------------------------

    def _leer_form(self):
        r = self._items[self._idx]
        datos = dict(r['datos'])
        original = r['datos'].get('denominacion')
        for key, *_ in _CAMPOS:
            datos[key] = self._inputs[key].get_valor()
        # Si el nombre no vino del cruce CUIT->nombre (celda roja) pero el
        # usuario lo corrigió acá, ya está revisado: no marcarlo en rojo.
        if not datos.get('denominacion_cruzada') and datos.get('denominacion') != original:
            datos['denominacion_cruzada'] = True

        if datos.get('tipo'):
            datos['tipo'] = str(datos['tipo']).strip().upper()
        if datos.get('cuit'):
            # Mismo formato que el parser (20-12345678-9) aunque se tipee sin
            # guiones: si no, la clave no coincide con la de la ya cargada.
            datos['cuit'] = _normalizar_cuit(datos['cuit'])

        # Si cambió la fecha y el mes/año siguen como los leyó el programa,
        # se recalculan con la fecha nueva (si el usuario tocó mes/año a
        # propósito, se respeta lo que puso).
        orig = r['datos']
        if datos.get('fecha') != orig.get('fecha'):
            m = re.match(r'^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$', datos.get('fecha') or '')
            if m:
                if datos.get('mes') == orig.get('mes'):
                    datos['mes'] = int(m.group(2))
                if datos.get('anio') == orig.get('anio'):
                    datos['anio'] = int(m.group(3))

        # La clave de duplicados se arma con tipo|CUIT|PV|número: si el
        # usuario corrigió alguno, se recalcula (si no, quedaba la vieja,
        # ej. "...|SIN_NUMERO", y la factura se podía cargar dos veces).
        if datos.get('tipo') != 'RCC':
            datos['clave'] = armar_clave(
                datos.get('tipo'), datos.get('cuit'),
                datos.get('punto_venta_factura') or datos.get('punto_venta'),
                datos.get('numero'))
        return datos

    def _confirmar(self):
        datos = self._leer_form()
        self._decisiones[self._idx] = {'omitida': False, 'datos': datos}
        self._avanzar()

    def _omitir(self):
        self._decisiones[self._idx] = {'omitida': True, 'datos': None}
        self._avanzar()

    def _avanzar(self):
        if self._idx + 1 < len(self._items):
            self._cargar(self._idx + 1)
        else:
            self._mostrar_fin()

    def _ir_anterior(self):
        self._cargar(self._idx - 1)

    def _mostrar_fin(self):
        confirmadas = sum(
            1 for v in self._decisiones.values() if not v['omitida']
        )
        omitidas = len(self._decisiones) - confirmadas
        self._lbl_titulo.setText('Terminaste de revisar')
        self._lbl_titulo.setStyleSheet(f'font-size: 14pt; font-weight: 700; color: {estilo.VERDE};')
        self._lbl_archivo.setText(
            f'Ahora apretá el botón VERDE de abajo para guardar ({confirmadas} factura/s).')
        self._btn_confirmar.setEnabled(False)
        self._btn_omitir.setEnabled(False)
        self._btn_escribir.setEnabled(confirmadas > 0)
        # Resaltar el botón para que sea imposible no verlo
        if confirmadas > 0:
            self._btn_escribir.setText('✓  GUARDAR EN EXCEL')
            self._btn_escribir.setFocus()
        self._refrescar_contadores()

    def _refrescar_contadores(self):
        total       = len(self._items)
        revisadas   = len(self._decisiones)
        confirmadas = sum(1 for v in self._decisiones.values() if not v['omitida'])
        omitidas    = revisadas - confirmadas
        pendientes  = total - revisadas

        self._lbl_conteo.setText(f'{self._idx + 1} de {total}')
        self._chip_ok.setText(f'✓ Confirmadas {confirmadas}')
        self._chip_omit.setText(f'✗ Omitidas {omitidas}')
        self._chip_omit.setVisible(omitidas > 0)
        self._chip_pend.setText(f'Pendientes {pendientes}')
        self._barra_revision.setMaximum(max(total, 1))
        self._barra_revision.setValue(revisadas)
        all_done = revisadas >= total
        self._btn_escribir.setEnabled(
            all_done and confirmadas > 0
        )

    # ------------------------------------------------------------------
    # Resultado final
    # ------------------------------------------------------------------

    def resultados_para_escribir(self):
        """
        Devuelve la lista de resultados a escribir en Excel.
        - Facturas confirmadas: con los datos editados del formulario.
        - Facturas con error:   incluidas tal cual para registrar_error().
        - Facturas omitidas:    excluidas.
        """
        out = []
        proc_idx = 0
        for r in self._todos:
            if r['datos'] and not r['error']:
                dec = self._decisiones.get(proc_idx)
                if dec and not dec['omitida']:
                    out.append({**r, 'datos': dec['datos']})
                # omitidas: no se incluyen
                proc_idx += 1
            else:
                out.append(r)  # errores → van a hoja ERRORES
        return out
