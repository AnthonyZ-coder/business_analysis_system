from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text

from app.core.database import Base


class ProjectInfo(Base):
    __tablename__ = "project_info"

    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String(64), unique=True, nullable=False, index=True)
    project_name = Column(String(255), nullable=False)
    customer_name = Column(String(255), nullable=False)
    total_amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="CNY")

    source_type = Column(String(50), nullable=False, default="MANUAL")
    status = Column(String(50), nullable=False, default="RECEIVED")
    rule_status = Column(String(50), nullable=False, default="NOT_EVALUATED")
    rule_template_code = Column(String(100), nullable=True)
    next_step = Column(String(50), nullable=False, default="NONE")

    remarks = Column(Text, nullable=True)
    ext_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )