# KIIT Placement Preparation Platform (KIIT PrepAI)

> **Agentic AI & RAG-Powered Campus Placement Intelligence Portal**  
> Built for **Kalinga Institute of Industrial Technology (KIIT University)** students.  
> Powered by **FastAPI**, **PostgreSQL 17**, **SQLAlchemy**, **LangGraph + Gemini**, **Local Document RAG (pypdf + TF-IDF/NumPy)**, and a **Vanilla HTML/CSS/JS** Single Page Application.

---

## 📋 Table of Contents
- [Project Overview](#-project-overview)
- [System Architecture](#-system-architecture)
- [Database Schema (ER Diagram)](#-database-schema-er-diagram)
- [Key Features](#-key-features)
- [Technology Stack](#-technology-stack)
- [Project Directory Structure](#-project-directory-structure)
- [Step-by-Step Setup Guide](#-step-by-step-setup-guide)
- [API Endpoints Reference](#-api-endpoints-reference)
- [Question Bank & Provenance Rules](#-question-bank--provenance-rules)
- [RAG Pipeline & Deterministic Fallback Engine](#-rag-pipeline--deterministic-fallback-engine)
- [Automated Testing](#-automated-testing)
- [Team Collaboration & Deployment](#-team-collaboration--deployment)

---

## 🚀 Project Overview

**KIIT PrepAI** is an institutional placement preparation platform engineered to solve the fragmentation of placement resources across university circulars, Google Drives, senior interview reports, and generic coding websites. 

The platform combines:
1. **Verified KIIT Placement Rules:** Official recruitment guidelines, CGPA cutoffs, backlog allowances, and selection processes directly transcribed from official Training & Placement (T&P) brochures (TCS, IBM, Cognizant, Accenture, Deloitte, HighRadius, Tech Mahindra).
2. **Provenance-Preserved Question Bank:** 271 categorized questions across 22 companies, strictly categorizing verified Previous Year Questions (`PYQ`), standard practice (`PRACTICE`), and unverified student interview recollections (`REPORTED`).
3. **Anti-Leakage Mock Arena:** Dynamic timed MCQ test sessions that hide answer keys and explanations until submission, prevent duplicate submissions, and link directly to student accounts.
4. **Performance & Weakness Analytics:** Automatic aggregation of category accuracy and topic mastery sorted weakest-first to drive targeted revision.
5. **Hybrid Agentic AI Assistant:** LangGraph ReAct agent with tools for database querying and document retrieval, supported by a deterministic zero-cloud **Database + Document RAG Fallback Engine** that delivers verified answers in under 2 seconds.

---

## 🏛️ System Architecture

```mermaid
flowchart TB
    subgraph Client ["Client Layer (Browser / SPA)"]
        UI["Vanilla SPA (HTML5 / CSS3 / ES6)"]
        UI_Auth["Student Auth Portal (Login / Signup / Guest)"]
        UI_Comp["Company Explorer"]
        UI_QBank["Question Bank & Filters"]
        UI_Mock["Mock Arena & Real-time Timer"]
        UI_Perf["Performance & Weakness Analytics"]
        UI_Chat["AI Assistant Chat & PDF RAG Search"]
    end

    subgraph API_Gateway ["FastAPI Application Gateway (:8000)"]
        CORS["CORS Middleware"]
        AuthMid["PBKDF2 Password Hashing & Signed HMAC Bearer Token Guard"]
        StaticServe["StaticFiles Mount (/ui -> index.html)"]
    end

    subgraph Routers ["FastAPI Routers"]
        R_Auth["/auth (Signup, Login, /me)"]
        R_Comp["/companies (List, Details, Eligibility, Rounds)"]
        R_Ques["/questions (List, Filters, Create)"]
        R_Mock["/mock (Start, Submit, Result Review)"]
        R_Perf["/performance (Student Dashboard, Weak Topics)"]
        R_Agent["/agent (Chat, RAG Search, Diagnostics)"]
    end

    subgraph Core_Services ["Application Core Services"]
        MockEngine["Mock Evaluation & Anti-Leakage Service"]
        PerfEngine["Performance Aggregation & Topic Ranker"]
        AgentEngine["LangGraph ReAct Agent (Gemini 1.5/2.0 Flash)"]
        LocalRAG["Deterministic Database + Document RAG Fallback Engine"]
    end

    subgraph RAG_Pipeline ["Local Document RAG Indexer"]
        PDFReader["pypdf Document Extractor (11 KIIT PDFs)"]
        Chunker["RecursiveCharacterTextSplitter (500 chars / 80 overlap)"]
        VectorMatrix["Lightweight TF-IDF Matrix + NumPy Cosine Engine"]
    end

    subgraph Data_Storage ["Persistent Layer (PostgreSQL 17 / Supabase)"]
        DB_Students[("students")]
        DB_Companies[("companies")]
        DB_Elig[("eligibility_criteria")]
        DB_Rounds[("selection_rounds")]
        DB_Questions[("questions")]
        DB_Mock[("mock_attempts")]
        DB_Answers[("attempt_answers")]
    end

    UI --> API_Gateway
    API_Gateway --> Routers
    Routers --> Core_Services
    Core_Services --> Data_Storage
    R_Agent --> AgentEngine
    R_Agent --> LocalRAG
    LocalRAG --> RAG_Pipeline
    AgentEngine --> RAG_Pipeline
```

---

## 🗄️ Database Schema (ER Diagram)

The relational schema enforces strict integrity constraints, foreign key cascades, and check constraints:

```mermaid
erDiagram
    students ||--o{ mock_attempts : "takes"
    companies ||--o| eligibility_criteria : "specifies"
    companies ||--o{ selection_rounds : "conducts"
    companies ||--o{ questions : "associated_with"
    companies ||--o{ mock_attempts : "targeted_by"
    mock_attempts ||--o{ attempt_answers : "contains"
    questions ||--o{ attempt_answers : "answers_for"

    students {
        int id PK
        varchar full_name
        varchar roll_number UK
        varchar email UK
        varchar branch
        decimal cgpa
        varchar password_hash
        timestamp created_at
    }

    companies {
        int id PK
        varchar name UK
        varchar industry
        text description
        timestamp created_at
        timestamp updated_at
    }

    eligibility_criteria {
        int id PK
        int company_id FK,UK
        decimal cgpa_cutoff
        int backlogs_allowed
        text branches
        text additional_notes
    }

    selection_rounds {
        int id PK
        int company_id FK
        int round_number
        varchar round_name
        text description
    }

    questions {
        int id PK
        int company_id FK
        varchar category
        varchar topic
        varchar difficulty
        varchar question_type
        int year
        text source
        text question_text
        text option_a
        text option_b
        text option_c
        text option_d
        char correct_option
        text explanation
        timestamp created_at
    }

    mock_attempts {
        int id PK
        int student_id FK
        varchar student_name
        varchar student_roll_number
        int company_id FK
        varchar category
        int total_questions
        int correct_answers
        decimal score_percentage
        timestamp started_at
        timestamp completed_at
        int time_taken_seconds
    }

    attempt_answers {
        int id PK
        int attempt_id FK
        int question_id FK
        char selected_option
        text written_answer
        boolean is_correct
    }
```

---

## ✨ Key Features

1. **Student Authentication & Auto-Linking (`/auth`)**:
   - Zero-dependency security using Python standard library `PBKDF2-HMAC-SHA256` (120,000 rounds) and HMAC-SHA256 signed Bearer tokens (7-day TTL).
   - If a student previously took mock tests as a guest using their roll number (e.g. `22051001`), signing up with that roll number immediately links all past attempts to their profile.
2. **Company Explorer (`/companies`)**:
   - 22 registered companies (TCS, IBM, Cognizant, Accenture, Deloitte, HighRadius, Tech Mahindra, Amazon, Atlassian, Cisco, Dell, Visa, etc.).
   - Transparent metadata distinction: verified KIIT companies display official CGPA cutoffs and selection rounds; question-bank-only companies are marked as "Not Verified (Question Bank Only)" with honest 404 responses for missing criteria rather than invented data.
3. **Question Bank (`/questions`)**:
   - 271 questions (29 verified MCQs with full answer keys, 242 coding and CS questions).
   - Filter by Company, Category (`Aptitude`, `Reasoning`, `Verbal`, `Technical`, `Coding`), Question Type, Difficulty, and MCQ status.
4. **Mock Test Arena (`/mock`)**:
   - Generates random, dynamic MCQ sets strictly from complete questions (`option_a` through `option_d` + `correct_option`).
   - Anti-leakage: `correct_option` and `explanation` are filtered out of the API response during the test.
   - Real-time countdown/elapsed timer, question jump navigation pills, single-attempt validation, and instant post-submission grading with detailed explanations.
5. **Student Performance Analytics (`/performance`)**:
   - Aggregated KPIs: Completed tests, Average score, Personal best, and Questions answered.
   - Category-wise progress bars (`Aptitude`, `Reasoning`, `Verbal`, `Technical`).
   - Weakest-topic breakdown sorted in ascending order of accuracy to highlight exact revision areas.
   - Attempt review modal to inspect past tests question by question.
6. **AI Placement Assistant & Document RAG (`/agent`)**:
   - Indexes 18 files (11 recruitment PDFs + company notes + sources manifest = 167 vectorized chunks).
   - Hybrid execution: connects to Google Gemini via LangGraph when `GEMINI_API_KEY` is provided, or uses the local deterministic Database + RAG engine to respond in ~1.7 seconds with zero cloud dependencies.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI (Python 3.10+) | High-performance asynchronous REST API with automatic OpenAPI Swagger docs |
| **Web Server** | Uvicorn (ASGI) | Production and development server with hot-reload |
| **ORM / Database** | SQLAlchemy 2.0 + PostgreSQL 17 | Relational persistence, constraints, connection pooling, schema migrations |
| **Authentication** | PBKDF2-HMAC-SHA256 + Signed HMAC | Zero external dependency secure password hashing and stateless token verification |
| **AI Orchestration** | LangGraph + LangChain Core | ReAct agent with dynamic tool routing |
| **LLM Provider** | Google Gemini (`gemini-1.5-flash`) | Context-aware placement reasoning and synthesis |
| **PDF Extraction** | `pypdf` (v7.0+) | Text extraction from multi-page official placement notices and brochures |
| **Vector Engine** | NumPy + TF-IDF Cosine Similarity | Lightweight local vector search over document chunks |
| **Frontend** | Vanilla HTML5 / CSS3 / ES6 JavaScript | Zero-framework Single Page Application with component-based modular structure |

---

## 📁 Project Directory Structure

```text
Student Preparation Platform/
├── .env.example                     # Environment variables template for team members
├── .gitignore                       # Prevents committing venv, .env, and caches
├── README.md                        # Master project documentation
├── PROJECT_REPORT.md                # Comprehensive academic project report
├── backend/
│   ├── requirements.txt             # Python dependencies
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint & static mount
│   │   ├── database.py              # PostgreSQL engine & session lifecycle
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── schemas.py               # Pydantic v2 validation contracts
│   │   ├── auth_utils.py            # Password hashing, token signing, startup DDL
│   │   ├── agent/
│   │   │   ├── graph.py             # LangGraph agent graph + local deterministic fallback
│   │   │   ├── prompts.py           # Placement assistant system prompts & guidelines
│   │   │   └── tools.py             # 7 PostgreSQL & RAG tools for the agent
│   │   ├── rag/
│   │   │   ├── pipeline.py          # PDF extraction, chunking, TF-IDF indexer
│   │   │   └── retriever.py         # Document search and index status diagnostics
│   │   └── routes/
│   │       ├── auth.py              # /auth signup, login, /me
│   │       ├── company.py           # /companies listings, eligibility, selection rounds
│   │       ├── questions.py         # /questions search, filters, creation
│   │       ├── mock.py              # /mock start, submit, attempt retrieval
│   │       ├── performance.py       # /performance student dashboard & weak topics
│   │       └── agent.py             # /agent chat, RAG search, RAG status
│   └── scripts/
│       └── import_questions.py      # Idempotent CSV & practice question importer
├── database/
│   ├── schema.sql                   # Full PostgreSQL schema DDL
│   ├── seed.sql                     # Verified KIIT placement seed data (TCS, IBM, etc.)
│   └── migrations/
│       ├── 001_update_questions_table.sql # Extended schema for question provenance
│       └── 002_add_students_auth.sql      # Student table & mock FK migration
├── frontend/
│   ├── index.html                   # Single Page Application HTML shell
│   ├── css/
│   │   └── styles.css               # Clean responsive styling, themes, grid layout
│   └── js/
│       ├── api.js                   # Centralized API fetch client with Bearer auth
│       ├── app.js                   # Application state, session handling, view routing
│       ├── companies.js             # Company Explorer module
│       ├── questions.js             # Question Bank browser & filter module
│       ├── mock.js                  # Timed Mock Arena module
│       ├── performance.js           # Student Analytics & Weak Topics module
│       └── agent.js                 # AI Chat & PDF RAG Search module
├── question_bank/                   # Master question CSV index & company folders
├── resources/companies/             # Official KIIT recruitment brochures & company notes
└── tests/
    └── test_api.py                  # End-to-end automated API, auth, mock & RAG tests
```

---

## 💻 Step-by-Step Setup Guide

### 1. Clone the Repository
```powershell
git clone https://github.com/<your-username>/Student-Preparation-Platform.git
cd "Student Preparation Platform"
```

### 2. Set Up Virtual Environment & Dependencies
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 3. Configure Database (`student_prep_db`)
1. Open **pgAdmin 4** or run `psql -U postgres`.
2. Create database:
   ```sql
   CREATE DATABASE student_prep_db;
   ```
3. Open the Query Tool on `student_prep_db` and execute:
   - `database/schema.sql` (Creates tables, indexes, check constraints)
   - `database/seed.sql` (Inserts verified companies, eligibility, rounds, PYQs)

### 4. Configure Environment Variables
Copy the template to create your `.env` file:
```powershell
copy .env.example .env
```
Edit `.env` with your PostgreSQL password:
```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/student_prep_db
AUTH_SECRET_KEY=kiit-prep-dev-secret-key-change-in-production
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
```
*(Note: If `GEMINI_API_KEY` is left as placeholder or empty, the platform automatically runs in Database + Document RAG Fallback mode with zero external cloud dependencies).*

### 5. Import Master Question Bank
Run the idempotent import script to populate 240 questions from `question_bank/MASTER_QUESTION_INDEX.csv` and 20 practice MCQs:
```powershell
.\venv\Scripts\python backend/scripts/import_questions.py
```

### 6. Run the Application
Start the Uvicorn development server:
```powershell
$env:PYTHONPATH="backend"; .\venv\Scripts\uvicorn app.main:app --reload
```

- **Web Portal:** [http://127.0.0.1:8000/ui/](http://127.0.0.1:8000/ui/)
- **Swagger Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 📡 API Endpoints Reference

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | API Root welcome message | No |
| `GET` | `/health` | Diagnostic health check (PostgreSQL connectivity) | No |
| `POST` | `/auth/signup` | Register student, hash password, link prior mock tests, return token | No |
| `POST` | `/auth/login` | Authenticate by roll number or email, return Bearer token | No |
| `GET` | `/auth/me` | Fetch authenticated student profile | **Bearer Token** |
| `GET` | `/companies/` | List all 22 registered placement companies | No |
| `GET` | `/companies/{name}` | Fetch company description and industry | No |
| `GET` | `/companies/{name}/eligibility` | Fetch verified CGPA cutoff, backlogs allowed, eligible branches | No |
| `GET` | `/companies/{name}/selection-process`| Fetch ordered rounds (e.g. Online Test, Technical Interview) | No |
| `GET` | `/questions/` | Search questions with filters (company, category, type, difficulty, MCQ) | No |
| `GET` | `/questions/filters` | Aggregated filter options (total questions, MCQs, categories, topics) | No |
| `POST` | `/questions/` | Add question with optional options and answer key | No |
| `POST` | `/mock/start` | Start dynamic MCQ mock test (hides answers, links student) | Optional |
| `POST` | `/mock/{id}/submit` | Submit answers, grade attempt, calculate score %, reveal explanations | Optional |
| `GET` | `/mock/{id}` | Retrieve attempt (answers hidden if active, revealed if submitted) | Optional |
| `GET` | `/performance/` | List recent platform mock test attempts | No |
| `GET` | `/performance/me` | Aggregated metrics & weak-topic breakdown for logged-in student | **Bearer Token** |
| `GET` | `/performance/{student_id}` | Performance analytics by roll number or student name | No |
| `POST` | `/agent/chat` | Send placement query to LangGraph / RAG Assistant | Optional |
| `GET` | `/agent/rag/search` | Raw semantic search over PDF chunks and notes | No |
| `GET` | `/agent/rag/status` | Indexer diagnostic stats (chunk count, extracted PDFs) | No |

---

## 🛡️ Question Bank & Provenance Rules

A core design principle of KIIT PrepAI is **strict provenance preservation**:
- **`PYQ` (Previous Year Question):** Questions officially confirmed to have appeared in past KIIT placement test drives with documented year and test type (e.g. TCS NQT 2024/2025).
- **`PRACTICE`:** High-quality standard preparation problems across Aptitude, Reasoning, Verbal, and CS foundations.
- **`REPORTED`:** Interview questions reported informally by students on discussion platforms or senior exit interviews. **Rule:** These are *never* relabeled as official `PYQ`s.
- **Mock Arena Integrity:** Only questions having non-null options (`option_a` through `option_d`) and a validated `correct_option` in `('A', 'B', 'C', 'D')` are eligible for mock generation. Coding questions and unverified items are excluded.

---

## 🧠 RAG Pipeline & Deterministic Fallback Engine

The platform implements a **two-tier architecture** for zero-cloud resilience:

1. **Document Chunking & Vectorization:**
   - Reads official placement notices (`resources/companies/*/04_recruitment_documents/*.pdf`) using `pypdf`.
   - Chunks text into 500-character segments with 80-character sliding overlap via `RecursiveCharacterTextSplitter`.
   - Computes term frequencies across 167 indexed chunks using NumPy matrix cosine similarity with domain-specific relevance weighting (e.g. boosting official brochures over manifests).
2. **Execution Routing:**
   - If `GEMINI_API_KEY` is configured with a valid Google AI Studio key (`AIzaSy...`), requests execute through a LangGraph ReAct agent equipped with 7 tools.
   - If `GEMINI_API_KEY` is missing, invalid, or offline, the platform executes `_run_local_tool_agent()`: an intelligent regex and keyword router that inspects PostgreSQL and the vector index directly, returning verified responses in **1.70 seconds** without external API latency or failure points.

---

## 🧪 Automated Testing

An automated test suite (`tests/test_api.py`) runs against an isolated in-memory SQLite database (`StaticPool`) to ensure offline verification without mutating the live PostgreSQL database:

```powershell
.\venv\Scripts\python -m unittest tests/test_api.py -v
```

**Test Coverage:**
- Root endpoint and UI static file mounting.
- Company endpoints, verified eligibility, and honest 404 behavior for unverified companies.
- Question filtering and provenance tag integrity.
- Mock test start (anti-leakage check: `correct_option` and `explanation` stripped).
- Single submission enforcement, rejection of invalid question IDs, accurate score percentage calculation.
- Student authentication: signup, duplicate roll conflict (409), invalid credentials (401), and automatic linking of prior guest mock attempts.
- Performance aggregation and weakest-topic sorting.
- AI Agent RAG search and deterministic database fallback.

---

## 👥 Team Collaboration & Deployment

### Group Project Workflow
- `.env` and `venv/` are excluded by `.gitignore` to prevent credential leakage.
- Team members can clone the repository, copy `.env.example` to `.env`, and immediately test locally.

### Cloud Database Deployment (Supabase / Neon)
To share a single database across the team:
1. Create a free project on [Supabase](https://supabase.com) or [Neon](https://neon.tech).
2. Run `database/schema.sql` and `database/seed.sql` in the Supabase SQL Editor.
3. Run `python backend/scripts/import_questions.py` with the Supabase connection string.
4. Update `DATABASE_URL` in `.env` to point to the cloud database.

---

## 📜 License
Developed as an academic software engineering and agentic AI project for **KIIT University**. All official recruitment documents and question bank materials belong to their respective corporate and university rights holders.
