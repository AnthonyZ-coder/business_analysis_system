import sqlite3

from app.db.schema.helpers import (
    add_column_if_not_exists,
    create_index_if_not_exists,
    execute_sql_list,
)


CONTRACT_PARSING_TABLE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS contract_parse_adjust_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_id INTEGER NOT NULL,
        field_name VARCHAR(64) NOT NULL,
        old_value TEXT,
        new_value TEXT,
        adjust_reason TEXT,
        source_type VARCHAR(32) DEFAULT 'MANUAL',
        adjusted_by VARCHAR(64),
        adjusted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        remarks TEXT,
        FOREIGN KEY (contract_id) REFERENCES contract_info(id)
    );
    """,
]


def init_contract_parsing_schema(conn: sqlite3.Connection) -> None:
    execute_sql_list(conn, CONTRACT_PARSING_TABLE_SQL)

    # 给 contract_info 补充人工修正标记字段
    add_column_if_not_exists(
        conn,
        table_name="contract_info",
        column_name="manual_adjusted_flag",
        alter_sql="""
        ALTER TABLE contract_info
        ADD COLUMN manual_adjusted_flag INTEGER DEFAULT 0
        """,
    )

    add_column_if_not_exists(
        conn,
        table_name="contract_info",
        column_name="last_adjusted_at",
        alter_sql="""
        ALTER TABLE contract_info
        ADD COLUMN last_adjusted_at DATETIME
        """,
    )

    # 调整日志表索引
    create_index_if_not_exists(
        conn,
        index_name="idx_contract_parse_adjust_log_contract_id",
        table_name="contract_parse_adjust_log",
        columns_sql="contract_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_contract_parse_adjust_log_field_name",
        table_name="contract_parse_adjust_log",
        columns_sql="field_name",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_contract_parse_adjust_log_adjusted_at",
        table_name="contract_parse_adjust_log",
        columns_sql="adjusted_at",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_contract_parse_adjust_log_adjusted_by",
        table_name="contract_parse_adjust_log",
        columns_sql="adjusted_by",
    )