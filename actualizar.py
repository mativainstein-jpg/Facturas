"""
Busca la última versión de la app en el repositorio y la aplica.

Diseñado para ser a prueba de fallos:
  - Si no hay git, o no es un repo, o no hay internet → no hace nada y deja
    que la app abra con la versión que ya está en disco.
  - Nunca corta el arranque de la app: cualquier problema se informa y se sigue.

Se ejecuta desde procesar.bat ANTES de abrir la aplicación, SIEMPRE, para que
el administrativo no tenga que pensar en nada. Está en Python (y no en el
.bat) para que actualizarse a sí mismo sea seguro: Python carga todo el
archivo en memoria antes de ejecutarlo.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
GIT_DIR = BASE_DIR / '.git'

# Que git nunca se quede esperando una contraseña (ni en la consola ni en la
# ventana de login del administrador de credenciales de Windows): si falta la
# credencial, falla enseguida y la app abre con la versión que ya tiene.
_ENV_GIT = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'never'}
DIAS_AVISO = 7
# Marca propia de la última descarga exitosa. FETCH_HEAD no sirve: git lo
# reescribe aunque la descarga falle. Dentro de .git, nadie la versiona.
MARCA_OK = GIT_DIR / 'facturas_ultima_actualizacion'


def _git(*args, timeout=30):
    """Corre un comando git en la carpeta de la app. Devuelve (ok, salida)."""
    try:
        r = subprocess.run(
            ['git', *args],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_ENV_GIT,
        )
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return False, 'git-no-instalado'
    except subprocess.TimeoutExpired:
        return False, 'timeout'
    except Exception as e:
        return False, str(e)


def _version_actual():
    """'DD/MM/AAAA;HH:MM' del último commit aplicado, o None si no se pudo saber."""
    ok, salida = _git('log', '-1', '--format=%cd', '--date=format:%d/%m/%Y;%H:%M', timeout=10)
    return salida.strip() if ok and salida else None


def _destrabar_lock():
    """Si una actualización anterior se cortó (por ejemplo, por el timeout),
    puede quedar .git/index.lock y desde ahí git falla siempre. Un lock de
    más de 10 minutos es de una corrida muerta: se borra."""
    lock = GIT_DIR / 'index.lock'
    try:
        if lock.exists() and time.time() - lock.stat().st_mtime > 600:
            lock.unlink()
    except OSError:
        pass


def _avisar_si_hace_mucho():
    try:
        dias = int((time.time() - MARCA_OK.stat().st_mtime) // 86400)
    except OSError:
        return   # nunca hubo una descarga exitosa con esta versión: sin dato
    if dias >= DIAS_AVISO:
        print()
        print('  ' + '!' * 60)
        print(f'  !!  AVISO: hace {dias} dias que esta PC no recibe actualizaciones.')
        print('  !!  La app abre igual, pero avisale a Mati.')
        print('  ' + '!' * 60)
        print()


def _mostrar_version():
    version = _version_actual()
    if version:
        print(f'  Version (fecha;hora): {version}')


def main():
    # ¿git disponible?
    ok, _ = _git('--version', timeout=10)
    if not ok:
        print('  [i] Git no esta instalado: se usa la version actual.')
        return

    # ¿esta carpeta es un repositorio git?
    ok, _ = _git('rev-parse', '--is-inside-work-tree', timeout=10)
    if not ok:
        print('  [i] La app no se instalo con Git: se usa la version actual.')
        return

    # Rama actual
    ok, rama = _git('rev-parse', '--abbrev-ref', 'HEAD', timeout=10)
    if not ok or not rama:
        print('  [i] No pude determinar la version: se usa la actual.')
        return

    # Buscar cambios en el servidor (acá se necesita internet). Timeout corto:
    # si la conexión está mala, mejor fallar rápido y abrir con lo que hay
    # en vez de colgarse un buen rato en la pantalla de arranque.
    print('  Buscando actualizaciones...')
    # Solo la rama propia: las demás (el bot, otras PCs) no hacen falta.
    _destrabar_lock()
    ok, _ = _git('fetch', '--quiet', 'origin', rama, timeout=10)
    if not ok:
        print('  [i] Sin internet o sin acceso: se usa la version que ya tenes.')
        _avisar_si_hace_mucho()
        _mostrar_version()
        return
    try:
        MARCA_OK.touch()
    except OSError:
        pass

    # Aplicar la última versión sin riesgo de conflictos.
    # Los datos del usuario (facturas.xlsx, token.json, credentials.json) están
    # en .gitignore, así que esto NO los toca.
    ok, _ = _git('reset', '--hard', '--quiet', f'origin/{rama}', timeout=15)
    if ok:
        print('  Version actualizada a la ultima.')
    else:
        print('  [i] No pude actualizar: se usa la version que ya tenes.')
    _mostrar_version()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Pase lo que pase, nunca frenar el arranque de la app.
        print(f'  [i] No se pudo verificar actualizaciones ({e}). Se abre igual.')
    sys.exit(0)
