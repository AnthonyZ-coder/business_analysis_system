import sqlite3

from app.db.schema.helpers import create_index_if_not_exists, execute_sql_list


PRODUCT_SPLIT_TABLE_SQL = [
    """
    CREATE TABLE IF NOT EXISTS product_line_category (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_code VARCHAR(64) NOT NULL UNIQUE,
        category_name VARCHAR(128) NOT NULL,
        category_desc TEXT,
        sort_order INTEGER DEFAULT 0,
        status VARCHAR(32) DEFAULT 'ENABLED',
        version_no VARCHAR(32) DEFAULT 'v0.1',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(64),
        updated_by VARCHAR(64),
        remarks TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS product_line_definition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_code VARCHAR(64) NOT NULL UNIQUE,
        product_name VARCHAR(128) NOT NULL,
        category_code VARCHAR(64) NOT NULL,
        definition TEXT,
        keywords TEXT,
        scope_included TEXT,
        scope_excluded TEXT,
        confusion_note TEXT,
        sort_order INTEGER DEFAULT 0,
        status VARCHAR(32) DEFAULT 'ENABLED',
        version_no VARCHAR(32) DEFAULT 'v0.1',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(64),
        updated_by VARCHAR(64),
        remarks TEXT,
        FOREIGN KEY (category_code) REFERENCES product_line_category(category_code)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS product_split_suggestion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        suggestion_code VARCHAR(64) NOT NULL UNIQUE,
        project_code VARCHAR(64) NOT NULL,
        contract_id INTEGER,
        contract_code VARCHAR(64),
        suggestion_name VARCHAR(255) NOT NULL,
        source_type VARCHAR(32) NOT NULL,
        source_model VARCHAR(128),
        llm_enabled_flag INTEGER DEFAULT 1,
        category_split_json TEXT,
        evidence_summary TEXT,
        reference_case_ids TEXT,
        matrix_applied_flag INTEGER DEFAULT 0,
        review_status VARCHAR(32) DEFAULT 'GENERATED',
        reviewer VARCHAR(64),
        reviewed_at DATETIME,
        status VARCHAR(32) DEFAULT 'ENABLED',
        version_no VARCHAR(32) DEFAULT 'v0.1',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(64),
        updated_by VARCHAR(64),
        remarks TEXT,
        FOREIGN KEY (contract_id) REFERENCES contract_info(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS product_split_suggestion_detail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        suggestion_id INTEGER NOT NULL,
        product_code VARCHAR(64) NOT NULL,
        product_name VARCHAR(128) NOT NULL,
        category_code VARCHAR(64) NOT NULL,
        split_ratio DECIMAL(10,6) NOT NULL,
        confidence_score DECIMAL(10,6),
        source_type VARCHAR(32) NOT NULL,
        evidence_text TEXT,
        evidence_page_info VARCHAR(255),
        matrix_weight DECIMAL(10,6),
        sort_order INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        remarks TEXT,
        FOREIGN KEY (suggestion_id) REFERENCES product_split_suggestion(id),
        FOREIGN KEY (product_code) REFERENCES product_line_definition(product_code),
        FOREIGN KEY (category_code) REFERENCES product_line_category(category_code)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS product_split_rule_draft (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draft_code VARCHAR(64) NOT NULL UNIQUE,
        project_code VARCHAR(64) NOT NULL,
        contract_id INTEGER,
        contract_code VARCHAR(64),
        draft_name VARCHAR(255) NOT NULL,
        draft_source_type VARCHAR(32) NOT NULL,
        llm_enabled_flag INTEGER DEFAULT 1,
        from_suggestion_id INTEGER,
        category_split_json TEXT,
        edit_status VARCHAR(32) DEFAULT 'DRAFT',
        review_status VARCHAR(32) DEFAULT 'DRAFT',
        reviewer VARCHAR(64),
        reviewed_at DATETIME,
        status VARCHAR(32) DEFAULT 'ENABLED',
        version_no VARCHAR(32) DEFAULT 'v0.1',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(64),
        updated_by VARCHAR(64),
        remarks TEXT,
        FOREIGN KEY (contract_id) REFERENCES contract_info(id),
        FOREIGN KEY (from_suggestion_id) REFERENCES product_split_suggestion(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS product_split_rule_draft_detail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draft_id INTEGER NOT NULL,
        product_code VARCHAR(64) NOT NULL,
        product_name VARCHAR(128) NOT NULL,
        category_code VARCHAR(64) NOT NULL,
        split_ratio DECIMAL(10,6) NOT NULL,
        source_type VARCHAR(32) NOT NULL,
        based_suggestion_detail_id INTEGER,
        adjust_reason TEXT,
        sort_order INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        remarks TEXT,
        FOREIGN KEY (draft_id) REFERENCES product_split_rule_draft(id),
        FOREIGN KEY (based_suggestion_detail_id) REFERENCES product_split_suggestion_detail(id),
        FOREIGN KEY (product_code) REFERENCES product_line_definition(product_code),
        FOREIGN KEY (category_code) REFERENCES product_line_category(category_code)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS product_split_rule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_code VARCHAR(64) NOT NULL UNIQUE,
        rule_name VARCHAR(255) NOT NULL,
        rule_type VARCHAR(32) NOT NULL,
        project_type_tag VARCHAR(128),
        applicable_scope TEXT,
        category_split_json TEXT,
        source_draft_id INTEGER NOT NULL,
        review_status VARCHAR(32) DEFAULT 'APPROVED',
        reviewer VARCHAR(64),
        reviewed_at DATETIME,
        is_default INTEGER DEFAULT 0,
        status VARCHAR(32) DEFAULT 'ENABLED',
        version_no VARCHAR(32) DEFAULT 'v0.1',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(64),
        updated_by VARCHAR(64),
        remarks TEXT,
        FOREIGN KEY (source_draft_id) REFERENCES product_split_rule_draft(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS product_split_rule_detail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id INTEGER NOT NULL,
        product_code VARCHAR(64) NOT NULL,
        product_name VARCHAR(128) NOT NULL,
        category_code VARCHAR(64) NOT NULL,
        split_ratio DECIMAL(10,6) NOT NULL,
        source_type VARCHAR(32) NOT NULL,
        based_draft_detail_id INTEGER,
        sort_order INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        remarks TEXT,
        FOREIGN KEY (rule_id) REFERENCES product_split_rule(id),
        FOREIGN KEY (based_draft_detail_id) REFERENCES product_split_rule_draft_detail(id),
        FOREIGN KEY (product_code) REFERENCES product_line_definition(product_code),
        FOREIGN KEY (category_code) REFERENCES product_line_category(category_code)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS project_split_rule_binding (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_code VARCHAR(64) NOT NULL,
        contract_id INTEGER,
        contract_code VARCHAR(64),
        rule_id INTEGER NOT NULL,
        binding_status VARCHAR(32) DEFAULT 'ACTIVE',
        selected_by VARCHAR(64),
        selected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        effective_from DATETIME,
        effective_to DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        remarks TEXT,
        FOREIGN KEY (rule_id) REFERENCES product_split_rule(id),
        FOREIGN KEY (contract_id) REFERENCES contract_info(id)
    );
    """,
]


