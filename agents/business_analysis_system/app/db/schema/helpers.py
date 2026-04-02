import sqlite3
from typing import List


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    rows = cursor.fetchall()
    return [row[1] for row in rows]


def column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    columns = get_table_columns(conn, table_name)
    return column_name in columns


def add_column_if_not_exists(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    alter_sql: str,
) -> None:
    if not table_exists(conn, table_name):
        return

    if not column_exists(conn, table_name, column_name):
        conn.execute(alter_sql)


def execute_sql_list(conn: sqlite3.Connection, sql_list: List[str]) -> None:
    for sql in sql_list:
        cleaned_sql = (sql or "").strip()
        if not cleaned_sql:
            continue
        conn.execute(cleaned_sql)


def create_index_if_not_exists(
    conn: sqlite3.Connection,
    index_name: str,
    table_name: str,
    columns_sql: str,
    unique: bool = False,
) -> None:
    unique_sql = "UNIQUE " if unique else ""
    sql = f"CREATE {unique_sql}INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_sql})"
    conn.execute(sql)