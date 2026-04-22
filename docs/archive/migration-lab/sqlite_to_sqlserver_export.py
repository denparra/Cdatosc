import sqlite3
from pathlib import Path


def map_type(sqlite_type: str, is_key: bool = False) -> str:
    t = (sqlite_type or "").upper()
    if "INT" in t:
        return "INT"
    if "REAL" in t or "FLOA" in t or "DOUB" in t:
        return "FLOAT"
    if "BLOB" in t:
        return "VARBINARY(MAX)"
    if "CHAR" in t or "CLOB" in t or "TEXT" in t:
        return "NVARCHAR(450)" if is_key else "NVARCHAR(MAX)"
    if "DATE" in t or "TIME" in t:
        return "NVARCHAR(64)"
    if "NUM" in t or "DEC" in t:
        return "DECIMAL(38, 10)"
    return "NVARCHAR(MAX)"


def quote_ident(name: str) -> str:
    return f"[{name}]"


def to_sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bytes):
        return "0x" + value.hex().upper()
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value).replace("'", "''")
    return f"N'{text}'"


def grouped_foreign_keys(conn: sqlite3.Connection, table: str):
    rows = conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
    grouped = {}
    for row in rows:
        fid = row[0]
        grouped.setdefault(
            fid,
            {
                "table": row[2],
                "from": [],
                "to": [],
                "on_update": row[5],
                "on_delete": row[6],
            },
        )
        grouped[fid]["from"].append(row[3])
        grouped[fid]["to"].append(row[4])
    return grouped.values()


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    sqlite_db = root / "data" / "datos_consignacion.db"
    out_sql = root / "docs" / "migration" / "datos_consignacion_mssql.sql"

    conn = sqlite3.connect(sqlite_db)
    conn.row_factory = sqlite3.Row

    tables = [
        r[0]
        for r in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    ]

    table_sql_map = {
        r[0]: r[1] or ""
        for r in conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }

    out = []
    out.append("SET NOCOUNT ON;")
    out.append("SET XACT_ABORT ON;")
    out.append("")

    identity_tables = set()
    foreign_keys_sql = []

    for table in tables:
        create_src = (table_sql_map.get(table) or "").upper()
        has_autoincrement = "AUTOINCREMENT" in create_src

        cols = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        pk_cols = sorted([c for c in cols if c[5] > 0], key=lambda x: x[5])
        single_int_pk = (
            len(pk_cols) == 1 and "INT" in (pk_cols[0][2] or "").upper() and has_autoincrement
        )

        key_columns = {c[1] for c in pk_cols}
        idx_rows = conn.execute(f'PRAGMA index_list("{table}")').fetchall()
        for idx in idx_rows:
            is_unique = idx[2] == 1
            if not is_unique:
                continue
            idx_name = idx[1]
            idx_cols = conn.execute(f'PRAGMA index_info("{idx_name}")').fetchall()
            for ic in idx_cols:
                key_columns.add(ic[2])
        fk_rows = conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
        for fk_row in fk_rows:
            key_columns.add(fk_row[3])

        col_defs = []
        for c in cols:
            name = c[1]
            col_type = c[2]
            notnull = c[3] == 1
            is_pk = c[5] > 0

            if single_int_pk and is_pk:
                col_defs.append(f"    {quote_ident(name)} INT IDENTITY(1,1) NOT NULL PRIMARY KEY")
                identity_tables.add(table)
                continue

            mapped = map_type(col_type, is_key=name in key_columns)
            null_sql = "NOT NULL" if (notnull or is_pk) else "NULL"
            col_defs.append(f"    {quote_ident(name)} {mapped} {null_sql}")

        constraints = []
        if pk_cols and not single_int_pk:
            pk_name = f"PK_{table}"
            pk_expr = ", ".join(quote_ident(c[1]) for c in pk_cols)
            constraints.append(f"    CONSTRAINT {quote_ident(pk_name)} PRIMARY KEY ({pk_expr})")

        for idx in idx_rows:
            idx_name = idx[1]
            is_unique = idx[2] == 1
            origin = idx[3]
            if not is_unique or origin == "pk":
                continue
            idx_cols = conn.execute(f'PRAGMA index_info("{idx_name}")').fetchall()
            if not idx_cols:
                continue
            uq_cols = ", ".join(quote_ident(ic[2]) for ic in idx_cols)
            uq_name = f"UQ_{table}_{idx_name}"
            constraints.append(f"    CONSTRAINT {quote_ident(uq_name)} UNIQUE ({uq_cols})")

        all_defs = col_defs + constraints
        out.append(f"IF OBJECT_ID(N'dbo.{table}', N'U') IS NOT NULL DROP TABLE dbo.{table};")
        out.append(f"CREATE TABLE dbo.{table} (")
        out.append(",\n".join(all_defs))
        out.append(");")
        out.append("")

        for fk in grouped_foreign_keys(conn, table):
            fk_name = f"FK_{table}_{fk['table']}_{'_'.join(fk['from'])}"
            from_cols = ", ".join(quote_ident(c) for c in fk["from"])
            to_cols = ", ".join(quote_ident(c) for c in fk["to"])
            on_delete = fk["on_delete"] if fk["on_delete"] and fk["on_delete"] != "NO ACTION" else ""
            on_update = fk["on_update"] if fk["on_update"] and fk["on_update"] != "NO ACTION" else ""
            fk_sql = (
                f"ALTER TABLE dbo.{table} WITH NOCHECK ADD CONSTRAINT {quote_ident(fk_name)} "
                f"FOREIGN KEY ({from_cols}) REFERENCES dbo.{fk['table']} ({to_cols})"
            )
            if on_delete:
                fk_sql += f" ON DELETE {on_delete}"
            if on_update:
                fk_sql += f" ON UPDATE {on_update}"
            fk_sql += ";"
            foreign_keys_sql.append(fk_sql)

    for table in tables:
        rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
        if not rows:
            continue
        col_names = rows[0].keys()
        col_expr = ", ".join(quote_ident(c) for c in col_names)

        out.append(f"-- Data for {table}")
        if table in identity_tables:
            out.append(f"SET IDENTITY_INSERT dbo.{table} ON;")

        for row in rows:
            vals = ", ".join(to_sql_literal(row[c]) for c in col_names)
            out.append(f"INSERT INTO dbo.{table} ({col_expr}) VALUES ({vals});")

        if table in identity_tables:
            out.append(f"SET IDENTITY_INSERT dbo.{table} OFF;")
        out.append("")

    out.append("-- Foreign keys")
    out.extend(foreign_keys_sql)
    out.append("")
    out_sql.write_text("\n".join(out), encoding="utf-8")
    print(f"Generated: {out_sql}")
    print(f"Tables: {len(tables)}")


if __name__ == "__main__":
    main()
