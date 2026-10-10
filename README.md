Automated Payroll Processing System

FASTAPI application that can process monthly payroll for 50000 employees and validates rows and calculates salary for valid rows and provides a download api for downloading process valid rows.

Project structure:   
    app/main.py: handles API routing
    app/Payroll.py: processes the CSV file, validates rows, and calculates salaries
    app/models.py: defines the database tables (payroll_jobs, payroll_records,row_errors)
    app/database.py: connects to the local SQLite database "payroll.db"
    payroll.db: sqllite db file

How to Run:
    python -m venv .venv
    # Windows PowerShell:
    .venv\Scripts\Activate.ps1
    # Mac / Linux:
    source .venv/bin/activate

    After activating:
        pip -r install requirements.txt 
    
    Start the server:
        uvicorn app.main:app --reload

Open http://127.0.0.1:8001/docs in your browser to test everything using Swagger UI.

API endpoints:

    @app.post("/payroll/upload", status_code=status.HTTP_202_ACCEPTED)
    Uploads your CSV file and payroll_month (example: 2025-05)
    It returns a job_id with an HTTP 202 accepted status while running jobs in background.

    @app.get("/payroll/jobs/{job_id}")
    Check the current progress and status of your upload (PENDING, PROCESSING, COMPLETED, PARTIAL, FAILED).

    @app.get("/payroll/jobs/{job_id}/results")
    Views a json list of all successfully calculated rows and any row errors.

    @app.get("/payroll/jobs/{job_id}/download")
    Downloads the final successful payroll calculations in a CSV file. [PARTIAL/COMPLETED]

DATABASE Schema:

JobStatus : PENDING ,PROCESSING ,COMPLETED ,PARTIAL ,FAILED

Table Name: payroll_jobs
    - id
    - payroll_month
    - status
    - total_rows
    - processed_rows
    - success_count
    - failed_count
    - error_summary
    - created_at
    - updated_at

Table Name: payroll_records (Unique Constraint: employee_id, payroll_month)
    - id
    - job_id
    - employee_id
    - name
    - monthly_salary
    - working_days
    - present_days
    - bonus
    - net_salary
    - payroll_month

Table Name: row_errors
    - id
    - job_id
    - row_number
    - employee_id
    - error_message
    - raw_data


Sample CSV:
    employee_id,name,monthly_salary,working_days,present_days,bonus
    E101,Rahul,60000,22,20,5000 
    E102,Priya,80000,26,52,10000 
    E103,Amit,45000,22,11,2000 
    E104,Neha,70000,22,32,3000 

Sample Request/Reponses:
    A. Sample POST Request on /payroll/upload

        Field 1: payroll_month = 2025-05
        Field 2: file = payroll.csv

        RESPONSE:
        {
            "job_id": 2,
            "status": "PENDING",
            "message": "Payroll upload accepted and queued for background processing."
        }

    B. Failed Job status
        GET /payroll/jobs/{job_id}
            parameter (job_id) : 2

        RESPONSE:
            {
            "status": "FAILED",
            "total_rows": 4,
            "error_summary": null,
            "updated_at": "2026-10-10T07:08:18.785609",
            "processed_rows": 4,
            "payroll_month": "2025-05",
            "id": 2,
            "success_count": 0,
            "failed_count": 4,
            "created_at": "2026-10-10T07:08:18.610728"
            }
    C. Job Results 
        GET /payroll/jobs/{job_id}/results
            parameter (job_id) : "490d8a2b-bfce-4436-a242-dc2a56eaaac0"
                
        RESPONSE:
            {
            "job_id": 1,
            "status": "COMPLETED",
            "successful_records": [
                {
                "employee_id": "E101",
                "name": "Rahul",
                "monthly_salary": 60000,
                "working_days": 22,
                "present_days": 20,
                "bonus": 5000,
                "net_salary": 59545.45
                },
                {
                "employee_id": "E102",
                "name": "Priya",
                "monthly_salary": 80000,
                "working_days": 22,
                "present_days": 22,
                "bonus": 10000,
                "net_salary": 90000
                },
                {
                "employee_id": "E103",
                "name": "Amit",
                "monthly_salary": 45000,
                "working_days": 22,
                "present_days": 18,
                "bonus": 2000,
                "net_salary": 38818.18
                },
                {
                "employee_id": "E104",
                "name": "Neha",
                "monthly_salary": 70000,
                "working_days": 22,
                "present_days": 21,
                "bonus": 3000,
                "net_salary": 69818.18
                }
            ],
            "row_errors": []
            }