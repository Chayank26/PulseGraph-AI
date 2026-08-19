# PulseGraph AI: Neuro-Symbolic Multimodal Clinical Decision Support System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-blue.svg)](https://www.postgresql.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)

PulseGraph AI is an enterprise-grade, API-driven, multimodal Neuro-Symbolic Clinical Decision Support System (CDSS). It combines LangGraph multi-agent workflow orchestration, strict clinical completeness checking, sequential blocking data acquisition requests, Human-in-the-Loop (HITL) physician approval, and PostgreSQL data persistence.

---

## 🏛️ System Architecture

PulseGraph AI follows a strict separation of concerns architecture:

```
                  ┌─────────────────────────────────────────┐
                  │          Attending Clinician            │
                  └────────────────────┬────────────────────┘
                                       │ (REST / JWT)
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │            FastAPI Backend              │
                  │   (/api/auth, /patients, /sessions)     │
                  └───────────┬─────────────────┬───────────┘
                              │                 │
           (Persists Domain)  ▼                 ▼ (Orchestrates State)
        ┌─────────────────────────┐        ┌─────────────────────────┐
        │  PostgreSQL Database    │        │  LangGraph StateGraph   │
        │  (Doctors, Patients,    │        │  (Triage, Vision,       │
        │   Sessions, Requests,   │        │   Diagnostic, Evidence, │
        │   Audit Logs, Results)  │        │   Safety, Guardrails)   │
        └─────────────────────────┘        └─────────────────────────┘
```

### Multi-Agent Workflow Topology

```
 [START] ──► triage ──► imaging ──► diagnostic ──► evidence ──► safety ──► symbolic_guardrail ──► human_review
               │           │            │             │          │                │                   │
               ▼           ▼            ▼             ▼          ▼                ▼                   │
       [data_request_review] ◄────────────────────────────────────────────────────────────────────────┘
               │
               ▼ (Resumes directly at requesting agent e.g. triage/imaging/safety)
```

1. **Triage Agent (`src/agents/triage.py`)**: Strict zero-defaults clinical risk score calculation (HEART, Wells PE, CURB-65). Creates a blocking `ClinicalDataRequest` if required parameters are missing.
2. **Imaging Vision Agent (`src/agents/imaging.py`)**: Computer vision diagnostic analysis for Chest X-Ray DICOM/PNG images (pleural effusion, pneumothorax, cardiomegaly).
3. **Diagnostic Agent (`src/agents/diagnostic.py`)**: Formulates ICD-10 differential diagnosis candidates with clinical rationales and recommended workups.
4. **Evidence RAG Agent (`src/agents/evidence_rag.py`)**: Retrieves peer-reviewed literature citations and PubMed guidelines to ground recommendations.
5. **Safety Agent (`src/agents/safety.py`)**: Audits drug-drug interactions, allergy contraindications, and physiological safety thresholds.
6. **Symbolic Guardrail Agent (`src/agents/symbolic_guardrail.py`)**: Deterministic, non-negotiable rule overrides (e.g. severe bradycardia beta-blocker contraindication).
7. **Human Review Node (`human_review_node`)**: HITL checkpoint requiring attending physician validation before EHR package export.

---

## 📁 Repository Structure

```
PulseGraph AI/
├── config/
│   └── settings.py             # Pydantic environment configuration & security validators
├── src/
│   ├── api/                    # Modular FastAPI REST API layer
│   │   ├── main.py             # FastAPI app initialization, lifespan, CORS, and exception handlers
│   │   ├── dependencies.py     # Database session injection & JWT clinician authentication
│   │   ├── routes/             # API routers (auth, doctors, patients, sessions, clinical)
│   │   └── schemas/            # Pydantic v2 request/response OpenAPI schemas
│   ├── db/                     # PostgreSQL database & SQLAlchemy 2.x persistence layer
│   │   ├── database.py         # Engine, SessionLocal, and table initialization
│   │   ├── models.py           # SQLAlchemy ORM models (Doctor, Patient, Session, Request, Audit, CDS)
│   │   └── repositories/       # Data access repositories (doctor, patient, session)
│   ├── services/
│   │   └── clinical_workflow.py# ClinicalWorkflowService connecting API to LangGraph & PostgreSQL
│   ├── agents/                 # Specialized clinical AI agent implementations
│   ├── core/                   # State definitions, data request helpers, and StateGraph machine
│   │   ├── state.py            # Central ClinicalState and domain Pydantic models
│   │   ├── graph.py            # LangGraph multi-agent workflow state machine
│   │   ├── checkpointer.py     # Pluggable execution checkpointer provider
│   │   └── data_requests.py    # Sequential blocking ClinicalDataRequest helpers
│   ├── main.py                 # Backend API entry point server runner
│   └── ui.py                   # Streamlit web dashboard
├── alembic/                    # Database migration scripts
│   └── versions/               # Alembic schema version files
├── scripts/
│   └── demo_phase3.py          # Legacy CLI demonstration execution script
├── tests/                      # Comprehensive Pytest test suite (84 passing tests)
├── docker-compose.yml          # PostgreSQL 16 Docker container configuration
├── .env.example                # Environment variable template
├── requirements.txt            # Core framework dependencies
└── README.md
```

---

## 📋 Prerequisites

* **Python**: 3.10 or higher
* **Docker & Docker Compose**: Required for running PostgreSQL instance

---

## ⚙️ Environment Configuration

