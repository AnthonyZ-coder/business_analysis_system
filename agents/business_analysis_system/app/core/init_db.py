from app.core.database import Base, engine

# 必须显式导入所有模型，确保 Base.metadata 能识别到表结构 
from app.models.file_record import FileRecord
from app.models.project_info import ProjectInfo
from app.models.contract_info import ContractInfo
from app.models.billing_record import BillingRecord

def init_db() -> None:
    """初始化数据库表 """
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")