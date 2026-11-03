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
        self.setGeometry(100, 80, 780, 660)
        self.setMinimumSize(640, 560)
        self.worker = None
        self._procesando = False
        crear_archivo_locales_si_falta()   # deja listo el Excel de proveedores locales
        self._init_ui()
        self._log('Listo para trabajar. Empezá con "Insertar facturas".')

    def _init_ui(self):
        fondo = QWidget()
        fondo.setObjectName('fondo')
        layout = QVBoxLayout(fondo)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 24)
        self.setCentralWidget(fondo)

        # ── Encabezado ────────────────────────────────────────────────
        titulo = QLabel('Procesador de Facturas')
        titulo.setObjectName('titulo')
        layout.addWidget(titulo)
        subtitulo = 'Pasa las facturas de AFIP en PDF al Excel'
        version = _version_app()
        if version:
            subtitulo += f'   ·   versión {version}'
        lbl_sub = QLabel(subtitulo)
        lbl_sub.setObjectName('subtitulo')
        layout.addWidget(lbl_sub)

        # ── Los 3 pasos ───────────────────────────────────────────────
        pasos = QHBoxLayout()
        pasos.setSpacing(12)
        for numero, texto in (
            ('1', 'Apretá "Insertar facturas" y elegí uno o varios PDF.'),
            ('2', 'Revisá los datos de cada factura y confirmá.'),
            ('3', 'Se guardan en el Excel. Las celdas en ROJO hay que revisarlas a mano.'),
        ):
            pasos.addWidget(self._tarjeta_paso(numero, texto), 1)
        layout.addLayout(pasos)

        # ── Acciones ──────────────────────────────────────────────────
        self.btn_local = QPushButton('📄   Insertar facturas')
        estilo.marcar(self.btn_local, variante='primario')
        self.btn_local.setMinimumHeight(50)
        self.btn_local.setFont(estilo.fuente(12, negrita=True))
        self.btn_local.setCursor(Qt.PointingHandCursor)
        self.btn_local.setToolTip('Seleccioná uno o más PDFs locales para procesar')
        self.btn_local.clicked.connect(self._insertar_local)
        layout.addWidget(self.btn_local)

        secundarios = QHBoxLayout()
        secundarios.setSpacing(10)

        self.btn_excel = QPushButton('📊   Abrir Excel')
        self.btn_excel.setMinimumHeight(40)
        self.btn_excel.clicked.connect(self._abrir_excel)
        secundarios.addWidget(self.btn_excel, 1)

        self.btn_proveedores = QPushButton('➕   Agregar proveedores')
        self.btn_proveedores.setMinimumHeight(40)
        self.btn_proveedores.setToolTip(
            'Abre el Excel donde podés cargar proveedores nuevos (CUIT, nombre, '
            'código de gasto y de rubro). Se usan en esta PC al procesar.'
        )
        self.btn_proveedores.clicked.connect(self._abrir_proveedores)
        secundarios.addWidget(self.btn_proveedores, 1)

        self.btn_gmail = QPushButton('📧  Buscar en Gmail')
        estilo.marcar(self.btn_gmail, variante='enlace')
        self.btn_gmail.setMinimumHeight(40)
        self.btn_gmail.setToolTip(
            'Busca PDFs nuevos en Gmail, los procesa y etiqueta los ya procesados'
        )
        self.btn_gmail.clicked.connect(self._procesar_gmail)
        secundarios.addWidget(self.btn_gmail)

        for b in (self.btn_excel, self.btn_proveedores, self.btn_gmail):
            b.setCursor(Qt.PointingHandCursor)
        layout.addLayout(secundarios)

        # ── Actividad (registro + progreso) ───────────────────────────
        actividad = estilo.tarjeta(QFrame())
        act_lo = QVBoxLayout(actividad)
        act_lo.setContentsMargins(16, 14, 16, 14)
        act_lo.setSpacing(10)

        lbl_act = QLabel('ACTIVIDAD')
        lbl_act.setObjectName('seccion')
        act_lo.addWidget(lbl_act)

        self.log_text = QTextEdit()
        self.log_text.setObjectName('log')
        self.log_text.setReadOnly(True)
        self.log_text.setFont(estilo.fuente(9, mono=True))
        act_lo.addWidget(self.log_text, 1)

        pie = QHBoxLayout()
        self.barra = QProgressBar()
        self.barra.setTextVisible(False)
        self.barra.setVisible(False)
        pie.addWidget(self.barra, 1)
        self.btn_cancelar = QPushButton('✕  Cancelar')
        estilo.marcar(self.btn_cancelar, variante='peligro')
        self.btn_cancelar.setVisible(False)
        self.btn_cancelar.clicked.connect(self._cancelar_worker)
        pie.addWidget(self.btn_cancelar)
        act_lo.addLayout(pie)

        layout.addWidget(actividad, 1)
        self.show()

    def _tarjeta_paso(self, numero, texto):
        tarjeta = estilo.tarjeta(QFrame())
        lo = QHBoxLayout(tarjeta)
        lo.setContentsMargins(12, 12, 12, 12)
        lo.setSpacing(10)
        num = QLabel(numero)
        num.setObjectName('paso_num')
        num.setFixedSize(28, 28)
        num.setAlignment(Qt.AlignCenter)
        lo.addWidget(num, 0, Qt.AlignTop)
        lbl = QLabel(texto)
        lbl.setWordWrap(True)
        lo.addWidget(lbl, 1)
        return tarjeta

    # ------------------------------------------------------------------

    def _bloquear(self):
        self._procesando = True
        self.btn_gmail.setEnabled(False)
        self.btn_local.setEnabled(False)
        self.barra.setValue(0)
        self.barra.setVisible(True)
        self.btn_cancelar.setEnabled(True)
        self.btn_cancelar.setVisible(True)
        self._log('─' * 55)

    def _desbloquear(self):
        self._procesando = False
        self.btn_gmail.setEnabled(True)
        self.btn_local.setEnabled(True)
        self.barra.setVisible(False)
        self.btn_cancelar.setVisible(False)

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
            QMessageBox.warning(
                self,
                'No se pudo leer ninguna factura',
                'Ninguno de los archivos elegidos pudo procesarse.\n\n'
                'Puede pasar si:\n'
                '  • el PDF es una foto o imagen escaneada (no texto),\n'
                '  • no es una factura A o C de AFIP,\n'
                '  • el archivo está dañado.\n\n'
                'Probá con otro archivo o revisá que sea el PDF correcto.'
            )
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
        self.log_text.append(mensaje)
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _progreso(self, actual, total):
        self.barra.setMaximum(total)
        self.barra.setValue(actual)

    def _finalizado(self, resumen):
        self._desbloquear()
        ok         = resumen.get('ok', 0)
        duplicados = resumen.get('duplicados', 0)
        errores    = resumen.get('errores', 0)
        verificar  = resumen.get('verificar', 0)

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
                f'\n{errores} no se pudieron leer (mirá la hoja "ERRORES" del Excel).'
            )

        if ok == 0 and duplicados == 0 and errores == 0:
            QMessageBox.information(self, 'Terminado', 'No había facturas nuevas para cargar.')
            return

        mensaje = ' '.join(partes)
        caja = QMessageBox(self)
        caja.setIcon(QMessageBox.Information)
        caja.setWindowTitle('Terminado')
        caja.setText(mensaje)
        if ok > 0:
            btn_abrir = caja.addButton('Abrir Excel', QMessageBox.AcceptRole)
            caja.addButton('Cerrar', QMessageBox.RejectRole)
            caja.exec_()
            if caja.clickedButton() == btn_abrir:
                self._abrir_excel()
        else:
            caja.exec_()

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
