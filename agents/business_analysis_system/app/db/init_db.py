import sqlite3

from app.core.config import DB_PATH

# 后面逐步补齐这些文件
try:
    from app.db.schema.base_schema import init_base_schema
except ImportError:
    def init_base_schema(conn: sqlite3.Connection) -> None:
        pass


try:
    from app.db.schema.contract_parsing_schema import init_contract_parsing_schema
except ImportError:
    def init_contract_parsing_schema(conn: sqlite3.Connection) -> None:
        pass


try:
    from app.db.schema.product_split_schema import init_product_split_schema
except ImportError:
    def init_product_split_schema(conn: sqlite3.Connection) -> None:
        pass


try:
    from app.db.schema.phase_income_schema import init_phase_income_schema
except ImportError:
    def init_phase_income_schema(conn: sqlite3.Connection) -> None:
        pass


try:
    from app.db.schema.result_storage_schema import init_result_storage_schema
except ImportError:
    def init_result_storage_schema(conn: sqlite3.Connection) -> None:
        pass


def init_db() -> None:
    conn = sqlite3.connect(str(DB_PATH))
    try:
        init_base_schema(conn)
        init_contract_parsing_schema(conn)
        init_product_split_schema(conn)
        init_phase_income_schema(conn)
        init_result_storage_schema(conn)

        conn.commit()
        print("Database schema initialized successfully.")
    except Exception as exc:
        conn.rollback()
        print(f"Database schema initialization failed: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()