# N-Tier Supply Chain Intelligence Platform

This MVP repository implements the "N-Tier Supply Chain Intelligence" platform designed for the Bursa Automotive Pilot. The application utilizes a FastAPI backend powered by LangChain and Neo4j for N-Tier Knowledge Graph mapping, and features an interactive Streamlit UI for risk monitoring and graph visualization.

## Core Features
- **Contract Ingestion (LLM)**: Automated chunking and parsing of unstructured PDF contracts using an LLM (Claude Sonnet / Gemini) into structured JSON.
- **ERP Integration**: Synchronous injection of structured ERP/Customs Bill of Materials data directly into the Knowledge Graph bypassing LLMs.
- **Background News Monitoring**: Asynchronous real-time news evaluation highlighting high/critical supply chain risks continuously running on background tasks.
- **Risk Propagation Engine**: Multi-hop path traversal simulation calculating days to "Line Stoppage" propagating risks from lower tier suppliers to main factories.
- **Interactive Graph Visualization**: Frontend UI presenting a physics-based relational Knowledge Graph rendered dynamically using `streamlit-agraph`.

## Technology Stack
- **Backend**: FastAPI, Neo4j Async Driver, LangChain, Pydantic, Python 3.12+
- **Frontend**: Streamlit, Streamlit AGraph
- **AI/LLM**: Anthropic Claude-3, Google Gemini 1.5 Flash (Free Tier monitoring)

## Running the Application
### Backend (FastAPI + Neo4j)
1. Set up a local Neo4j desktop instance or AuraDB.
2. Ensure you have activated your virtual environment containing all required modules.
3. Start the engine from the root directory:
```bash
uvicorn main:app --reload
```

### Frontend (Streamlit)
Start the frontend interface in a separate terminal window:
```bash
streamlit run app.py
```
