import io
import re
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Tuple

def parse_date(date_str: Any) -> str | None:
    if pd.isna(date_str) or not str(date_str).strip():
        return None
    date_str = str(date_str).strip()
    
    # Supported formats
    formats = [
        "%d-%m-%Y",  # e.g., 04-09-2024
        "%Y/%m/%d",  # e.g., 2024/02/05
        "%Y-%m-%d",  # e.g., 2024-07-15
        "%d/%m/%Y",  # e.g., 04/09/2024
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    # Fallback to pandas parser
    try:
        return pd.to_datetime(date_str).strftime("%Y-%m-%d")
    except Exception:
        return date_str

def clean_amount(amount_val: Any) -> float:
    if pd.isna(amount_val):
        return 0.0
    val_str = str(amount_val).strip()
    # Remove currency symbols ($ or others) and keep digits, dots, and minus signs
    cleaned = re.sub(r"[^\d\.\-]", "", val_str)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def clean_csv_data(csv_content: str) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Cleans raw CSV content.
    Returns:
        - List of cleaned transaction dicts
        - Raw row count
        - Cleaned row count
    """
    # Read CSV
    df = pd.read_csv(io.StringIO(csv_content))
    raw_row_count = len(df)

    # 1. Remove exact duplicate rows
    df = df.drop_duplicates(keep="first")
    
    # Fill NaN values with empty string or None for parsing
    df = df.where(pd.notnull(df), None)

    cleaned_transactions = []
    for _, row in df.iterrows():
        # Strip txn_id or set to None if blank
        txn_id = str(row["txn_id"]).strip() if row.get("txn_id") else None
        if txn_id == "None" or not txn_id:
            txn_id = None

        # Clean Date
        date_raw = row.get("date")
        date_clean = parse_date(date_raw)

        # Clean Merchant
        merchant = str(row.get("merchant", "Unknown")).strip() or "Unknown"

        # Clean Amount
        amount_raw = row.get("amount")
        amount_clean = clean_amount(amount_raw)

        # Clean Currency
        currency_raw = row.get("currency")
        currency_clean = str(currency_raw).strip().upper() if currency_raw else "INR"

        # Clean Status
        status_raw = row.get("status")
        status_clean = str(status_raw).strip().upper() if status_raw else "PENDING"

        # Clean Category
        category_raw = row.get("category")
        if not category_raw or pd.isna(category_raw) or str(category_raw).strip() == "":
            category_clean = "Uncategorised"
        else:
            category_clean = str(category_raw).strip()

        # Account ID
        account_id = str(row.get("account_id", "Unknown")).strip() or "Unknown"

        # Notes
        notes = str(row.get("notes", "")).strip() if row.get("notes") else ""

        cleaned_transactions.append({
            "txn_id": txn_id,
            "date": date_clean,
            "merchant": merchant,
            "amount": amount_clean,
            "currency": currency_clean,
            "status": status_clean,
            "category": category_clean,
            "account_id": account_id,
            "notes": notes
        })

    cleaned_row_count = len(cleaned_transactions)
    return cleaned_transactions, raw_row_count, cleaned_row_count
