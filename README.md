# PulseGraph AI: Open-Source Clinical Decision Support & Diagnostics Agent Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)

PulseGraph AI is an open-source, multi-agent AI framework designed for clinical decision support (CDS), diagnostic reasoning, and evidence-grounded therapeutics safety auditing.

---

## 🏛️ Architecture Overview

PulseGraph AI orchestrates specialized clinical sub-agents within a state machine built on **LangGraph** and **Pydantic**:

```
 ┌────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
 │  Triage Agent  │ ──► │ Diagnostic Agent │ ──► │  Evidence RAG    │ ──► │   Safety Agent   │
 │ (Risk Calc)    │     │ (Differential)   │     │ (PubMed/Guideline│     │ (Pharmacology/   │
 └────────────────┘     └──────────────────┘     └──────────────────┘     │  Guardrails)     │
                                                                          └──────────────────┘
```

1. **Triage Agent (`src/agents/triage.py`)**: Parses raw clinical notes, ingests FHIR resources, extracts vital signs, and calculates clinical risk scores (BMI, Wells PE, CHA2DS2-VASc).
2. **Diagnostic Agent (`src/agents/diagnostic.py`)**: Formulates differential diagnostic candidates with ICD-10 codes, rationales, and recommended diagnostic workups.
3. **Evidence RAG Agent (`src/agents/evidence_rag.py`)**: Retrieves peer-reviewed clinical practice guidelines and literature citations to ground diagnostic candidates.
4. **Safety Agent (`src/agents/safety.py`)**: Audits drug-drug interactions, allergy contraindications, and critical physiological thresholds.

---

## 📁 Directory Structure

```
.
├── config/
│   └── settings.py             # Environment vars and API configs
├── data/
│   └── mock_patients/          # Synthetic FHIR JSON & clinical notes
├── src/
│   ├── agents/                 # Individual agent implementations
│   │   ├── triage.py
│   │   ├── diagnostic.py
│   │   ├── evidence_rag.py
│   │   └── safety.py
│   ├── core/                   # Shared types, state schemas, and graphs
│   │   ├── state.py            # LangGraph TypedDict & Pydantic state
│   │   └── graph.py            # Orchestrator & state machine
│   ├── tools/                  # Medical tools (calculators, RxNorm)
│   │   ├── calculators.py
│   │   └── pharmacology.py
│   └── main.py                 # CLI/API Entrypoint
├── tests/                      # Unit and integration tests
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/pulsegraph/pulsegraph-ai.git
cd "PulseGraph AI"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```

### 3. Run Verification Entrypoint
```bash
python -m src.main
```

### 4. Run Test Suite
```bash
pytest tests/
```

---

## 🔒 Safety & Disclaimer

> **IMPORTANT**: AegisCDS is intended strictly for clinical research, algorithm development, and decision support evaluation. It does NOT provide standalone medical advice or replace professional clinical judgment.
