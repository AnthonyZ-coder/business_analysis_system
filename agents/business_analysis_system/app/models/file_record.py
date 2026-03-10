from app.core.database import Base, engine

# 必须导入所有模型，确保 metadata 能识别到表
from app.models.file_record import FileRecord  # noqa: F401
from app.models.project_info import ProjectInfo  # noqa: F401
from app.models.contract_info import ContractInfo  # noqa: F401
from app.models.billing_record import BillingRecord  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")