from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Any, Optional

class JobSummaryBase(BaseModel):
    total_spend_inr: float
    total_spend_usd: float
    top_merchants: List[Dict[str, Any]]
    anomaly_count: int
    narrative: str
    risk_level: str

    model_config = ConfigDict(from_attributes=True)

class JobSummaryResponse(JobSummaryBase):
    id: UUID
    job_id: UUID

class JobResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    row_count_raw: int
    row_count_clean: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class JobStatusResponse(JobResponse):
    summary: Optional[JobSummaryBase] = None

class TransactionResponse(BaseModel):
    id: UUID
    txn_id: Optional[str] = None
    date: Optional[str] = None
    merchant: str
    amount: float
    currency: str
    status: str
    category: str
    account_id: str
    is_anomaly: bool
    anomaly_reason: Optional[str] = None
    llm_category: Optional[str] = None
    llm_failed: bool

    model_config = ConfigDict(from_attributes=True)

class JobResultsResponse(BaseModel):
    job_id: UUID
    filename: str
    status: str
    summary: Optional[JobSummaryBase] = None
    transactions: List[TransactionResponse] = []
    anomalies: List[TransactionResponse] = []
    category_breakdown: Dict[str, Dict[str, float]] = {}

    model_config = ConfigDict(from_attributes=True)
