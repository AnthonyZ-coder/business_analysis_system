import sqlite3

from app.db.schema.helpers import create_index_if_not_exists, execute_sql_list


PHASE_INCOME_TABLE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS phase_income_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase_income_code VARCHAR(64) NOT NULL UNIQUE,
        billing_period VARCHAR(16) NOT NULL,
        billing_date DATE,

        project_code VARCHAR(64) NOT NULL,
        project_name VARCHAR(255),

        contract_id INTEGER,
        contract_code VARCHAR(64),
        contract_name VARCHAR(255),

        rule_id INTEGER NOT NULL,
        rule_code VARCHAR(64),
        rule_name VARCHAR(255),

        input_amount DECIMAL(18,2) NOT NULL,
        amount_type VARCHAR(32) NOT NULL,
        tax_included_amount DECIMAL(18,2) NOT NULL,
        tax_excluded_amount DECIMAL(18,2) NOT NULL,
        tax_rate DECIMAL(10,4) DEFAULT 0.06,

        calc_status VARCHAR(32) DEFAULT 'CALCULATED',
        source_type VARCHAR(32) DEFAULT 'MANUAL',

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(64),
        updated_by VARCHAR(64),
        remarks TEXT,

        FOREIGN KEY (contract_id) REFERENCES contract_info(id),
        FOREIGN KEY (rule_id) REFERENCES product_split_rule(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS phase_income_detail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase_income_id INTEGER NOT NULL,

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

        FOREIGN KEY (phase_income_id) REFERENCES phase_income_record(id),
        FOREIGN KEY (product_code) REFERENCES product_line_definition(product_code),
        FOREIGN KEY (category_code) REFERENCES product_line_category(category_code)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS phase_income_category_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phase_income_id INTEGER NOT NULL,
        category_code VARCHAR(64) NOT NULL,
        category_name VARCHAR(128) NOT NULL,

        split_ratio DECIMAL(10,6) NOT NULL,
        tax_included_amount DECIMAL(18,2) NOT NULL,
        tax_excluded_amount DECIMAL(18,2) NOT NULL,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        remarks TEXT,

        FOREIGN KEY (phase_income_id) REFERENCES phase_income_record(id),
        FOREIGN KEY (category_code) REFERENCES product_line_category(category_code)
    );
    """,
]


def init_phase_income_schema(conn: sqlite3.Connection) -> None:
    execute_sql_list(conn, PHASE_INCOME_TABLE_SQL)

    # 主表索引
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_record_code",
        table_name="phase_income_record",
        columns_sql="phase_income_code",
        unique=True,
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_record_billing_period",
        table_name="phase_income_record",
        columns_sql="billing_period",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_record_project_code",
        table_name="phase_income_record",
        columns_sql="project_code",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_record_contract_id",
        table_name="phase_income_record",
        columns_sql="contract_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_record_rule_id",
        table_name="phase_income_record",
        columns_sql="rule_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_record_calc_status",
        table_name="phase_income_record",
        columns_sql="calc_status",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_record_source_type",
        table_name="phase_income_record",
        columns_sql="source_type",
    )

    # 明细表索引
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_detail_phase_income_id",
        table_name="phase_income_detail",
        columns_sql="phase_income_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_detail_product_code",
        table_name="phase_income_detail",
        columns_sql="product_code",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_detail_category_code",
        table_name="phase_income_detail",
        columns_sql="category_code",
    )

    # 分类汇总表索引
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_category_summary_phase_income_id",
        table_name="phase_income_category_summary",
        columns_sql="phase_income_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_phase_income_category_summary_category_code",
        table_name="phase_income_category_summary",
        columns_sql="category_code",
    )