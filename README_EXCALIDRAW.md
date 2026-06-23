# 🎨 Excalidraw System Architecture & ERD Drawing Guide

Hey! Agar aap is project (**AI-Powered Transaction Processing Pipeline**) ka ek awesome, premium, aur clear architecture diagram **Excalidraw** pe banana chahte hain, toh ye guide aapke liye perfect blueprint hai. 

Is guide ko follow karke aap ek professional-grade visual diagram draw kar payenge jise aap senior developers ya tech-leads ke samne review ke liye present kar sakte hain.

---

## 🎨 Theme & Styling System (Aesthetics)
Excalidraw me design ko visually premium banane ke liye, random colors aur shapes ki jagah ek **structured styling system** use karein:

### 1. Color Palette (Harmonious & Professional)
Har layer aur component ke liye specialized colors choose karein:

| Layer / Component | Background Color (Hex) | Stroke/Text Color | Styling Tip |
| :--- | :--- | :--- | :--- |
| **Client / User Interface** | `#F8FAFC` (Light Grey) | `#475569` (Slate) | Use a simple screen/laptop container |
| **API Layer (FastAPI)** | `#E0F2FE` (Light Blue) | `#0284C7` (Sky Blue) | Solid border, representation of gateway |
| **Broker (Redis)** | `#FEE2E2` (Light Red) | `#DC2626` (Red) | Use Cylinder/Database shape |
| **Workers (Celery Cluster)** | `#DCFCE7` (Light Green) | `#16A34A` (Green) | Dotted or soft border representing asynchronous process |
| **Database (Postgres)** | `#F3E8FF` (Light Purple) | `#7C3AED` (Purple) | Cylinder shape with horizontal lines |
| **AI Engine (DeepSeek)** | `#FEF9C3` (Light Yellow) | `#CA8A04` (Gold/Orange) | Cloud shape or glowing star icon |

### 2. Typography & Fonts
* **Main Titles**: Use **Sans-serif** (Bold, Large size).
* **Component Names**: Use **Monospace** (Medium size) so they look like actual code packages (e.g., `data_cleaner.py`, `SQLAlchemy ORM`).
* **Step Labels & Annotations**: Use **Hand-drawn** (Small size) for a natural, sketch-like flow.

### 3. Stroke & Arrow Styles
* **Synchronous Requests (HTTP/REST)**: Solid lines (`──>`) with sharp arrowheads.
* **Asynchronous Jobs (Celery/Redis)**: Dashed lines (`- - >`) to represent queueing & background execution.
* **Database Queries (SQL/ORM)**: Medium-stroke solid lines.
* **External APIs**: Bi-directional dashed lines (`< - - >`) with retry labels.
* **Roughness**: Set to **Medium** to give that signature Excalidraw hand-drawn sketch vibe.

---

## 🏗️ Step 1: Canvas Layout & Positioning (The Grid)
Apne Excalidraw canvas par components ko is order me arrange karein taaki flow **Left-to-Right** aur **Top-to-Bottom** readable ho:

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   [ Client Browser ] ──(1) Upload───> [ FastAPI Gateway ]             │
│          ▲                                   │                         │
│          │ (14) Poll Status & Results        │ (2) ORM                 │
│          ▼                                   ▼                         │
│   [ Client Polls ] <─(15,16) Fetch─── [ SQLAlchemy ORM ]               │
│                                              │                         │
│                                              │ (3) Save                │
│                                              ▼                         │
│                                       [( PostgreSQL )]                 │
│                                              ▲                         │
│                                              │ (7, 12, 13) Read/Write  │
│                                              │                         │
│   [ Redis Broker ] <──(4) Push Payload ──────┘                         │
│          │                                                             │
│          │ (6) Dequeue Task                                            │
│          ▼                                                             │
│   [ Celery Worker ]                                                    │
│    ├───> [ data_cleaner.py ] (8. Clean & Deduplicate)                  │
│    ├───> [ anomaly_detector.py ] (9. 3x Median & USD Check)            │
│    └───> [ llm_client.py ] (10. DeepSeek Client)                       │
│                  │                                                     │
│                  └────(11) HTTPS Requests/Retries───> [ DeepSeek API ] │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Canvas Elements to Draw:
1. **Frames (F key)**:
   * Create 5 separate **Frames** (dotted light grey containers) to group your modules:
     * `API Gateway Layer`
     * `Message Broker`
     * `Worker Cluster`
     * `Persistence Layer`
     * `Cognitive AI Layer`