def init_product_split_schema(conn: sqlite3.Connection) -> None:
    execute_sql_list(conn, PRODUCT_SPLIT_TABLE_SQL)

    # 基础字典表索引
    create_index_if_not_exists(
        conn,
        index_name="idx_product_line_category_code",
        table_name="product_line_category",
        columns_sql="category_code",
        unique=True,
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_line_definition_code",
        table_name="product_line_definition",
        columns_sql="product_code",
        unique=True,
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_line_definition_category",
        table_name="product_line_definition",
        columns_sql="category_code",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_line_definition_status",
        table_name="product_line_definition",
        columns_sql="status",
    )

    # suggestion 层索引
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_suggestion_project_code",
        table_name="product_split_suggestion",
        columns_sql="project_code",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_suggestion_contract_id",
        table_name="product_split_suggestion",
        columns_sql="contract_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_suggestion_review_status",
        table_name="product_split_suggestion",
        columns_sql="review_status",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_suggestion_detail_suggestion_id",
        table_name="product_split_suggestion_detail",
        columns_sql="suggestion_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_suggestion_detail_product_code",
        table_name="product_split_suggestion_detail",
        columns_sql="product_code",
    )

    # draft 层索引
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_draft_project_code",
        table_name="product_split_rule_draft",
        columns_sql="project_code",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_draft_contract_id",
        table_name="product_split_rule_draft",
        columns_sql="contract_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_draft_from_suggestion_id",
        table_name="product_split_rule_draft",
        columns_sql="from_suggestion_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_draft_edit_status",
        table_name="product_split_rule_draft",
        columns_sql="edit_status",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_draft_review_status",
        table_name="product_split_rule_draft",
        columns_sql="review_status",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_draft_detail_draft_id",
        table_name="product_split_rule_draft_detail",
        columns_sql="draft_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_draft_detail_product_code",
        table_name="product_split_rule_draft_detail",
        columns_sql="product_code",
    )

    # rule 层索引
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_code",
        table_name="product_split_rule",
        columns_sql="rule_code",
        unique=True,
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_source_draft_id",
        table_name="product_split_rule",
        columns_sql="source_draft_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_status",
        table_name="product_split_rule",
        columns_sql="status",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_project_type_tag",
        table_name="product_split_rule",
        columns_sql="project_type_tag",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_detail_rule_id",
        table_name="product_split_rule_detail",
        columns_sql="rule_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_product_split_rule_detail_product_code",
        table_name="product_split_rule_detail",
        columns_sql="product_code",
    )

    # binding 层索引
    create_index_if_not_exists(
        conn,
        index_name="idx_project_split_rule_binding_project_code",
        table_name="project_split_rule_binding",
        columns_sql="project_code",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_project_split_rule_binding_contract_id",
        table_name="project_split_rule_binding",
        columns_sql="contract_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_project_split_rule_binding_rule_id",
        table_name="project_split_rule_binding",
        columns_sql="rule_id",
    )
    create_index_if_not_exists(
        conn,
        index_name="idx_project_split_rule_binding_status",
        table_name="project_split_rule_binding",
        columns_sql="binding_status",
    )