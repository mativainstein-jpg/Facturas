import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QApplication, QMessageBox
import estilo
from config import BASE_DIR
from ventana import VentanaFacturas

LOG_ERRORES = BASE_DIR / 'error.log'


def _manejar_excepcion(tipo, valor, tb):
    """
    Handler global: sin esto, un error no previsto cierra la app sin avisar
    (la ventana de consola está oculta en el .exe compilado).
    """
    detalle = ''.join(traceback.format_exception(tipo, valor, tb))

    try:
        with open(str(LOG_ERRORES), 'a', encoding='utf-8') as f:
            f.write(f'\n{"=" * 60}\n{datetime.now()}\n{detalle}\n')
    except Exception:
        pass

    try:
        QMessageBox.critical(
            None,
            'Error inesperado',
            'Ocurrió un error inesperado.\n\n'
            f'Se guardó el detalle en:\n{LOG_ERRORES}\n\n'
            f'{tipo.__name__}: {valor}\n\n'
            'Si el problema continúa, enviá ese archivo para revisarlo.'
        )
    except Exception:
        pass


if __name__ == '__main__':
    sys.excepthook = _manejar_excepcion
    # Nítido en notebooks con escalado de Windows (125%, 150%...). Tiene que ir
    # antes de crear la QApplication.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    if hasattr(QGuiApplication, 'setHighDpiScaleFactorRoundingPolicy'):
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    estilo.aplicar(app)
    window = VentanaFacturas()
    sys.exit(app.exec_())
