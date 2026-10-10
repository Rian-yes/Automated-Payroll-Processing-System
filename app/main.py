import csv
import io
from datetime import datetime
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import JobStatus, PayrollJob, PayrollRecord, RowError
from app.Payroll import process_payroll

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Automated Payroll Processing System", version="1.0.0")


@app.post("/payroll/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_payroll(
    background_tasks: BackgroundTasks,
    payroll_month: str = Form(...,description="YYYY-MM"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        datetime.strptime(payroll_month, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payroll_month format. Use YYYY-MM.")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    content = await file.read()
    csv_str = content.decode("utf-8")

    job = PayrollJob(payroll_month=payroll_month, status=JobStatus.PENDING)
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(process_payroll, job.id, csv_str, payroll_month)

    return {
        "job_id": job.id,
        "status": JobStatus.PENDING,
        "message": "Payroll upload accepted and queued for background processing."
    }


@app.get("/payroll/jobs/{job_id}")
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(PayrollJob).filter(PayrollJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/payroll/jobs/{job_id}/results")
def get_job_results(job_id: int, db: Session = Depends(get_db)):
    job = db.query(PayrollJob).filter(PayrollJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    records = db.query(PayrollRecord).filter(PayrollRecord.job_id == job_id).all()
    errors = db.query(RowError).filter(RowError.job_id == job_id).all()

    return {
        "job_id": job.id,
        "status": job.status,
        "successful_records": [
            {
                "employee_id": r.employee_id,
                "name": r.name,
                "monthly_salary": r.monthly_salary,
                "working_days": r.working_days,
                "present_days": r.present_days,
                "bonus": r.bonus,
                "net_salary": r.net_salary
            } for r in records
        ],
        "row_errors": [
            {
                "row_number": e.row_number,
                "employee_id": e.employee_id,
                "error_message": e.error_message,
                "raw_data": e.raw_data
            } for e in errors
        ]
    }


@app.get("/payroll/jobs/{job_id}/download")
def download_payroll_results(job_id: int, db: Session = Depends(get_db)):
    job = db.query(PayrollJob).filter(PayrollJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status not in [JobStatus.COMPLETED, JobStatus.PARTIAL]:
        raise HTTPException(
            status_code=400, 
            detail=f"Results are not ready yet. Current status: {job.status.value}"
        )

    records = db.query(PayrollRecord).filter(PayrollRecord.job_id == job_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "employee_id", "name", "monthly_salary", "working_days", 
        "present_days", "bonus", "net_salary", "payroll_month"
    ])
    
    for r in records:
        writer.writerow([
            r.employee_id, r.name, r.monthly_salary, r.working_days, 
            r.present_days, r.bonus, r.net_salary, r.payroll_month
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=processed_payroll_{job_id}.csv"}
    )