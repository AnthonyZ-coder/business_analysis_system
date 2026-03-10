from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CONTRACT_UPLOAD_DIR = UPLOAD_DIR / "contracts"
BILLING_UPLOAD_DIR = UPLOAD_DIR / "billings"
SQLITE_DIR = DATA_DIR / "sqlite"
DB_PATH = SQLITE_DIR / "ba_system.db"

# 自动创建目录 [cite: 11]
for path in [DATA_DIR, UPLOAD_DIR, CONTRACT_UPLOAD_DIR, BILLING_UPLOAD_DIR, SQLITE_DIR]:
    path.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

APP_NAME = "Business Analysis System"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "MVP for business analysis intelligent agent"

# 25个产品线定义 (根据 PRD 整理 )
PRODUCT_LINES = [
    "基座", "分布式", "计算", "存储", "AI原生存储", 
    "对象存储", "网络", "PAAS平台", "低代码平台", "AI应用开发平台", 
    "微服务", "容器服务", "中间件", "数据库", "数据工程平台", 
    "星罗先进算力调度平台-AICC", "星罗先进算力调度平台-AICP", "AI边缘一体机", 
    "可观测平台", "云桌面", "云视频", "安全", "CUOS", 
    "私有云云管平台", "云迁移服务"
]