import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.services.data_cleaner import parse_date, clean_amount, clean_csv_data
from app.services.anomaly_detector import detect_anomalies
from app.services.llm_client import simulate_classification, simulate_narrative_summary

# 1. Test Data Cleaning Service
def test_parse_date():
    assert parse_date("04-09-2024") == "2024-09-04"
    assert parse_date("2024/02/05") == "2024-02-05"
    assert parse_date("2024-07-15") == "2024-07-15"
    assert parse_date("  11/03/2024  ") == "2024-03-11"
    assert parse_date(None) is None
    assert parse_date("") is None

def test_clean_amount():
    assert clean_amount("123.45") == 123.45
    assert clean_amount("$11325.79") == 11325.79
    assert clean_amount("   $150.00   ") == 150.00
    assert clean_amount(None) == 0.0
    assert clean_amount("abc") == 0.0

def test_clean_csv_data():
    raw_csv = """txn_id,date,merchant,amount,currency,status,category,account_id,notes
TXN1021,17-02-2024,Zomato,2536.35,USD,SUCCESS,Food,ACC001,Verified
TXN1021,17-02-2024,Zomato,2536.35,USD,SUCCESS,Food,ACC001,Verified
TXN1000,23-11-2024,Amazon,423.91,INR,failed,,ACC004,
"""
    cleaned, raw_count, clean_count = clean_csv_data(raw_csv)
    # Check that exact duplicate (TXN1021) was removed
    assert raw_count == 3
    assert clean_count == 2
    assert cleaned[0]["merchant"] == "Zomato"
    assert cleaned[1]["category"] == "Uncategorised"  # Blank category filled with 'Uncategorised'
    assert cleaned[1]["status"] == "FAILED"  # Casing normalized to uppercase

# 2. Test Anomaly Detection Service
def test_detect_anomalies():
    transactions = [
        # ACC001 transactions: amounts 10, 12, 11, 15, 100 (100 is outlier)
        {"account_id": "ACC001", "amount": 10.0, "currency": "INR", "merchant": "MerchantA"},
        {"account_id": "ACC001", "amount": 12.0, "currency": "INR", "merchant": "MerchantA"},
        {"account_id": "ACC001", "amount": 11.0, "currency": "INR", "merchant": "MerchantA"},
        {"account_id": "ACC001", "amount": 15.0, "currency": "INR", "merchant": "MerchantA"},
        {"account_id": "ACC001", "amount": 100.0, "currency": "INR", "merchant": "MerchantA"},  # Outlier! Median is ~12, 3x is 36. 100 > 36
        # USD + domestic brand anomalies
        {"account_id": "ACC002", "amount": 20.0, "currency": "USD", "merchant": "Swiggy"},  # Mismatch!
        {"account_id": "ACC002", "amount": 30.0, "currency": "INR", "merchant": "Swiggy"},  # OK
        {"account_id": "ACC002", "amount": 40.0, "currency": "USD", "merchant": "Amazon"},  # OK
    ]
    
    results = detect_anomalies(transactions)
    
    # Check outlier
    outlier_txn = [t for t in results if t["amount"] == 100.0][0]
    assert outlier_txn["is_anomaly"] is True
    assert "Statistical outlier" in outlier_txn["anomaly_reason"]

    # Check USD domestic mismatch
    usd_swiggy = [t for t in results if t["merchant"] == "Swiggy" and t["currency"] == "USD"][0]
    assert usd_swiggy["is_anomaly"] is True
    assert "charged in USD" in usd_swiggy["anomaly_reason"]

    # Check non-anomalies
    ok_swiggy = [t for t in results if t["merchant"] == "Swiggy" and t["currency"] == "INR"][0]
    assert ok_swiggy["is_anomaly"] is False

# 3. Test LLM Simulation Fallbacks
def test_simulate_classification():
    txns = [
        {"id": "t1", "merchant": "Swiggy", "notes": ""},
        {"id": "t2", "merchant": "Amazon", "notes": ""},
        {"id": "t3", "merchant": "HDFC ATM", "notes": ""},
    ]
    mapping = simulate_classification(txns)
    assert mapping["t1"] == "Food"
    assert mapping["t2"] == "Shopping"
    assert mapping["t3"] == "Cash Withdrawal"

def test_simulate_narrative_summary():
    metrics = {
        "total_txns": 10,
        "anomaly_count": 2,  # 20% anomaly ratio -> high risk
        "total_spend_inr": 150000.0,
        "total_spend_usd": 120.0,
        "top_merchants": [{"merchant": "Flipkart", "count": 4}]
    }
    summary = simulate_narrative_summary(metrics)
    assert summary["risk_level"] == "high"
    assert "Flipkart" in summary["narrative"]
    assert "high proportion" in summary["narrative"]

# 4. Test API Router Endpoints
# Configure in-memory SQLite database for router testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def test_upload_endpoint_validation():
    # Test upload with invalid file extension
    response = client.post("/jobs/upload", files={"file": ("test.txt", b"some data", "text/plain")})
    assert response.status_code == 400
    assert "Only CSV file uploads" in response.json()["detail"]

    # Test upload with empty CSV file
    response = client.post("/jobs/upload", files={"file": ("test.csv", b"", "text/csv")})
    assert response.status_code == 400
    assert "CSV file is empty" in response.json()["detail"]

    # Test upload with missing required fields
    invalid_csv = b"txn_id,date,merchant,amount,currency\nTXN1021,17-02-2024,Zomato,2536.35,USD\n"
    response = client.post("/jobs/upload", files={"file": ("test.csv", invalid_csv, "text/csv")})
    assert response.status_code == 400
    assert "missing required headers" in response.json()["detail"]
