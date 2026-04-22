/* @SQLines(Filename - docs/migration/datos_consignacion_sqlite_dump.sql:3, type - tables, source - links_contactos, target - links_contactos) */
CREATE TABLE links_contactos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_general VARCHAR(max) NOT NULL,
                fecha_creacion VARCHAR(max) NOT NULL,
                marca VARCHAR(max) NOT NULL,
                descripcion VARCHAR(max) NOT NULL
            , user_id INTEGER);

/* @SQLines(Filename - docs/migration/datos_consignacion_sqlite_dump.sql:49, type - tables, source - contactos, target - contactos) */
CREATE TABLE contactos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_auto VARCHAR(max) UNIQUE NOT NULL,
                telefono VARCHAR(max) NOT NULL,
                nombre VARCHAR(max) NOT NULL,
                auto VARCHAR(max) NOT NULL,
                precio REAL NOT NULL,
                descripcion VARCHAR(max) NOT NULL,
                id_link INTEGER,
                FOREIGN KEY (id_link) REFERENCES links_contactos(id)
            );

/* @SQLines(Filename - docs/migration/datos_consignacion_sqlite_dump.sql:7505, type - tables, source - mensajes, target - mensajes) */
CREATE TABLE mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion VARCHAR(max) NOT NULL
            , user_id INTEGER);

/* @SQLines(Filename - docs/migration/datos_consignacion_sqlite_dump.sql:7519, type - tables, source - export_logs, target - export_logs) */
CREATE TABLE export_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                mensaje_id INTEGER NOT NULL,
                link_generado VARCHAR(max) NOT NULL,
                fecha_exportacion VARCHAR(max) NOT NULL,
                FOREIGN KEY (contact_id) REFERENCES contactos(id),
                FOREIGN KEY (mensaje_id) REFERENCES mensajes(id)
            );

/* @SQLines(Filename - docs/migration/datos_consignacion_sqlite_dump.sql:25660, type - tables, source - users, target - users) */
CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(max) UNIQUE NOT NULL,
                password_hash VARCHAR(max) NOT NULL,
                role VARCHAR(max) NOT NULL
            );

/* @SQLines(Filename - docs/migration/datos_consignacion_sqlite_dump.sql:25670, type - tables, source - contactos_restringidos, target - contactos_restringidos) */
CREATE TABLE contactos_restringidos (
                telefono_normalizado VARCHAR(max) PRIMARY KEY,
                telefono_original VARCHAR(max) NOT NULL,
                motivo VARCHAR(max),
                created_at VARCHAR(max) NOT NULL,
                created_by INTEGER NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users(id)
            );

/* @SQLines(Filename - docs/migration/datos_consignacion_sqlite_dump.sql:26082, type - tables, source - clientes_interesados, target - clientes_interesados) */
CREATE TABLE clientes_interesados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha VARCHAR(max) NOT NULL,
                auto VARCHAR(max) NOT NULL,
                numero VARCHAR(max) NOT NULL,
                link VARCHAR(max) NOT NULL,
                correo VARCHAR(max),
                user_id INTEGER,
                created_at VARCHAR(max) NOT NULL DEFAULT (convert(datetime, 'now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

/* @SQLines(Filename - docs/migration/datos_consignacion_sqlite_dump.sql:26093, type - tables, source - contactos_restringidos_link, target - contactos_restringidos_link) */
CREATE TABLE contactos_restringidos_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telefono_normalizado VARCHAR(max) NOT NULL,
                telefono_original VARCHAR(max) NOT NULL,
                link_id INTEGER NOT NULL,
                motivo VARCHAR(max),
                created_at VARCHAR(max) NOT NULL,
                created_by INTEGER NOT NULL,
                UNIQUE(telefono_normalizado, link_id),
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (link_id) REFERENCES links_contactos(id) ON DELETE CASCADE
            );

/* @SQLines(Filename - docs/migration/datos_consignacion_sqlite_dump.sql:26105, type - tables, source - contactos_restringidos_contacto, target - contactos_restringidos_contacto) */
CREATE TABLE contactos_restringidos_contacto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telefono_normalizado VARCHAR(max) NOT NULL,
                telefono_original VARCHAR(max) NOT NULL,
                contact_id INTEGER NOT NULL,
                motivo VARCHAR(max),
                created_at VARCHAR(max) NOT NULL,
                created_by INTEGER NOT NULL,
                UNIQUE(contact_id),
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (contact_id) REFERENCES contactos(id) ON DELETE CASCADE
            );

/* @SQLines(Filename - docs/migration/datos_consignacion_sqlite_dump.sql:26118, type - tables, source - sqlite_sequence, target - sqlite_sequence) */
CREATE TABLE sqlite_sequence(name,seq);