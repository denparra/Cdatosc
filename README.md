# DATOS_CONSIGNACION

Aplicación en Streamlit para registrar y organizar contactos de venta de
automóviles. Emplea SQLite para el almacenamiento y utiliza técnicas de
_scraping_ con **Requests** y **BeautifulSoup** para completar
automáticamente los datos de cada vehículo.

La aplicación cuenta con un sistema de autenticación de usuarios con roles
(**admin** o **user**) almacenados en la base de datos. El rol administrador
puede gestionar otras cuentas desde la interfaz.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso rápido

Ejecución directa con Streamlit:

```bash
streamlit run src/app.py
```

También existe el script `run.py` que permite empaquetar la aplicación con
PyInstaller o ejecutarla desde un entorno virtual ya configurado:

```bash
python run.py
```

Para instrucciones detalladas, consulta
[docs/README.md](docs/README.md).

## Pruebas

```bash
pytest
```
