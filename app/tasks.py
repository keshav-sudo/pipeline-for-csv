import logging
from datetime import datetime
from celery import Celery
from app.config import settings
from app.database import SessionLocal
from app.models import Job, Transaction, JobSummary
from app.services.data_cleaner import clean_csv_data
from app.services.anomaly_detector import detect_anomalies
from app.services.llm_client import classify_transactions, generate_narrative

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

@celery_app.task(name="app.tasks.process_transaction_job")
def process_transaction_job(job_id_str: str, csv_content: str) -> str:
    """
    Asynchronous task that runs the transaction ingestion and analysis pipeline.
    """
    logger.info(f"Starting Celery task for job {job_id_str}")
    db = SessionLocal()
    
    try:
        # Retrieve the Job
        job = db.query(Job).filter(Job.id == job_id_str).first()
        if not job:
            logger.error(f"Job {job_id_str} not found in database.")
            return f"Job {job_id_str} not found"

        # Update status to processing
        job.status = "processing"
        db.commit()

        # Step 1: Clean CSV data
        logger.info(f"Running Data Cleaning for Job {job_id_str}")
        cleaned_txns, raw_count, clean_count = clean_csv_data(csv_content)
        job.row_count_raw = raw_count
        job.row_count_clean = clean_count
        db.commit()

        # Step 2: Anomaly Detection
        logger.info(f"Running Anomaly Detection for Job {job_id_str}")
        cleaned_txns = detect_anomalies(cleaned_txns)

        # Step 3: LLM Classification
        # Find transactions without categories (they were filled with 'Uncategorised')
        uncategorised_txns = []
        for i, txn in enumerate(cleaned_txns):
            # If the CSV had blank category, it's cleaned as 'Uncategorised'
            if txn["category"] == "Uncategorised":
                # We need a temporary unique ID for mapping responses back from LLM
                txn_temp = txn.copy()
                txn_temp["id"] = f"temp_{i}"
                uncategorised_txns.append(txn_temp)

        llm_classifications = {}
        llm_failed = False
        
        if uncategorised_txns:
            logger.info(f"Found {len(uncategorised_txns)} uncategorised transactions. Requesting LLM classification.")
            try:
                # This has internal 3x retry with exponential backoff
                llm_classifications = classify_transactions(uncategorised_txns, settings.DEEPSEEK_API_KEY)
            except Exception as e:
                logger.error(f"LLM Classification completely failed after retries: {e}. Marking batch as llm_failed.")
                llm_failed = True
        
        # Create Transaction database models
        db_transactions = []
        anomaly_count = 0
        total_spend_inr = 0.0
        total_spend_usd = 0.0
        merchant_counts = {}

        for i, txn in enumerate(cleaned_txns):
            is_anomaly = txn["is_anomaly"]
            if is_anomaly:
                anomaly_count += 1

            amount = txn["amount"]
            currency = txn["currency"]
            
            # Spend calculations
            if currency == "INR":
                total_spend_inr += amount
            elif currency == "USD":
                total_spend_usd += amount

            # Merchant count tracking
            merchant = txn["merchant"]
            merchant_counts[merchant] = merchant_counts.get(merchant, 0) + 1

            # Map LLM category back
            llm_cat = None
            if txn["category"] == "Uncategorised" and not llm_failed:
                temp_id = f"temp_{i}"
                llm_cat = llm_classifications.get(temp_id)

            db_txn = Transaction(
                job_id=job.id,
                txn_id=txn["txn_id"],
                date=txn["date"],
                merchant=merchant,
                amount=amount,
                currency=currency,
                status=txn["status"],
                category=txn["category"],
                account_id=txn["account_id"],
                is_anomaly=is_anomaly,
                anomaly_reason=txn["anomaly_reason"],
                llm_category=llm_cat,
                llm_failed=llm_failed and (txn["category"] == "Uncategorised")
            )
            db_transactions.append(db_txn)

        # Save all transactions
        db.add_all(db_transactions)
        db.commit()

        # Step 4: LLM Narrative Summary
        # Compute Top 3 Merchants
        sorted_merchants = sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        top_merchants_json = [{"merchant": name, "count": count} for name, count in sorted_merchants]

        metrics = {
            "total_txns": len(cleaned_txns),
            "total_spend_inr": total_spend_inr,
            "total_spend_usd": total_spend_usd,
            "anomaly_count": anomaly_count,
            "top_merchants": top_merchants_json
        }

        logger.info(f"Generating LLM Narrative Summary for Job {job_id_str}")
        # narrative_summary returns { "narrative": str, "risk_level": str }
        summary_result = generate_narrative(metrics, settings.DEEPSEEK_API_KEY)

        # Save Job Summary
        job_summary = JobSummary(
            job_id=job.id,
            total_spend_inr=total_spend_inr,
            total_spend_usd=total_spend_usd,
            top_merchants=top_merchants_json,
            anomaly_count=anomaly_count,
            narrative=summary_result["narrative"],
            risk_level=summary_result["risk_level"]
        )
        db.add(job_summary)

        # Mark job as completed
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Job {job_id_str} processed successfully!")
        return f"Job {job_id_str} processed successfully"

    except Exception as e:
        logger.exception(f"Error processing job {job_id_str}: {e}")
        db.rollback()
        try:
            job = db.query(Job).filter(Job.id == job_id_str).first()
            if job:
                job.status = "failed"
                job.completed_at = datetime.utcnow()
                job.error_message = str(e)
                db.commit()
        except Exception as db_err:
            logger.error(f"Failed to save job failure status to database: {db_err}")
        return f"Job {job_id_str} failed: {str(e)}"
    finally:
        db.close()
