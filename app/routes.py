import io
import csv
import os
import logging
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Job, Transaction, JobSummary
from app.schemas import (
    JobResponse,
    JobStatusResponse,
    JobResultsResponse,
    TransactionResponse,
    JobSummaryBase
)
from app.tasks import process_transaction_job

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def get_index():
    """
    Serves the premium single-page web dashboard for uploading datasets,
    tracking ingestion tasks, and rendering DeepSeek results.
    """
    # Look for templates relative to the router's file location
    file_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard template index.html not found</h1>", status_code=404)


@router.post("/jobs/upload", response_model=JobResponse, status_code=201)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts a raw CSV file upload, validates structure, registers the job in the database,
    and enqueues the job processing task asynchronously to Redis/Celery.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV file uploads are supported.")
        
    try:
        contents = await file.read()
        csv_text = contents.decode("utf-8")
        
        # Fast validation of columns structure
        sniffer = csv.reader(io.StringIO(csv_text))
        headers = next(sniffer, None)
        if not headers:
            raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")
            
        required_fields = {"merchant", "amount", "currency", "status", "account_id"}
        headers_lower = {h.strip().lower() for h in headers if h}
        
        missing_fields = required_fields - headers_lower
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"CSV is missing required headers: {', '.join(missing_fields)}"
            )

        # Create Pending Job Record
        db_job = Job(
            filename=file.filename,
            status="pending"
        )
        db.add(db_job)
        db.commit()
        db.refresh(db_job)

        # Enqueue processing task asynchronously
        process_transaction_job.delay(str(db_job.id), csv_text)

        logger.info(f"Enqueued job {db_job.id} for file: {file.filename}")
        return db_job
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("Error during CSV upload validation")
        raise HTTPException(status_code=500, detail=f"Failed to ingest CSV: {str(e)}")


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the status of a specific job.
    Includes a high-level summary if the job is completed.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    response_data = {
        "id": job.id,
        "filename": job.filename,
        "status": job.status,
        "row_count_raw": job.row_count_raw,
        "row_count_clean": job.row_count_clean,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "error_message": job.error_message,
        "summary": None
    }

    if job.status == "completed" and job.summary:
        response_data["summary"] = JobSummaryBase(
            total_spend_inr=job.summary.total_spend_inr,
            total_spend_usd=job.summary.total_spend_usd,
            top_merchants=job.summary.top_merchants,
            anomaly_count=job.summary.anomaly_count,
            narrative=job.summary.narrative,
            risk_level=job.summary.risk_level
        )

    return response_data


@router.get("/jobs/{job_id}/results", response_model=JobResultsResponse)
def get_job_results(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the full structured output details for a completed job,
    including the cleaned transactions list, flagged anomalies, spending
    categorization breakdown, and the LLM-generated narrative summary.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    if job.status != "completed":
        return JobResultsResponse(
            job_id=job.id,
            filename=job.filename,
            status=job.status,
            summary=None,
            transactions=[],
            anomalies=[],
            category_breakdown={}
        )

    # Fetch transactions and anomalies
    transactions = db.query(Transaction).filter(Transaction.job_id == job.id).all()
    anomalies = [t for t in transactions if t.is_anomaly]

    # Calculate category spending breakdown per currency
    category_breakdown = {}
    for t in transactions:
        curr = t.currency.upper()
        # Fallback to llm_category if original category was Uncategorised
        cat = t.llm_category if (t.category == "Uncategorised" and t.llm_category) else t.category
        if not cat:
            cat = "Uncategorised"
            
        category_breakdown.setdefault(curr, {})
        category_breakdown[curr][cat] = round(category_breakdown[curr].get(cat, 0.0) + t.amount, 2)

    summary_data = None
    if job.summary:
        summary_data = JobSummaryBase(
            total_spend_inr=job.summary.total_spend_inr,
            total_spend_usd=job.summary.total_spend_usd,
            top_merchants=job.summary.top_merchants,
            anomaly_count=job.summary.anomaly_count,
            narrative=job.summary.narrative,
            risk_level=job.summary.risk_level
        )

    return JobResultsResponse(
        job_id=job.id,
        filename=job.filename,
        status=job.status,
        summary=summary_data,
        transactions=[TransactionResponse.model_validate(t) for t in transactions],
        anomalies=[TransactionResponse.model_validate(a) for a in anomalies],
        category_breakdown=category_breakdown
    )


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(
    status: Optional[str] = Query(None, description="Filter jobs by status (pending, processing, completed, failed)"),
    db: Session = Depends(get_db)
):
    """
    Lists all processed or queued jobs, sorted by creation timestamp descending.
    Supports filtering by status query parameters.
    """
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status.lower().strip())
    
    jobs = query.order_by(Job.created_at.desc()).all()
    return jobs