2. **Components**:
   * Draw rounded rectangles for Python services/classes.
   * Draw cylinders for Redis and Postgres.
   * Draw a Cloud/Bubble shape for the DeepSeek API.

---

## 🔄 Step 2: Drawing the Request Lifecycle (16 Arrow Steps)
Draw these arrows one-by-one to visualize the entire end-to-end processing pipeline:

### Phase 1: Ingestion & Handshake (Fast & Responsive)
1. **Arrow 1**: Client Browser ➔ FastAPI Gateway
   * **Style**: Solid, Sky Blue arrow.
   * **Label**: `1. POST /jobs/upload (CSV File)`
2. **Arrow 2**: FastAPI Gateway ➔ SQLAlchemy ORM Engine
   * **Style**: Solid line.
   * **Label**: `2. Instantiate Job`
3. **Arrow 3**: SQLAlchemy ORM Engine ➔ PostgreSQL Database
   * **Style**: Solid, Purple arrow.
   * **Label**: `3. Save Metadata (status='pending')`
4. **Arrow 4**: FastAPI Gateway ➔ Redis In-Memory Queue
   * **Style**: Dashed, Red arrow.
   * **Label**: `4. Push Task Payload (UUID + CSV)`
5. **Arrow 5**: FastAPI Gateway ➔ Client Browser
   * **Style**: Solid, Sky Blue arrow.
   * **Label**: `5. Instant 201 Created Response (UUID)`

### Phase 2: Asynchronous Background Pipeline
6. **Arrow 6**: Redis In-Memory Queue ➔ Celery Worker Cluster
   * **Style**: Dashed, Green arrow.
   * **Label**: `6. Dequeue Task (process_transaction_job)`
7. **Arrow 7**: Celery Worker ➔ SQLAlchemy ORM Engine
   * **Style**: Solid line.
   * **Label**: `7. Update Job Status ('processing')`
8. **Arrow 8**: Celery Worker ➔ `data_cleaner.py`
   * **Style**: Thin Solid line.
   * **Label**: `8. Clean CSV, Normalize Dates, Deduplicate`
9. **Arrow 9**: Celery Worker ➔ `anomaly_detector.py`
   * **Style**: Thin Solid line.
   * **Label**: `9. Check 3x Median & Geolocation Mismatch`
10. **Arrow 10**: Celery Worker ➔ `llm_client.py`
    * **Style**: Thin Solid line.
    * **Label**: `10. Parse Uncategorized Rows`
11. **Arrow 11**: `llm_client.py` ➔ DeepSeek API (deepseek-chat)
    * **Style**: Bidirectional Double-Headed Dashed Yellow line.
    * **Label**: `11. Batch Categorization & Summarize (HTTPS with Backoff)`
12. **Arrow 12**: Celery Worker ➔ SQLAlchemy ORM Engine
    * **Style**: Solid line.
    * **Label**: `12. Save Transactions, Metrics & Summary`
13. **Arrow 13**: SQLAlchemy ORM Engine ➔ PostgreSQL Database
    * **Style**: Solid, Purple arrow.
    * **Label**: `13. Commit Transaction & Set status='completed'`

### Phase 3: Results Polling & Delivery
14. **Arrow 14**: Client Browser ➔ FastAPI Gateway
    * **Style**: Solid line.
    * **Label**: `14. GET /jobs/:id/results (Poll)`
15. **Arrow 15**: FastAPI Gateway ➔ SQLAlchemy ORM Engine ➔ PostgreSQL
    * **Style**: Solid line.
    * **Label**: `15. Fetch Job, Transactions, and Summaries`
16. **Arrow 16**: FastAPI Gateway ➔ Client Browser
    * **Style**: Solid, Sky Blue arrow.
    * **Label**: `16. Output Cleaned JSON Payload`

---

## 🗄️ Step 3: Drawing the Database ER-Diagram (Schema)
Create a separate section on your canvas for the relational schema representation.

