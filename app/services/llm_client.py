import os
import json
import time
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Allowed categories for transaction classification
VALID_CATEGORIES = {
    "Food",
    "Shopping",
    "Travel",
    "Transport",
    "Utilities",
    "Cash Withdrawal",
    "Entertainment",
    "Other"
}

def simulate_classification(txns: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Simulation fallback when GEMINI_API_KEY is not provided.
    Performs deterministic rule-based classification mimicking an LLM.
    """
    logger.info("Running simulated transaction classification (No API key present)")
    mapping = {}
    for txn in txns:
        txn_id = str(txn.get("id"))
        merchant = str(txn.get("merchant", "")).lower()
        notes = str(txn.get("notes", "")).lower()
        
        category = "Other"
        if any(m in merchant for m in ["swiggy", "zomato"]):
            category = "Food"
        elif any(m in merchant for m in ["amazon", "flipkart", "myntra"]):
            category = "Shopping"
        elif any(m in merchant for m in ["irctc", "makemytrip", "easemytrip", "booking"]):
            category = "Travel"
        elif any(m in merchant for m in ["ola", "uber", "rapido"]):
            category = "Transport"
        elif any(m in merchant for m in ["jio", "recharge", "electricity", "bill"]):
            category = "Utilities"
        elif any(m in merchant for m in ["atm", "cash", "withdrawal", "hdfc atm"]):
            category = "Cash Withdrawal"
        elif any(m in merchant for m in ["bookmyshow", "netflix", "prime", "movie"]):
            category = "Entertainment"
            
        mapping[txn_id] = category
    return mapping

def simulate_narrative_summary(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulation fallback when GEMINI_API_KEY is not provided.
    Generates a realistic narrative and risk analysis based on batch metrics.
    """
    logger.info("Running simulated narrative summary (No API key present)")
    anomaly_count = metrics.get("anomaly_count", 0)
    total_txns = metrics.get("total_txns", 0)
    
    anomaly_ratio = anomaly_count / total_txns if total_txns > 0 else 0.0
    
    if anomaly_ratio > 0.15:
        risk_level = "high"
        risk_desc = f"An exceptionally high proportion ({anomaly_ratio:.1%}) of transactions are flagged as anomalous, indicating potential security risks or data integrity issues."
    elif anomaly_ratio > 0.05:
        risk_level = "medium"
        risk_desc = f"With {anomaly_count} anomalies detected ({anomaly_ratio:.1%}), some transactions deviate significantly from typical account behavior, showing medium risk."
    else:
        risk_level = "low"
        risk_desc = "The transaction patterns appear standard, and the statistical outliers represent low risk."

    top_merchants_list = metrics.get("top_merchants", [])
    top_merchants_str = ", ".join(m.get("merchant", "Unknown") for m in top_merchants_list[:3])
    
    narrative = (
        f"Total transaction volume reached {metrics.get('total_spend_inr', 0.0):.2f} INR and {metrics.get('total_spend_usd', 0.0):.2f} USD. "
        f"Major spending was recorded across key vendors, including {top_merchants_str or 'various merchants'}. "
        f"{risk_desc}"
    )

    return {
        "narrative": narrative,
        "risk_level": risk_level
    }

def call_deepseek_with_retry(prompt: str, api_key: str, max_retries: int = 3, initial_delay: float = 1.0) -> str:
    """
    Calls the DeepSeek API with exponential backoff on failure.
    """
    import httpx
    from app.config import settings
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Calling DeepSeek API (Attempt {attempt + 1}/{max_retries + 1})...")
            response = httpx.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            res_data = response.json()
            text = res_data["choices"][0]["message"]["content"].strip()
            if not text:
                raise ValueError("Received empty response text from DeepSeek API")
            return text
        except Exception as e:
            logger.warning(f"DeepSeek API call failed on attempt {attempt + 1}: {e}")
            if attempt == max_retries:
                logger.error(f"All {max_retries + 1} DeepSeek API attempts failed.")
                raise e
            time.sleep(delay)
            delay *= 2.0  # Exponential backoff

    raise RuntimeError("Unexpected end of retry loop")

def classify_transactions(txns: List[Dict[str, Any]], api_key: str | None) -> Dict[str, str]:
    """
    Classifies a batch of transactions using DeepSeek or fallback simulator.
    """
    if not txns:
        return {}

    if not api_key:
        return simulate_classification(txns)

    # Format simplified representations of transactions to save context tokens
    simplified_txns = []
    for t in txns:
        simplified_txns.append({
            "id": str(t["id"]),
            "merchant": t.get("merchant"),
            "amount": t.get("amount"),
            "currency": t.get("currency"),
            "notes": t.get("notes")
        })

    prompt = f"""You are a financial transaction classification engine.
Your task is to classify the provided transactions into one of these exact categories:
{', '.join(sorted(VALID_CATEGORIES))}

Input JSON list of transactions:
{json.dumps(simplified_txns, indent=2)}

You must return a strict JSON object where:
- Keys are the transaction "id" strings.
- Values are the matched category string (exactly one of the list above).

Return ONLY the JSON object. Do not include markdown codeblocks (like ```json), commentary, or extra spacing.
"""

    try:
        raw_response = call_deepseek_with_retry(prompt, api_key)
        
        # Clean markdown code blocks if the API returned them despite instructions
        clean_json = raw_response
        if clean_json.startswith("```"):
            lines = clean_json.split("\n")
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                clean_json = "\n".join(lines[1:-1])

        results = json.loads(clean_json)
        
        # Standardize and validate categories
        validated = {}
        for k, v in results.items():
            val = str(v).strip().title()
            if val not in VALID_CATEGORIES:
                val = "Other"
            validated[k] = val
        return validated

    except Exception as e:
        logger.error(f"LLM Classification failed: {e}. Fallback to simulator.")
        # Re-raise to let the retry task system handle marking this batch as llm_failed
        raise e

def generate_narrative(metrics: Dict[str, Any], api_key: str | None) -> Dict[str, Any]:
    """
    Generates a 2-3 sentence narrative and assigns a risk level using DeepSeek or fallback simulator.
    """
    if not api_key:
        return simulate_narrative_summary(metrics)

    prompt = f"""You are a senior risk and financial analyst.
Based on the following batch transaction statistics, generate a spending narrative and assess overall risk level:
- Total Transactions: {metrics['total_txns']}
- Total Spend in INR: {metrics['total_spend_inr']:.2f}
- Total Spend in USD: {metrics['total_spend_usd']:.2f}
- Top Merchants: {json.dumps(metrics['top_merchants'])}
- Flagged Anomalies: {metrics['anomaly_count']}

You must return a strict JSON object with these exact keys:
1. "narrative": A 2-3 sentence professional financial narrative summarizing spending trends, top merchants, and anomaly details.
2. "risk_level": A string, either "low", "medium", or "high" (assess based on the percentage and severity of flagged anomalies).

Return ONLY the JSON object. Do not include markdown formatting or commentary.
"""

    try:
        raw_response = call_deepseek_with_retry(prompt, api_key)
        
        clean_json = raw_response
        if clean_json.startswith("```"):
            lines = clean_json.split("\n")
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                clean_json = "\n".join(lines[1:-1])

        result = json.loads(clean_json)
        
        narrative = str(result.get("narrative", "")).strip()
        risk_level = str(result.get("risk_level", "low")).strip().lower()
        
        if risk_level not in ["low", "medium", "high"]:
            risk_level = "low"
            
        return {
            "narrative": narrative or "Narrative summary generation completed.",
            "risk_level": risk_level
        }
    except Exception as e:
        logger.error(f"LLM Narrative generation failed: {e}. Falling back to simulation.")
        # For narrative, since it's the final summary, we can gracefully fall back to simulation
        # so the job doesn't fail.
        return simulate_narrative_summary(metrics)
