import sqlite3

from app.db.schema.helpers import create_index_if_not_exists, execute_sql_list


RESULT_STORAGE_TABLE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS result_storage_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result_code VARCHAR(64) NOT NULL UNIQUE,
        source_record_type VARCHAR(64) NOT NULL,
        source_record_id INTEGER NOT NULL,

        billing_period VARCHAR(16) NOT NULL,
        billing_date DATE,

        project_code VARCHAR(64) NOT NULL,
        project_name VARCHAR(255),

        contract_id INTEGER,
        contract_code VARCHAR(64),
        contract_name VARCHAR(255),

        rule_id INTEGER,
        rule_code VARCHAR(64),
        rule_name VARCHAR(255),

        input_amount DECIMAL(18,2) NOT NULL,
        amount_type VARCHAR(32) NOT NULL,
        tax_included_amount DECIMAL(18,2) NOT NULL,
        tax_excluded_amount DECIMAL(18,2) NOT NULL,
        tax_rate DECIMAL(10,4) DEFAULT 0.06,

        result_status VARCHAR(32) DEFAULT 'STORED',
        version_no VARCHAR(32) DEFAULT 'v0.1',

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(64),
        updated_by VARCHAR(64),
        remarks TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS result_storage_detail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result_id INTEGER NOT NULL,

        product_code VARCHAR(64) NOT NULL,
        product_name VARCHAR(128) NOT NULL,
        category_code VARCHAR(64) NOT NULL,

        split_ratio DECIMAL(10,6) NOT NULL,
        tax_included_amount DECIMAL(18,2) NOT NULL,
        tax_excluded_amount DECIMAL(18,2) NOT NULL,

        sort_order INTEGER DEFAULT 0,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        remarks TEXT,

        FOREIGN KEY (result_id) REFERENCES result_storage_record(id),
        FOREIGN KEY (product_code) REFERENCES product_line_definition(product_code),
        FOREIGN KEY (category_code) REFERENCES product_line_category(category_code)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_status_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        business_key VARCHAR(128) NOT NULL,
        business_type VARCHAR(64) NOT NULL,

        source_module VARCHAR(64) NOT NULL,

        from_status VARCHAR(64),
        to_status VARCHAR(64) NOT NULL,

        action_type VARCHAR(64),
        operator VARCHAR(64),
        action_time DATETIME DEFAULT CURRENT_TIMESTAMP,

        related_record_type VARCHAR(64),
        related_record_id INTEGER,

        message TEXT,
        ext_json TEXT
    );
    """,
]


def init_result_storage_schema(conn: sqlite3.Connection) -> None:
    execute_sql_list(conn, RESULT_STORAGE_TABLE_SQL)

    # result_storage_record 主表索引
    create_index_if_not_exists(
        conn,
        index_name="idx_result_storage_record_code",
        table_name="result_storage_record",
        columns_sql="result_code",
        unique=True,
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_result_storage_record_source_record",
        table_name="result_storage_record",
        columns_sql="source_record_type, source_record_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_result_storage_record_billing_period",
        table_name="result_storage_record",
        columns_sql="billing_period",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_result_storage_record_project_code",
        table_name="result_storage_record",
        columns_sql="project_code",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_result_storage_record_contract_id",
        table_name="result_storage_record",
        columns_sql="contract_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_result_storage_record_rule_id",
        table_name="result_storage_record",
        columns_sql="rule_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_result_storage_record_result_status",
        table_name="result_storage_record",
        columns_sql="result_status",
    )

    # result_storage_detail 明细表索引
    create_index_if_not_exists(
        conn,
        index_name="idx_result_storage_detail_result_id",
        table_name="result_storage_detail",
        columns_sql="result_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_result_storage_detail_product_code",
        table_name="result_storage_detail",
        columns_sql="product_code",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_result_storage_detail_category_code",
        table_name="result_storage_detail",
        columns_sql="category_code",
    )

    # workflow_status_log 状态日志表索引
    create_index_if_not_exists(
        conn,
        index_name="idx_workflow_status_log_business_key",
        table_name="workflow_status_log",
        columns_sql="business_key",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_workflow_status_log_business_type",
        table_name="workflow_status_log",
        columns_sql="business_type",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_workflow_status_log_source_module",
        table_name="workflow_status_log",
        columns_sql="source_module",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_workflow_status_log_related_record",
        table_name="workflow_status_log",
        columns_sql="related_record_type, related_record_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_workflow_status_log_action_time",
        table_name="workflow_status_log",
        columns_sql="action_time",
    )