<img width="1916" height="962" alt="image" src="https://github.com/user-attachments/assets/96ac2712-899a-49bb-a5bc-08bd1c78e931" />
<img width="1878" height="584" alt="image" src="https://github.com/user-attachments/assets/360e3120-1f84-4168-8768-f0bf87a25944" />

**Excalidraw Diagram Edit Link:** https://excalidraw.com/#json=HMkfTuPd4G65D9oFBzS0R,L6TzIHDZCIHpvSVEKXDKEg

---

# Pipeline for CSV: AI-Powered Transaction Processing Pipeline

This repository implements a production-grade, asynchronous financial transaction auditing and processing pipeline. It standardizes dirty transaction files, performs statistical anomaly scans, and enriches data categories and narratives using **DeepSeek AI**.

## 🛠️ System Architecture & Stack

- **API Layer:** FastAPI (running on port `8000`). Handles async uploads and polls job details.
- **Task Broker (Queue):** Redis (Port `6379`). Manages non-blocking message routing.
- **Worker Engine:** Celery. Pulls jobs, cleans CSV columns, flags outlier distributions, and coordinates LLM calls.
- **Database Layer:** PostgreSQL. Persists raw/cleaned records, AI classifications, and summaries.
- **LLM Engine:** DeepSeek Chat API (`deepseek-chat`) with exponential backoff retries.

---

## 🚀 Quick Start (Docker Compose)

The entire system starts up with a single command. 

### 1. Configure Credentials
Create a `.env` file in the root directory:
```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-chat
```

### 2. Start the Services
Run the following command to build and launch all containers:
```bash
docker compose up --build
```
This command spins up:
- **`transaction_api`** (FastAPI) at `http://localhost:8000`
- **`transaction_worker`** (Celery Task Worker)
- **`transaction_redis`** (Message Queue)
- **`transaction_db`** (PostgreSQL Database)

### 3. Open Web Dashboard
Once the containers are running, navigate to the web dashboard in your browser:
👉 **`http://localhost:8000/`**

You can drag and drop your `transactions.csv` directly into the Light Mode UI to visualize the step-by-step progress stepper!

---

## 📡 API Reference & Example cURL Requests

### 1. Ingest/Upload CSV Job
Uploads a raw transaction CSV, starts a pending job record, and returns the Job ID immediately.
```bash
curl -X POST "http://localhost:8000/jobs/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@transactions.csv"
```
**Example Response:**
```json
{
  "id": "4d3c0ce6-248f-46fe-8072-6326f2e06523",
  "filename": "transactions.csv",
  "status": "pending",
  "row_count_raw": null,
  "row_count_clean": null,
  "created_at": "2026-06-23T05:38:20.481",
  "completed_at": null,
  "error_message": null
}
```

### 2. Get Job Status
Returns current execution status (`pending`, `processing`, `completed`, or `failed`).
```bash
curl -X GET "http://localhost:8000/jobs/4d3c0ce6-248f-46fe-8072-6326f2e06523/status"
```

### 3. Get Job Results
Retrieves full cleaned lists, statistical outlier reasons, and the DeepSeek summary narrative.
```bash
curl -X GET "http://localhost:8000/jobs/4d3c0ce6-248f-46fe-8072-6326f2e06523/results"
```

### 4. List All Jobs
List historical tasks, with optional status filtering.
```bash
curl -X GET "http://localhost:8000/jobs?status=completed"
```

---

## 🧪 Running Unit Tests
To run the automated pytest test cases locally:
```bash
python3 -m pytest tests/
```
