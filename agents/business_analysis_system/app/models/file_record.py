from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text
from app.core.database import Base

class FileRecord(Base):
    """文件上传记录模型 """
    __tablename__ = "file_record"

    id = Column(Integer, primary_key=True, index=True)
    file_uuid = Column(String(64), unique=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # contract_pdf / billing_pdf [cite: 9]
    storage_path = Column(String(512), nullable=False)
    file_size = Column(Integer)
    file_hash = Column(String(64))
    mime_type = Column(String(100))
    uploader = Column(String(100))
    parse_status = Column(String(50), default="PENDING")
    
    ext_json = Column(Text, nullable=True)
    upload_time = Column(DateTime, default=datetime.utcnow)