Create a local `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `POSTGRES_DB` | PostgreSQL Database Name | `pulsegraph` |
| `POSTGRES_USER` | PostgreSQL Username | `pulsegraph_user` |
| `POSTGRES_PASSWORD` | PostgreSQL Password | `your_secure_postgres_password_here` |
| `DATABASE_URL` | PostgreSQL SQLAlchemy Connection URL | `postgresql://pulsegraph_user:password@localhost:5432/pulsegraph` |
| `PULSEGRAPH_JWT_SECRET` | JWT Secret Key for Session Tokens | `your_secure_jwt_secret_key_here` |
| `JWT_EXPIRATION_MINUTES` | Token Validity Duration | `10080` (7 days) |
| `OPENAI_API_KEY` | OpenAI API Key (Vision & LLM Reasoning) | `sk-...` |

---

## 🚀 Quickstart Guide

### 1. Start Docker PostgreSQL Database

```bash
docker compose up -d
```
Verify container status:
```bash
docker exec pulsegraph_postgres pg_isready -U pulsegraph_user -d pulsegraph
```

### 2. Environment & Dependency Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install core dependencies
pip install -r requirements.txt
```

### 3. Run Database Migrations

Apply database schema to PostgreSQL:
```bash
alembic upgrade head
```

### 4. Start Backend Server

Launch the production FastAPI server:
```bash
python -m src.main
```
> The API server will start at `http://localhost:8000`.

---

## 📖 API Documentation

Interactive API documentation is automatically generated:

* **Swagger UI**: `http://localhost:8000/docs`
* **ReDoc UI**: `http://localhost:8000/redoc`
* **OpenAPI Specification**: `http://localhost:8000/openapi.json`

### Key Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Authenticate clinician and receive JWT token |
| `POST` | `/api/doctors` | Register a new physician |
| `GET` | `/api/doctors/me` | Retrieve authenticated physician profile |
| `POST` | `/api/patients` | Create a new patient record |
| `GET` | `/api/patients/{patient_id}` | Get patient record details |
| `POST` | `/api/clinical/sessions` | Initialize a clinical decision support session |
| `POST` | `/api/clinical/sessions/{id}/run` | Trigger/execute multi-agent workflow |
| `GET` | `/api/clinical/sessions/{id}/data-requests` | Retrieve pending blocking data requests |
| `POST` | `/api/clinical/sessions/{id}/data-requests/{req_id}/resolve` | Submit requested clinical field values and resume graph |
| `GET` | `/api/clinical/sessions/{id}/review` | Fetch complete HITL review package |
| `POST` | `/api/clinical/sessions/{id}/approve` | Clinician approval and EHR export |
| `POST` | `/api/clinical/sessions/{id}/reevaluate` | Request physician re-evaluation loop |
| `POST` | `/api/clinical/sessions/{id}/reject` | Clinician rejection / manual takeover |
| `GET` | `/api/clinical/sessions/{id}/audit-trail` | Retrieve append-only audit log |

---

## 🔄 Example Workflow Lifecycle

1. **Clinician Authentication**: Doctor logs in via `POST /api/auth/login` and receives a JWT bearer token.
2. **Patient Registration**: Patient record is created via `POST /api/patients`.
3. **Session Initialization**: Clinical assessment session is initialized via `POST /api/clinical/sessions`.
4. **Workflow Execution**: Workflow is triggered via `POST /api/clinical/sessions/{id}/run`.
   - If required parameters are missing, triage pauses execution at `data_request_review` and creates a `ClinicalDataRequest`.
5. **Data Acquisition Resolution**: Clinician submits requested data via `POST /api/clinical/sessions/{id}/data-requests/{request_id}/resolve`. The graph validates inputs and resumes execution directly at the requesting node (`triage`).
6. **HITL Review & Approval**: Attending clinician reviews differential diagnoses, imaging reports, and symbolic overrides, approving recommendations via `POST /api/clinical/sessions/{id}/approve`.
7. **EHR Package Export**: Approved CDS package is exported to EHR and persisted in PostgreSQL (`CDSResultModel`).

---

## 🧪 Testing

Run the comprehensive test suite covering database repositories, API endpoints, authentication security, sequential data acquisition, HITL loops, and end-to-end workflows:

```bash
python -m pytest tests/
```

> **84 / 84 tests passing** in 11.23 seconds.

---

## ⚠️ Current Limitations

* **Execution Checkpointer**: Uses `MemorySaver` in-memory checkpointer by default for development workflow step resumption. Production deployments should configure persistent checkpointers (e.g. `PostgresSaver` / `RedisSaver`).
* **Mock Image Analysis**: If `OPENAI_API_KEY` is unpopulated, the imaging agent uses heuristic vision output based on image file metadata.

---

## 🔮 Future Production Improvements

1. **Production LangGraph Checkpointer**: Integrate `langgraph-checkpoint-postgres` for multi-instance checkpointer persistence.
2. **FHIR R4 Server Adapter**: Direct RESTful synchronization with SMART-on-FHIR EHR servers (Epic, Cerner).
3. **Enterprise SSO**: OAuth2 / OIDC integration for hospital Active Directory physician login.

---

## 🔒 Safety & Medical Disclaimer

> **IMPORTANT**: PulseGraph AI is intended strictly for clinical decision support research, algorithm development, and decision evaluation. It does NOT provide standalone medical advice or replace professional clinical judgment.
