import html
import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

import estilo

from config import EXCEL_FACTURAS, EXCEL_LOCALES
from procesador import (
    ProcesadorGmailWorker, ProcesadorLocalWorker, escribir_resultados_en_excel,
)
from excel_manager import crear_archivo_locales_si_falta
from reconciliacion import ReconciliacionDialog
from no_leidas import CARPETA_NO_LEIDAS, NOMBRE_CARPETA, abrir_carpeta_no_leidas


def _version_app():
    """'DD/MM/AAAA HH:MM' del último commit aplicado, o '' si no se pudo saber
    (sin Git, o no instalada desde un repo)."""
    try:
        r = subprocess.run(
            ['git', 'log', '-1', '--format=%cd', '--date=format:%d/%m/%Y %H:%M'],
            cwd=str(Path(__file__).resolve().parent),
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else ''
    except Exception:
        return ''


class VentanaFacturas(QMainWindow):
    def __init__(self):
        super().__init__()
        titulo = 'Procesador de Facturas'
        version = _version_app()
        if version:
            titulo += f' — versión {version}'
        self.setWindowTitle(titulo)
        self.setGeometry(100, 80, 800, 680)
        self.setMinimumSize(660, 580)
        self._version = version
        self.worker = None
        self._procesando = False
        crear_archivo_locales_si_falta()   # deja listo el Excel de proveedores locales
        self._init_ui()
        self._log('Listo para trabajar. Empezá con "Insertar facturas".')

    def _init_ui(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 14)
        self.setCentralWidget(widget)

        # ── Encabezado ámbar ────────────────────────────────────────────
        encabezado = QFrame()
        encabezado.setProperty('clase', 'encabezado')
        enc_lo = QHBoxLayout(encabezado)
        enc_lo.setContentsMargins(20, 16, 20, 16)
        icono = QLabel()
        icono.setPixmap(estilo.icono_app().pixmap(40, 40))
        icono.setStyleSheet('background: rgba(255,255,255,0.22); border-radius: 12px; padding: 6px;')
        enc_lo.addWidget(icono)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        titulo = QLabel('Procesador de Facturas')
        titulo.setStyleSheet('color: white; font-size: 17pt; font-weight: 700; background: transparent;')
        subtitulo = QLabel('Facturas de AFIP en PDF al Excel  ·  Naiman')
        subtitulo.setStyleSheet('color: rgba(255,255,255,0.88); font-size: 10pt; background: transparent;')
        textos.addWidget(titulo)
        textos.addWidget(subtitulo)
        enc_lo.addLayout(textos, 1)
        if self._version:
            lbl_version = QLabel(f'versión {self._version}')
            lbl_version.setStyleSheet(
                'background: rgba(255,255,255,0.22); color: white; border-radius: 11px; '
                'padding: 4px 11px; font-size: 9pt;')
            enc_lo.addWidget(lbl_version, 0, Qt.AlignTop)
        layout.addWidget(encabezado)

        # ── Cómo se usa: 3 pasos ────────────────────────────────────────
        pasos_frame, pasos_lo = estilo.tarjeta('Cómo se usa', espacio=12)
        pasos = QHBoxLayout()
        pasos.setSpacing(12)
        for n, titulo_paso, detalle in (
            (1, 'Elegí los PDF', 'Apretá "Insertar" y elegí uno o varios.'),
            (2, 'Revisá cada una', 'Corregí lo que haga falta y confirmá.'),
            (3, 'Se guarda en el Excel', 'Queda en facturas.xlsx.'),
        ):
            caja = QHBoxLayout()
            caja.setSpacing(10)
            caja.addWidget(estilo.numero_paso(n), 0, Qt.AlignTop)
            txt = QLabel(f'<b>{titulo_paso}</b><br>'
                         f'<span style="color:{estilo.TEXTO_SUAVE}">{detalle}</span>')
            txt.setWordWrap(True)
            txt.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            txt.setMinimumHeight(txt.fontMetrics().lineSpacing() * 3 + 4)
            txt.setStyleSheet('background: transparent;')
            caja.addWidget(txt, 1)
            pasos.addLayout(caja, 1)
        pasos_lo.addLayout(pasos)
        nota = estilo.banner('error')
        nota.setText('Las celdas en <b>ROJO</b> del Excel hay que revisarlas y completarlas a mano.')
        pasos_lo.addWidget(nota)
        layout.addWidget(pasos_frame)

        # ── Acciones ────────────────────────────────────────────────────
        acciones = QHBoxLayout()
        acciones.setSpacing(10)
        self.btn_local = QPushButton('＋  Insertar facturas')
        estilo.variante(self.btn_local, 'primario')
        self.btn_local.setMinimumHeight(48)
        self.btn_local.setStyleSheet('font-size: 11.5pt;')
        self.btn_local.setToolTip('Seleccioná uno o más PDFs locales para procesar')
        self.btn_local.clicked.connect(self._insertar_local)
        acciones.addWidget(self.btn_local, 3)

        self.btn_excel = QPushButton('Abrir Excel')
        estilo.variante(self.btn_excel, 'fantasma')
        self.btn_excel.setMinimumHeight(48)
        self.btn_excel.setToolTip('Abre facturas.xlsx')
        self.btn_excel.clicked.connect(self._abrir_excel)
        acciones.addWidget(self.btn_excel, 1)
        layout.addLayout(acciones)

        secundarios = QHBoxLayout()
        secundarios.setSpacing(10)
        self.btn_proveedores = QPushButton('Agregar proveedores')
        estilo.variante(self.btn_proveedores, 'fantasma')
        self.btn_proveedores.setToolTip(
            'Abre el Excel donde podés cargar proveedores nuevos (CUIT, nombre, '
            'código de gasto y de rubro). Se usan en esta PC al procesar.'
        )
        self.btn_proveedores.clicked.connect(self._abrir_proveedores)
        secundarios.addWidget(self.btn_proveedores, 1)

        self.btn_no_leidas = QPushButton('Ver no leídas')
        estilo.variante(self.btn_no_leidas, 'fantasma')
        self.btn_no_leidas.setToolTip(
            f'Abre la carpeta "{NOMBRE_CARPETA}": copia de los PDF que el '
            'programa no pudo leer, para cargarlos a mano'
        )
        self.btn_no_leidas.clicked.connect(self._abrir_no_leidas)
        secundarios.addWidget(self.btn_no_leidas, 1)

        self.btn_gmail = QPushButton('Buscar en Gmail')
        estilo.variante(self.btn_gmail, 'enlace')
        self.btn_gmail.setToolTip(
            'Busca PDFs nuevos en Gmail, los procesa y etiqueta los ya procesados'
        )
        self.btn_gmail.clicked.connect(self._procesar_gmail)
        secundarios.addWidget(self.btn_gmail)

        for b in (self.btn_local, self.btn_excel, self.btn_proveedores,
                  self.btn_no_leidas, self.btn_gmail):
            b.setCursor(Qt.PointingHandCursor)
        layout.addLayout(secundarios)

        # ── Progreso (solo mientras procesa) ────────────────────────────
        self.fila_progreso = QWidget()
        prog_lo = QHBoxLayout(self.fila_progreso)
        prog_lo.setContentsMargins(0, 0, 0, 0)
        prog_lo.setSpacing(10)
        self.lbl_progreso = QLabel('Leyendo…')
        self.lbl_progreso.setProperty('clase', 'suave')
        prog_lo.addWidget(self.lbl_progreso)
        self.barra = QProgressBar()
        prog_lo.addWidget(self.barra, 1)
        self.btn_cancelar = QPushButton('Cancelar')
        estilo.variante(self.btn_cancelar, 'fantasma')
        self.btn_cancelar.clicked.connect(self._cancelar_worker)
        prog_lo.addWidget(self.btn_cancelar)
        self.fila_progreso.setVisible(False)
        layout.addWidget(self.fila_progreso)

        # ── Actividad (registro) + resumen de la última carga ───────────
        act_frame, act_lo = estilo.tarjeta(espacio=8)
        cab = QHBoxLayout()
        lbl_act = QLabel('Actividad')
        lbl_act.setProperty('clase', 'titulo_tarjeta')
        cab.addWidget(lbl_act)
        cab.addStretch()
        self.chips_resumen = {}
        for clave, tipo in (('ok', 'exito'), ('duplicados', 'neutro'),
                            ('errores', 'error'), ('verificar', 'aviso')):
            c = estilo.chip('', tipo)
            c.setVisible(False)
            self.chips_resumen[clave] = c
            cab.addWidget(c)
        act_lo.addLayout(cab)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        act_lo.addWidget(self.log_text, 1)
        layout.addWidget(act_frame, 1)

        # ── Pie ─────────────────────────────────────────────────────────
        pie = QHBoxLayout()
        ayuda = QLabel('Las facturas se guardan en facturas.xlsx (con respaldo automático).')
        ayuda.setProperty('clase', 'etiqueta')
        pie.addWidget(ayuda, 1)
        btn_salir = QPushButton('Salir')
        estilo.variante(btn_salir, 'fantasma')
        btn_salir.setStyleSheet('padding: 5px 14px;')
        btn_salir.clicked.connect(self.close)
        pie.addWidget(btn_salir)
        layout.addLayout(pie)
        self.show()

    # ------------------------------------------------------------------

    def _bloquear(self):
        self._procesando = True
        self.btn_gmail.setEnabled(False)
        self.btn_local.setEnabled(False)
        self.barra.setValue(0)
        self.lbl_progreso.setText('Leyendo…')
        self.btn_cancelar.setEnabled(True)
        self.fila_progreso.setVisible(True)
        self._log('─' * 55)

    def _desbloquear(self):
        self._procesando = False
        self.btn_gmail.setEnabled(True)
        self.btn_local.setEnabled(True)
        self.fila_progreso.setVisible(False)

    def _cancelar_worker(self):
        if self.worker is not None:
            self.worker.cancelar()
            self.btn_cancelar.setEnabled(False)
            self._log('… cancelando (termina la factura en curso)…')

    # ------------------------------------------------------------------
    # Gmail — procesa y escribe directamente (batch sin conciliación)
    # ------------------------------------------------------------------

    def _procesar_gmail(self):
        self._bloquear()
        self.worker = ProcesadorGmailWorker()
        self.worker.log.connect(self._log)
        self.worker.progreso.connect(self._progreso)
        self.worker.terminado.connect(self._finalizado)
        self.worker.error_critico.connect(self._error_critico)
        self.worker.start()

    # ------------------------------------------------------------------
    # Local — parsea → conciliación factura por factura → escribe
    # ------------------------------------------------------------------

    def _insertar_local(self):
        rutas, _ = QFileDialog.getOpenFileNames(
            self, 'Seleccionar facturas PDF', '', 'Archivos PDF (*.pdf)'
        )
        if not rutas:
            return

        self._bloquear()
        self.worker = ProcesadorLocalWorker([Path(r) for r in rutas])
        self.worker.log.connect(self._log)
        self.worker.progreso.connect(self._progreso)
        self.worker.preview.connect(self._abrir_conciliacion)
        self.worker.error_critico.connect(self._error_critico)
        self.worker.start()

    def _abrir_conciliacion(self, resultados):
        self._desbloquear()
        n_parseable = sum(1 for r in resultados if r['datos'] and not r['error'])
        if n_parseable == 0:
            self._log('✗ No se pudo leer ninguna factura.')
            copiados = any(r.get('copia_no_leida') for r in resultados)
            caja = QMessageBox(self)
            caja.setIcon(QMessageBox.Warning)
            caja.setWindowTitle('No se pudo leer ninguna factura')
            caja.setText(
                'Ninguno de los archivos elegidos pudo procesarse.\n\n'
                'Puede pasar si:\n'
                '  • el PDF es una foto o imagen escaneada (no texto),\n'
                '  • no es una factura A o C de AFIP,\n'
                '  • el archivo está dañado.\n\n'
                + (f'Quedó una copia en la carpeta "{NOMBRE_CARPETA}" para '
                   'cargarlas a mano.' if copiados else
                   'Probá con otro archivo o revisá que sea el PDF correcto.')
            )
            btn_ver = caja.addButton('Ver no leídas', QMessageBox.AcceptRole) if copiados else None
            caja.addButton('Cerrar', QMessageBox.RejectRole)
            caja.exec_()
            if btn_ver is not None and caja.clickedButton() == btn_ver:
                self._abrir_no_leidas()
            return

        dlg = ReconciliacionDialog(resultados, self)
        if dlg.exec_() == ReconciliacionDialog.Accepted:
            self._escribir(dlg.resultados_para_escribir())
        else:
            self._log('↩ Revisión cancelada. No se guardó nada.')

    def _escribir(self, resultados):
        # Reintenta sin perder la revisión ya hecha (caso típico: Excel abierto)
        while True:
            self._log('Guardando en Excel...')
            try:
                resumen = escribir_resultados_en_excel(resultados)
                self._finalizado(resumen)
                return
            except PermissionError as e:
                resp = QMessageBox.warning(
                    self, 'El Excel está abierto',
                    f'{e}\n\n'
                    'Cerrá el Excel y apretá "Reintentar". '
                    'No perdés lo que ya revisaste.',
                    QMessageBox.Retry | QMessageBox.Cancel, QMessageBox.Retry
                )
                if resp != QMessageBox.Retry:
                    self._log('↩ Guardado cancelado. La revisión no se guardó.')
                    return
            except Exception as e:
                self._error_critico(str(e))
                return

    # ------------------------------------------------------------------

    def _log(self, mensaje):
        self.log_text.append(_linea_html(mensaje))
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _progreso(self, actual, total):
        self.barra.setMaximum(total)
        self.barra.setValue(actual)
        self.lbl_progreso.setText(f'Leyendo {actual} de {total}…')

    def _mostrar_resumen(self, ok, duplicados, errores, verificar):
        textos = {
            'ok':         f'✓ Guardadas {ok}',
            'duplicados': f'Repetidas {duplicados}',
            'errores':    f'Con problemas {errores}',
            'verificar':  f'A revisar {verificar}',
        }
        valores = {'ok': ok, 'duplicados': duplicados, 'errores': errores, 'verificar': verificar}
        for clave, chip in self.chips_resumen.items():
            chip.setText(textos[clave])
            # "guardadas" siempre se muestra; el resto solo si hay alguna
            chip.setVisible(clave == 'ok' or valores[clave] > 0)

    def _finalizado(self, resumen):
        self._desbloquear()
        ok         = resumen.get('ok', 0)
        duplicados = resumen.get('duplicados', 0)
        errores    = resumen.get('errores', 0)
        verificar  = resumen.get('verificar', 0)

        self._mostrar_resumen(ok, duplicados, errores, verificar)
        self._log('─' * 55)
        self._log(
            f'✅  Listo — Guardadas: {ok}  |  '
            f'Repetidas: {duplicados}  |  '
            f'Con problemas: {errores}  |  '
            f'A revisar (rojo): {verificar}'
        )

        # Resumen en un cartel, en palabras simples
        partes = [f'Se guardaron {ok} factura(s) en el Excel.']
        if verificar:
            partes.append(
                f'\n⚠ {verificar} tienen celdas en ROJO que hay que revisar y '
                'completar a mano dentro del Excel.'
            )
        if duplicados:
            partes.append(f'\n{duplicados} ya estaban cargadas y se saltearon.')
        if errores:
            partes.append(
                f'\n{errores} no se pudieron leer: se copiaron a la carpeta '
                f'"{NOMBRE_CARPETA}" (y quedan anotadas en la hoja "ERRORES" del Excel).'
            )

        if ok == 0 and duplicados == 0 and errores == 0:
            QMessageBox.information(self, 'Terminado', 'No había facturas nuevas para cargar.')
            return

        mensaje = ' '.join(partes)
        caja = QMessageBox(self)
        caja.setIcon(QMessageBox.Information)
        caja.setWindowTitle('Terminado')
        caja.setText(mensaje)
        btn_abrir = caja.addButton('Abrir Excel', QMessageBox.AcceptRole) if ok > 0 else None
        btn_ver   = caja.addButton('Ver no leídas', QMessageBox.ActionRole) if errores else None
        caja.addButton('Cerrar', QMessageBox.RejectRole)
        caja.exec_()
        if btn_abrir is not None and caja.clickedButton() == btn_abrir:
            self._abrir_excel()
        elif btn_ver is not None and caja.clickedButton() == btn_ver:
            self._abrir_no_leidas()

    def _error_critico(self, mensaje):
        self._desbloquear()
        self._log(f'❌  {mensaje}')
        QMessageBox.critical(
            self,
            'No se pudo completar',
            f'{mensaje}\n\nCuando lo soluciones, volvé a intentarlo.'
        )

    def _abrir_archivo(self, path):
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception:
            QMessageBox.information(
                self, 'Abrilo a mano',
                'No pude abrir el archivo automáticamente.\n\n'
                f'Está guardado en:\n{path}'
            )

    def _abrir_excel(self):
        if not EXCEL_FACTURAS.exists():
            QMessageBox.information(
                self, 'Todavía no hay Excel',
                'Todavía no se cargó ninguna factura, así que el Excel no existe.\n\n'
                'Cargá facturas primero con "Insertar facturas".'
            )
            return
        self._abrir_archivo(str(EXCEL_FACTURAS))

    def _abrir_no_leidas(self):
        if not abrir_carpeta_no_leidas():
            QMessageBox.information(
                self, 'Abrila a mano',
                'No pude abrir la carpeta automáticamente.\n\n'
                f'Está en:\n{CARPETA_NO_LEIDAS}'
            )

    def _abrir_proveedores(self):
        crear_archivo_locales_si_falta()
        QMessageBox.information(
            self, 'Agregar proveedores',
            'Se va a abrir el Excel de proveedores de esta PC.\n\n'
            'Cargá una fila por proveedor nuevo: CUIT, Nombre, Código de Gasto y '
            'Código de Rubro. Los códigos podés consultarlos en las pestañas '
            '"Codigos de GASTO" y "Codigos de RUBRO" del mismo archivo.\n\n'
            'Guardá y cerrá el Excel. Los proveedores nuevos se usan la próxima '
            'vez que proceses facturas. (Estos cambios quedan en esta PC y no se '
            'pierden con las actualizaciones.)'
        )
        self._abrir_archivo(str(EXCEL_LOCALES))

    def closeEvent(self, event):
        # Evitar que cierre a mitad de un proceso y deje el Excel a medias
        if self._procesando:
            resp = QMessageBox.question(
                self, 'Hay un proceso en curso',
                'Se están procesando facturas en este momento.\n\n'
                '¿Seguro que querés cerrar? Se puede perder lo que falta cargar.',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if resp != QMessageBox.Yes:
                event.ignore()
                return
            if self.worker is not None:
                self.worker.cancelar()
                self.worker.wait(3000)
        event.accept()


def _linea_html(mensaje):
    """Una línea del registro de actividad, con color según el tipo."""
    texto = str(mensaje)
    if texto.strip() and set(texto.strip()) == {'─'}:
        return (f'<div style="color:{estilo.BORDE_FUERTE}; font-size:6pt;">'
                f'{"─" * 40}</div>')
    limpio = html.escape(texto).replace('  ', '&nbsp;&nbsp;')
    t = texto.lstrip()
    if t.startswith(('✓', '✅')):
        color, peso = estilo.VERDE, 600 if t.startswith('✅') else 400
    elif t.startswith('⚠'):
        color, peso = estilo.AVISO_TEXTO, 400
    elif t.startswith(('✗', '❌')):
        color, peso = estilo.ROJO, 400
    elif t.startswith(('↩', '…', '→')):
        color, peso = estilo.TEXTO_SUAVE, 400
    else:
        color, peso = estilo.TEXTO, 400
    return f'<span style="color:{color}; font-weight:{peso};">{limpio}</span>'
