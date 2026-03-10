from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class FileRecord(Base):
    __tablename__ = "file_record"

    id = Column(Integer, primary_key=True, index=True)
    file_uuid = Column(String(64), unique=True, nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False, index=True)
    storage_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(128), nullable=False, index=True)
    mime_type = Column(String(100), nullable=True)
    upload_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    uploader = Column(String(100), nullable=True)
    parse_status = Column(String(50), nullable=False, default="PENDING")
    ext_json = Column(Text, nullable=True)