### Drawing Technique:
1. Use **Rectangles** with **3 vertical columns** or draw horizontal dividers to partition the table name, field names, and data types.
2. Align table titles in bold and monospace format (e.g. `jobs`).
3. Draw primary keys (`PK`) and foreign keys (`FK`) explicitly.

### Tables & Fields to Draw:

#### 1. Table `jobs` (Color: Pastel Purple Background)
```text
┌──────────────────────────────────────┐
│                 jobs                 │
├──────────────────────────────────────┤
│ 🔑 id (UUIDv4)                  PK   │
│ 📝 filename (VARCHAR)                │
│ ⚙️ status (VARCHAR)                  │
│ 📊 row_count_raw (INT)               │
│ 🧹 row_count_clean (INT)             │
│ 📅 created_at (TIMESTAMP)            │
│ 🏁 completed_at (TIMESTAMP)          │
│ ❌ error_message (TEXT)              │
└──────────────────────────────────────┘
```

#### 2. Table `transactions` (Color: Pastel Purple Background)
```text
┌──────────────────────────────────────┐
│             transactions             │
├──────────────────────────────────────┤
│ 🔑 id (UUIDv4)                  PK   │
│ 🔗 job_id (UUIDv4)              FK   │
│ 🆔 txn_id (VARCHAR)                  │
│ 📅 date (VARCHAR)                    │
│ 🏪 merchant (VARCHAR)                │
│ 💵 amount (DOUBLE)                   │
│ 💱 currency (VARCHAR)                │
│ 🚦 status (VARCHAR)                  │
│ 🏷️ category (VARCHAR)                │
│ 👤 account_id (VARCHAR)              │
│ 🚨 is_anomaly (BOOLEAN)              │
│ 💬 anomaly_reason (TEXT)             │
│ 🤖 llm_category (VARCHAR)            │
│ 🧠 llm_raw_response (TEXT)           │
│ ⚠️ llm_failed (BOOLEAN)              │
└──────────────────────────────────────┘
```

#### 3. Table `job_summaries` (Color: Pastel Purple Background)
```text
┌──────────────────────────────────────┐
│            job_summaries             │
├──────────────────────────────────────┤
│ 🔑 id (UUIDv4)                  PK   │
│ 🔗 job_id (UUIDv4)       FK (Unique) │
│ 🇮🇳 total_spend_inr (DOUBLE)          │
│ 🇺🇸 total_spend_usd (DOUBLE)          │
│ 🛍️ top_merchants (JSON)              │
│ 🚨 anomaly_count (INT)               │
│ 📝 narrative (TEXT)                  │
│ ⚠️ risk_level (VARCHAR)              │
└──────────────────────────────────────┘
```

### Relationship connectors (Lines):
* Connect `jobs.id` ➔ `transactions.job_id` using a **One-to-Many** relationship line.
  * *Excalidraw Tip*: Draw a line where the end near `jobs` has a single crossbar (`|`), and the end near `transactions` has a crow's foot fork (`<`).
* Connect `jobs.id` ➔ `job_summaries.job_id` using a **One-to-One** relationship line.
  * *Excalidraw Tip*: Draw a line with a crossbar (`|`) on both sides.

---

## 💡 Pro Excalidraw Hacks for Premium Look
1. **Grid Snapping**: Keep "Snap to grid" enabled (`Ctrl/Cmd + Shift + G`) to make sure all boxes and arrows align perfectly.
2. **Library Import (Icons)**:
   * Click on the Library icon (top right corner of the Excalidraw interface).
   * Search for **"Software Architecture"** or **"Cloud & Database"**.
   * Add PostgreSQL, Redis, Fastapi/Python, and Client/Browser icons to place on top of your boxes for a gorgeous look.
3. **Embed Hand-written comments**: Add small notes with a hand-drawn circle tool around sections like the "3x Median Outlier logic" next to `anomaly_detector.py` or the "PgBouncer suggestion" next to the Postgres DB connection to show your technical depth.
4. **Export Settings**:
   * Export as **SVG** if you want to embed it directly in your markdown documents (`docs/`) because SVG scales perfectly without pixelation.
   * Export as **PNG (with Dark Mode toggle if applicable)** for presentations or slack shares. Select "Include background" to keep canvas colors intact.

---

*Now open [Excalidraw](https://excalidraw.com) and start building! If you need help structuring other modules, just ask!*
