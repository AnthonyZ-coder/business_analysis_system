from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.core.database import Base


class ContractInfo(Base):
    __tablename__ = "contract_info"

    id = Column(Integer, primary_key=True, index=True)
    contract_code = Column(String(64), unique=True, nullable=False, index=True)
    contract_name = Column(String(255), nullable=False)
    project_code = Column(String(64), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    contract_amount = Column(Numeric(18, 2), nullable=False)
    tax_included = Column(Boolean, nullable=False, default=True)
    sign_date = Column(Date, nullable=True)

    file_record_id = Column(Integer, ForeignKey("file_record.id"), nullable=True)
    parse_status = Column(String(50), nullable=False, default="PENDING")

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