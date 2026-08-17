# Member 360° Health Intelligence Assistant

> **AI-Powered Operational Healthcare Intelligence Platform for Service Representatives and Care Coordinators**  
> *Built with Python, FastAPI, Jinja2, MongoDB, Pandas, and Google Gemini API.*

---

## 🌟 Executive Summary

The **Member 360° Health Intelligence Assistant** transforms fragmented synthetic healthcare records into a unified, traceable 360° view of a member. It empowers service representatives and care coordinators to immediately access member demographics, eligibility coverage, claims history, medications, care gaps, prior authorizations, and recent service interactions.

The platform pairs **deterministic Python-level open issue detection** with **Google Gemini-powered intelligence summaries**, enforcing strict clinical safety guardrails and providing **verifiable database source traceability** for every generated insight.

---

## ⚠️ Synthetic Healthcare Data & Safety Notice

- **Synthetic Data**: This application uses **synthetic healthcare data** derived from the Synthea patient simulator. It does NOT contain real patient data, real Protected Health Information (PHI), or real insurance identifiers.
- **Operational Focus**: The AI assistant provides administrative and operational coordination support. It **does NOT diagnose diseases, prescribe treatments, or alter medication regimens**.

---

## 🏗️ System Architecture

```
Raw Synthea CSVs (16 files)
      │
      ▼
Data Transformation Pipeline (Pandas)
      │
      ▼
Processed Member 360 Data (7 normalized datasets)
      │
      ▼
Data Validation & Integrity Checks (0 FK orphans, 100% relational integrity)
      │
      ▼
MongoDB Document Store (Indexes on member_id, dates, statuses)
      │
      ├──► FastAPI Backend REST Endpoints (/api/members, /api/member/{id}, /api/health)
      │
      ├──► Deterministic Open Issue Detector (Pending auths, claims, gaps, contacts)
      │
      ├──► Google Gemini AI Engine (Strict JSON Schema, Grounded Prompting)
      │
      └──► Jinja2 Glassmorphic Web UI (Responsive Dashboard, Source Inspector Modal)
```

---

## 📂 Project Structure

```
member360-health-intelligence/
├── app/
│   ├── main.py                     # FastAPI application, static/template mounting, lifespan
│   ├── api/
│   │   ├── routes_members.py       # Member listing, search, and 360° profile endpoints
│   │   ├── routes_ai.py            # AI summary generation & source record inspector
│   │   └── routes_health.py        # System health and collection diagnostics
│   ├── models/                     # Core domain entities
│   ├── schemas/
│   │   ├── member.py               # Pydantic schemas for Member 360 response
│   │   └── ai.py                   # Pydantic schemas for AI summary and source traceability
│   ├── services/
│   │   ├── member_service.py       # Search and pagination service
│   │   ├── aggregation_service.py  # 360° profile aggregation & deterministic issue rules
│   │   └── ai_service.py           # Gemini API integration, prompt guardrails, source verification
│   ├── database/
│   │   └── mongodb.py              # MongoDB connection manager with resilient mongomock fallback
│   ├── templates/                  # Jinja2 UI templates
│   │   ├── base.html               # Base layout, navbar, source record modal
│   │   ├── index.html              # Homepage with operational metrics & quick search
│   │   ├── member_search.html      # Searchable member directory with pagination
│   │   └── member_360.html         # Interactive 360° profile & AI intelligence dashboard
│   └── static/
│       ├── css/style.css           # Modern dark navy glassmorphic design system
│       └── js/member_360.js        # Tab manager, AI summary caller, interactive modal
├── data/
│   ├── raw/synthea/                # 16 unmodified raw Synthea CSV files
│   └── processed/                  # 7 cleaned & derived Member 360 CSV files
├── scripts/
│   ├── inspect_data.py             # Schema inspection tool
│   ├── transform_data.py           # Pandas transformation pipeline
│   ├── generate_synthetic_data.py  # Deterministic synthetic authorizations & interactions
│   ├── validate_data.py            # Relational integrity and schema validator
│   └── load_mongodb.py             # Bulk loader and index builder
├── tests/
│   ├── test_data.py                # Pipeline and foreign key referential integrity tests
│   ├── test_members.py             # Member API and 360 aggregation tests
│   └── test_ai.py                  # Open issue detector, AI schema, and source verification tests
├── .env.example
├── requirements.txt
└── README.md
```

---

## 📊 Data Validation Report

The automated validation suite (`scripts/validate_data.py`) verifies 100% referential integrity across all entities:

| Entity | Records | Primary Key | Foreign Key Status |
| :--- | :--- | :--- | :--- |
| **Members** | 1,171 | `member_id` | Master Table |
| **Eligibility** | 3,989 | `eligibility_id` | 100% Linked to Valid Members |
| **Claims-Like View** | 53,346 | `claim_id` | 100% Linked to Valid Members |
| **Medications** | 42,989 | `medication_id` | 100% Linked to Valid Members |
| **Care Gaps** | 3,688 | `gap_id` | 100% Linked to Valid Members |
| **Authorizations** | 1,113 | `authorization_id` | 100% Linked to Valid Members |
| **Interactions** | 2,258 | `interaction_id` | 100% Linked to Valid Members |
| **Total Documents** | **108,554** | — | **0 Invalid / 0 Missing FKs** |

---

## ⚡ Setup and Installation

### 1. Clone & Environment Setup
```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=member360
GEMINI_API_KEY=your_google_gemini_api_key_here
APP_ENV=development
```
*(Note: If a local MongoDB instance is offline, the backend automatically activates its in-memory fallback engine so all features, tests, and web pages work out of the box).*

---

## 🚀 Data Pipeline Execution Commands

Execute the data pipeline steps in order:

```bash
# 1. Inspect raw Synthea dataset schemas
python scripts/inspect_data.py

# 2. Transform raw files into normalized Member 360 CSVs
python scripts/transform_data.py

# 3. Generate reproducible synthetic prior authorizations & service interactions
python scripts/generate_synthetic_data.py

# 4. Run data validation & integrity report
python scripts/validate_data.py

# 5. Populate MongoDB collections and create query indexes
python scripts/load_mongodb.py
```

---

## 🌐 Running the Web Application

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```
Open your browser and navigate to:
- **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Member Directory**: [http://localhost:8000/search](http://localhost:8000/search)
- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **System Health Diagnostics**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 🧪 Automated Testing

Run the test suite with pytest:
```bash
python -m pytest -v
```
All **13 unit and integration tests** validate data schemas, foreign keys, 360° aggregation, deterministic open issue rules, AI schema validation, and source record traceability.

---

## 🛡️ AI Guardrails & Source Traceability

1. **Deterministic Rule Engine**: Pending prior authorizations, pending claims, open care gaps, and unresolved service interactions are detected deterministically in Python before any LLM processing.
2. **Grounded Gemini Prompting**: Strict system instructions prevent unsupported medical conclusions, disease predictions, or clinical prescriptions.
3. **Pydantic Validation**: AI JSON responses are strictly validated against `AISummaryResponse` schema (`key_facts`, `open_issues`, `next_actions`, `sources`).
4. **Source Inspector Modal**: Every AI insight includes a clickable source badge (e.g. `📍 Source: authorization [AUTH-1001]`). Clicking the badge queries `GET /api/ai/source/{type}/{id}` and renders the original database document for immediate verification.
