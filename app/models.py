import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from app.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class PayrollJob(Base):
    __tablename__ = "payroll_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    payroll_month = Column(String(7), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    total_rows = Column(Integer, default=0, nullable=False)
    processed_rows = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    error_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class PayrollRecord(Base):
    __tablename__ = "payroll_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False, index=True)
    employee_id = Column(String(12), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    monthly_salary = Column(Numeric(12, 2), nullable=False)
    working_days = Column(Integer, nullable=False)
    present_days = Column(Integer, nullable=False)
    bonus = Column(Numeric(12, 2), nullable=False)
    net_salary = Column(Numeric(12, 2), nullable=False)
    payroll_month = Column(String(7), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "employee_id", "payroll_month", name="unique_employee_payroll_month"
        ),
    )


class RowError(Base):
    __tablename__ = "row_errors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    employee_id = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=False)
    raw_data = Column(Text, nullable=True)