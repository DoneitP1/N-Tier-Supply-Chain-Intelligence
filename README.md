# N-Tier Supply Chain Intelligence Platform

A high-performance supply chain risk analysis and data ingestion platform built with a modern, n-tier architecture. This system leverages Graph Databases (Neo4j) for deep relationship analysis and Large Language Models (LLM) for automated data extraction.

## 🚀 Modern Tech Stack

- **Frontend**: Next.js 14, React, TypeScript, Framer Motion (Glassmorphism UI)
- **Backend**: FastAPI (Python 3.11+), Pydantic v2
- **Data Layers**:
  - **Neo4j**: Graph database for N-tier supply chain modeling and recursive risk propagation.
  - **PostgreSQL**: Relational database for user management, auditing, and document metadata.
  - **Redis**: Caching layer and Celery task broker.
- **AI/LLM**: LangChain, Anthropic (Claude 3), Google Gemini (Optional)
- **DevOps & Monitoring**:
  - **Docker Compose**: Full stack orchestration.
  - **Prometheus & Grafana**: Real-time observability and dashboarding.
  - **Celery & Redis**: Asynchronous task processing (Outbox Pattern).

## 💡 Key Features

### 1. N-Tier Recursive Risk Engine
Analyzes supply chain disruptions up to 5 tiers deep. Uses Cypher recursive queries to identify cascading impacts from suppliers to final production factories, highlighting stock-out risks based on lead times.

### 2. Intelligent Data Ingestion
- **PDF Extraction**: Automated LLM-powered extraction from logistics contracts and news feeds.
- **Outbox Pattern**: Ensures eventual consistency between PostgreSQL (Audit) and Neo4j (Graph) through transactional events.
- **Entity Resolution**: High-performance fuzzy matching using Neo4j Full-Text Search and Vector Indexing.

### 3. Professional Observability
Integrated Prometheus metrics tracking API response times, ingestion success rates, and LLM token usage, visualized through Grafana dashboards.

## 🛠 Getting Started

### Prerequisites
- Docker & Docker Compose
- Anthropic API Key (Claude)

### Installation
1. Clone the repository.
2. Create a `.env` file in the root:
   ```env
   ANTHROPIC_API_KEY=your_key_here
   NEO4J_PASSWORD=password
   POSTGRES_PASSWORD=password
   ```
3. Spin up the infrastructure:
   ```bash
   docker-compose up --build
   ```
4. Access the platforms:
   - **Frontend**: `http://localhost:3000`
   - **API Docs**: `http://localhost:8000/docs`
   - **Grafana**: `http://localhost:3001` (Admin/admin)

## 🏗 Architecture Analysis
The project follows a clean, layered architecture:
- `api/routes`: RESTful endpoints with RBAC (analyst/admin roles).
- `services`: Business logic (Risk Engine, Ingestion Core, ERP Integration).
- `models`: Unified schemas for PG and Neo4j.
- `core`: Centralized configuration, security, and telemetry.

---
*Developed for High-Precision Supply Chain Intelligence.*
