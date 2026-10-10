import csv
import io
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models import JobStatus, PayrollJob, PayrollRecord, RowError

REQUIRED_COLUMNS = [
    "employee_id",
    "name",
    "monthly_salary",
    "working_days",
    "present_days",
    "bonus",
]


def process_payroll(job_id: int, csv_content: str, payroll_month: str):
    db = SessionLocal()
    
    job = db.query(PayrollJob).filter(PayrollJob.id == job_id).first()
    if not job:
        db.close()
        return

    job.status = JobStatus.PROCESSING
    db.commit()

    reader = csv.DictReader(io.StringIO(csv_content))
    headers = reader.fieldnames or []

    for col in REQUIRED_COLUMNS:
        if col not in headers:
            job.status = JobStatus.FAILED
            job.error_summary = f"Missing required column: {col}"
            db.commit()
            db.close()
            return

    rows = list(reader)
    job.total_rows = len(rows)
    db.commit()

    success_count = 0
    failed_count = 0
    processed_count = 0

    for index, row in enumerate(rows, start=1):
        processed_count += 1
        
        try:
            for col in REQUIRED_COLUMNS:
                if not row.get(col) or not str(row[col]).strip():
                    raise ValueError(f"Missing value for {col}")

            emp_id = str(row["employee_id"]).strip()
            name = str(row["name"]).strip()
            monthly_salary = Decimal(row["monthly_salary"])
            working_days = int(row["working_days"])
            present_days = int(row["present_days"])
            bonus = Decimal(row["bonus"])

            if working_days <= 0:
                raise ValueError("Working days must be greater than zero.")
            if present_days < 0:
                raise ValueError("Present days cannot be negative.")
            if present_days > working_days:
                raise ValueError("Present days cannot exceed working days.")
            if monthly_salary < 0:
                raise ValueError("Monthly salary cannot be negative.")
            if bonus < 0:
                raise ValueError("Bonus cannot be negative.")

            base_salary = (monthly_salary * Decimal(present_days)) / Decimal(working_days)
            net_salary = (base_salary + bonus).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            record = PayrollRecord(
                job_id=job_id,
                employee_id=emp_id,
                name=name,
                monthly_salary=monthly_salary,
                working_days=working_days,
                present_days=present_days,
                bonus=bonus,
                net_salary=net_salary,
                payroll_month=payroll_month,
            )
            db.add(record)
            db.commit()
            success_count += 1

        except IntegrityError:
            db.rollback()
            failed_count += 1
            db.add(RowError(
                job_id=job_id,
                row_number=index,
                employee_id=row.get("employee_id"),
                error_message="Duplicate payroll record for employee in this payroll month.",
                raw_data=str(row),
            ))
            db.commit()

        except Exception as e:
            db.rollback()
            failed_count += 1
            db.add(RowError(
                job_id=job_id,
                row_number=index,
                employee_id=row.get("employee_id"),
                error_message=str(e),
                raw_data=str(row),
            ))
            db.commit()

        if processed_count % 50 == 0 or processed_count == job.total_rows:
            job.processed_rows = processed_count
            job.success_count = success_count
            job.failed_count = failed_count
            db.commit()

    if success_count == job.total_rows and job.total_rows > 0:
        job.status = JobStatus.COMPLETED
    elif success_count > 0:
        job.status = JobStatus.PARTIAL
    else:
        job.status = JobStatus.FAILED

    db.commit()
    db.close()