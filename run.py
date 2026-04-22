import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

_PORT = 8501


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # Carpeta temporal donde PyInstaller extrae el bundle
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def _open_browser(port: int, delay: float = 3.0) -> None:
    """Espera que Streamlit arranque y luego abre el navegador por defecto."""
    time.sleep(delay)
    webbrowser.open(f"http://localhost:{port}")


def run_streamlit():
    script_path = resource_path(os.path.join("src", "app.py"))
    runtime_base = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent
    )
    os.environ["DATOS_CONSIGNACION_HOME"] = str(runtime_base)

    if getattr(sys, "frozen", False):
        # Ejecutable PyInstaller: streamlit viene empaquetado dentro del bundle.
        # No usar subprocess porque "streamlit" no existe en el PATH de la PC destino.
        #
        # En el bundle, __file__ de streamlit/config.py apunta a _MEIPASS (sin
        # "site-packages"), por lo que Streamlit se autodetecta en developmentMode=True.
        # Eso bloquea el arranque vía AssertionError si se pasa --server.port y además
        # hace que intente conectarse a un dev-server webpack en lugar de servir los
        # assets estáticos empaquetados. Se fuerza a False mediante la variable de entorno
        # antes de que config.py se inicialice.
        os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

        # Abre el navegador automáticamente una vez que el servidor esté listo.
        threading.Thread(
            target=_open_browser, args=(_PORT,), daemon=True
        ).start()
        sys.argv = [
            "streamlit",
            "run",
            script_path,
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ]
        from streamlit.web import cli as stcli
        stcli.main()
    else:
        import subprocess
        subprocess.run(
            ["streamlit", "run", script_path],
            env=os.environ.copy(),
            cwd=str(runtime_base),
        )


if __name__ == "__main__":
    run_streamlit()
