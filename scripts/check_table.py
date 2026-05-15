import sqlite3
conn = sqlite3.connect('data/datos_consignacion.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contacto_disponibilidad'")
print('Tabla existe:', bool(cur.fetchone()))
