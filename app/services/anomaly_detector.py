import statistics
from typing import List, Dict, Any

def detect_anomalies(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detects statistical outliers and currency-merchant mismatches in the transaction list.
    Updates each transaction in place by adding:
        - is_anomaly (bool)
        - anomaly_reason (str | None)
    """
    # 1. Group transaction amounts by account_id to calculate medians
    account_amounts = {}
    for txn in transactions:
        acc_id = txn["account_id"]
        if acc_id:
            account_amounts.setdefault(acc_id, []).append(txn["amount"])

    # Calculate median for each account
    account_medians = {}
    for acc_id, amounts in account_amounts.items():
        if amounts:
            account_medians[acc_id] = statistics.median(amounts)
        else:
            account_medians[acc_id] = 0.0

    # 2. Flag anomalies
    domestic_brands = {"swiggy", "ola", "irctc"}

    for txn in transactions:
        reasons = []
        acc_id = txn["account_id"]
        amount = txn["amount"]
        currency = txn["currency"]
        merchant = txn["merchant"]

        # Rule 1: Outlier check (amount > 3 * median of the account)
        median = account_medians.get(acc_id, 0.0)
        if median > 0.0 and amount > 3.0 * median:
            reasons.append(f"Statistical outlier: Amount {amount} exceeds 3x the account's median ({median:.2f})")

        # Rule 2: Domestic brand with USD currency
        if currency.upper() == "USD" and merchant.lower() in domestic_brands:
            reasons.append(f"Domestic merchant brand '{merchant}' charged in USD")

        # Set anomaly attributes
        if reasons:
            txn["is_anomaly"] = True
            txn["anomaly_reason"] = "; ".join(reasons)
        else:
            txn["is_anomaly"] = False
            txn["anomaly_reason"] = None

    return transactions
