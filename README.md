# DATOS_CONSIGNACION

Aplicación en Streamlit para registrar y organizar contactos de venta de
automóviles. Emplea SQLite para el almacenamiento y utiliza técnicas de
_scraping_ con **Requests** y **BeautifulSoup** para completar
automáticamente los datos de cada vehículo.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso rápido

Ejecución directa con Streamlit:

```bash
streamlit run src/app.py
```

Al iniciarse la base de datos se crea un usuario administrador por defecto:

- **usuario:** `admin`
- **contraseña:** `admin`

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
