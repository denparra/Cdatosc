# DATOS_CONSIGNACION

Esta aplicación de Streamlit permite recolectar y administrar contactos de venta de autos. Los datos se guardan en SQLite y se obtienen automáticamente desde páginas de vehículos mediante scraping.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecutar la aplicación

```bash
streamlit run src/app.py
```

La exportación permite generar un archivo HTML con enlaces de WhatsApp listos para enviar (sin adjuntar imágenes).

Para más detalles sobre el proyecto consulta [docs/README.md](docs/README.md).

## Pruebas

```bash
pytest
```
