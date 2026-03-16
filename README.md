# N-Tier Supply Chain Intelligence Platform

This platform implements the "N-Tier Supply Chain Intelligence" system designed for the Bursa Automotive Pilot. The application utilizes a FastAPI backend powered by LangChain and Neo4j for N-Tier Knowledge Graph mapping, and features a modern Next.js frontend for risk monitoring and graph visualization.

## Core Features
- **Contract Ingestion (LLM)**: Automated chunking and parsing of unstructured PDF contracts using an LLM (Claude Sonnet / Gemini) into structured JSON.
- **ERP Integration**: Synchronous injection of structured ERP/Customs Bill of Materials data directly into the Knowledge Graph bypassing LLMs.
- **Background News Monitoring**: Asynchronous real-time news evaluation highlighting high/critical supply chain risks continuously running on background tasks.
- **Risk Propagation Engine**: Multi-hop path traversal simulation calculating days to "Line Stoppage" propagating risks from lower tier suppliers to main factories.
- **Interactive Graph Visualization**: Premium Next.js frontend UI presenting a physics-based relational Knowledge Graph rendered dynamically using ReactFlow.

## Technology Stack
- **Backend**: FastAPI, Neo4j Async Driver, LangChain, Pydantic, Python 3.12+
- **Frontend**: Next.js 15, ReactFlow, TailwindCSS, Lucide React
- **AI/LLM**: Anthropic Claude-3, Google Gemini 1.5 Flash (Free Tier monitoring)

## Running the Application

Ensure you have a local Neo4j desktop instance or AuraDB set up.

### Backend (FastAPI)
1. Ensure you have activated your virtual environment.
2. Start the engine from the root directory:
```bash
uvicorn main:app --reload
```

### Frontend (Next.js)
Start the modern dashboard interface:
```bash
cd frontend
npm run dev
```

### Legacy Interface (Streamlit)
For internal prototyping purposes only:
```bash
streamlit run app.py
```
