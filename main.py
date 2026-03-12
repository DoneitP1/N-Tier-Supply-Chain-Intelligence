import os
import shutil
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from neo4j import AsyncGraphDatabase
import uvicorn
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pdf_processor import process_pdf_and_extract
from risk_engine import RiskSimulationRequest, RiskSimulationResult, simulate_risk_propagation
from erp_integration import ERPBOMPayload, ingest_erp_bom
from news_monitor import poll_news_and_analyze, extract_news_risk_via_llm, NewsRiskData

# ==========================================
# 1. DATABASE CONNECTION (Neo4j)
# ==========================================
class Neo4jConnection:
    """Singleton-style database connection manager."""
    def __init__(self, uri, user, pwd):
        # Using async driver for FastAPI compatibility and performance
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, pwd))
    
    async def close(self):
        if self._driver is not None:
            await self._driver.close()
    
    async def execute_query(self, query, parameters=None):
        """Standardized method to execute write/read queries."""
        async with self._driver.session() as session:
            result = await session.run(query, parameters)
            return await result.data()

# Inject credentials from environment or use defaults for local dev
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

db = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure db is accessible
    yield
    # Shutdown: clean up db connection
    await db.close()

app = FastAPI(
    title="N-Tier Supply Chain Intelligence API",
    description="Knowledge Graph ingestion and risk analysis endpoints.",
    version="1.0.0",
    lifespan=lifespan
)

# ==========================================
# 2. DATA MODELS (Pydantic / JSON Schema)
# ==========================================

# -- Contract Models --
class SupplierInfo(BaseModel):
    name: str = Field(..., description="Name of the supplier or factory.")
    location: Optional[str] = Field(None, description="Physical location of the supplier.")
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class PartInfo(BaseModel):
    part_code: str
    lead_time_days: Optional[int] = None
    minimum_stock_units: Optional[int] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class ClauseInfo(BaseModel):
    force_majeure_present: bool
    force_majeure_details: Optional[str] = None
    alternative_supplier_allowed: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class ContractData(BaseModel):
    document_type: str = "contract"
    supplier: SupplierInfo
    parts: List[PartInfo]
    clauses: ClauseInfo
    overall_extraction_confidence: float = Field(..., ge=0.0, le=1.0)

# ==========================================
# 3. LLM ENGINE (LangChain & Claude Sonnet)
# ==========================================

# Initialize the ChatAnthropic model. 
# Ensure ANTHROPIC_API_KEY is set in your environment variables.
llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0)

async def extract_contract_via_llm(raw_text: str) -> ContractData:
    """
    Uses Claude Sonnet via LangChain to extract contract details matching the Pydantic schema.
    """
    system_prompt = """
You are an expert Supply Chain Data Extractor. Your job is to extract supplier information, parts details, and clauses from the provided contract text.

STRICT JSON REQUIREMENT: Output MUST exactly match the required schema. Do not include markdown formatting or conversational filler.
NO HALLUCINATIONS: If a specific data point is missing from the input text, set its value to null. Do not invent names, locations, or lead times.
CONFIDENCE SCORING: Calculate and attach a `confidence_score` (0.0 to 1.0) for every major entity extracted, based on the clarity and explicit nature of the text.
If a contract clause is highly ambiguous, extract the raw text snippet, but drop the `confidence_score` below 0.5.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt.strip()),
        ("human", "Extract the supply chain data from the following contract text:\n\n{raw_text}")
    ])
    
    # Bind the Pydantic model directly to the LLM to enforce the schema
    chain = prompt | llm.with_structured_output(ContractData)
    return await chain.ainvoke({"raw_text": raw_text})

# ==========================================
# 4. API ENDPOINTS
# ==========================================

@app.post("/process-contract", status_code=status.HTTP_201_CREATED)
async def process_contract(contract: ContractData):
    """
    Accepts parsed contract JSON and maps it into the Neo4j Knowledge Graph.
    Ontology: (Factory)-[PRODUCES]->(Part)<-[SUPPLIES]-(Supplier)
    Since we often treat Supplier and Factory interchangeably in simpler models,
    we map the Supplier node, the Part node, and the relationship between them.
    """
    
    # Check if confidence is high enough to ingest automatically
    if contract.overall_extraction_confidence < 0.5:
        # Route to a human-in-the-loop queue in a real system
        raise HTTPException(
            status_code=422, 
            detail="Extraction confidence too low. Requires manual review."
        )

    # Cypher Query Logic:
    # MERGE creates nodes/relationships if they don't exist, matches them if they do.
    cypher_query = """
    MERGE (s:Supplier {name: $supplier_name})
    ON CREATE SET s.location = $location, s.last_updated = timestamp()
    ON MATCH SET s.location = coalesce($location, s.location), s.last_updated = timestamp()
    
    WITH s
    UNWIND $parts AS part_data
    MERGE (p:Part {code: part_data.part_code})
    
    MERGE (s)-[rel:SUPPLIES]->(p)
    ON CREATE SET 
        rel.lead_time_days = part_data.lead_time_days,
        rel.minimum_stock_units = part_data.minimum_stock_units,
        rel.force_majeure = $force_majeure,
        rel.alt_supplier_allowed = $alt_supplier
    ON MATCH SET
        rel.lead_time_days = coalesce(part_data.lead_time_days, rel.lead_time_days),
        rel.minimum_stock_units = coalesce(part_data.minimum_stock_units, rel.minimum_stock_units)
    """
    
    parameters = {
        "supplier_name": contract.supplier.name,
        "location": contract.supplier.location,
        "parts": [p.model_dump() for p in contract.parts],
        "force_majeure": contract.clauses.force_majeure_present,
        "alt_supplier": contract.clauses.alternative_supplier_allowed
    }
    
    try:
        await db.execute_query(cypher_query, parameters)
        return {"status": "success", "message": f"Contract for {contract.supplier.name} mapped to Knowledge Graph."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-news", status_code=status.HTTP_201_CREATED)
async def process_news(news: NewsRiskData):
    """
    Accepts news risk assessment data.
    If it's a valid supply chain risk, it flags impacted Suppliers or Locations in Neo4j.
    """
    if not news.event_classification.is_supply_chain_risk:
        return {"status": "ignored", "message": "Event classified as low/no supply chain risk."}
        
    # Example Cypher: Flag any suppliers in the affected locations, or exact matched entities
    cypher_query = """
    UNWIND $locations AS affected_loc
    MATCH (s:Supplier)
    WHERE s.location CONTAINS affected_loc OR s.name IN $entities
    
    MERGE (r:RiskEvent {type: $event_type, summary: $summary, severity: $severity})
    MERGE (s)-[im:IMPACTED_BY {timestamp: timestamp()}]->(r)
    RETURN count(s) as impacted_suppliers
    """
    
    parameters = {
        "locations": news.impact_details.locations_affected,
        "entities": news.impact_details.entities_affected,
        "event_type": news.event_classification.event_type,
        "severity": news.event_classification.severity,
        "summary": news.summary
    }
    
    try:
        result = await db.execute_query(cypher_query, parameters)
        impacted_count = result[0]['impacted_suppliers'] if result else 0
        return {
            "status": "success", 
            "message": f"Risk logged. Impacted {impacted_count} suppliers in the graph.",
            "severity": news.event_classification.severity
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RawTextPayload(BaseModel):
    text: str = Field(..., description="Raw text prefixed with [TYPE: CONTRACT_PDF] or [TYPE: NEWS_FEED]")

@app.post("/upload-pdf/", status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Saves an uploaded PDF contract, processes it with LangChain, 
    extracts data via our LLM engine, and ingests it into Neo4j.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
    temp_file_path = f"/tmp/{file.filename}"
    
    try:
        # Save the uploaded file temporarily
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Read and chunk the PDF
        contract_text = await process_pdf_and_extract(temp_file_path)
        
        # 2. Extract structured data using existing LLM logic
        extracted_data = await extract_contract_via_llm(contract_text)
        
        # 3. Ingest into Neo4j
        return await process_contract(extracted_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/analyze-raw-text", status_code=status.HTTP_200_OK)
async def analyze_raw_text(payload: RawTextPayload):
    """
    Accepts raw text, determines the type based on the prefix tag, 
    extracts structured data via Claude Sonnet, and ingests it into Neo4j.
    """
    raw_text = payload.text.strip()
    
    if raw_text.startswith("[TYPE: CONTRACT_PDF]"):
        # 1. Extract using LLM
        extracted_data = await extract_contract_via_llm(raw_text)
        # 2. Ingest to Neo4j
        return await process_contract(extracted_data)
        
    elif raw_text.startswith("[TYPE: NEWS_FEED]"):
        # 1. Extract using LLM
        extracted_data = await extract_news_risk_via_llm(raw_text)
        # 2. Ingest to Neo4j
        return await process_news(extracted_data)
        
    else:
        raise HTTPException(
            status_code=400, 
            detail="Unknown input format. Text must start with [TYPE: CONTRACT_PDF] or [TYPE: NEWS_FEED]"
        )

@app.get("/api/graph-data", status_code=status.HTTP_200_OK)
async def get_graph_data():
    """
    Fetches the entire Knowledge Graph nodes and edges for visualization.
    Uses id() to safely extract Neo4j internal node IDs and properties.
    """
    query = """
    MATCH (n)-[r]->(m)
    RETURN 
        id(n) AS n_id, labels(n)[0] AS n_label, coalesce(n.name, n.code, n.type, "Unknown") AS n_name,
        id(m) AS m_id, labels(m)[0] AS m_label, coalesce(m.name, m.code, m.type, "Unknown") AS m_name,
        type(r) AS r_type
    """
    try:
        results = await db.execute_query(query)
        nodes_dict = {}
        edges = []
        
        for row in results:
            n_id = row.get("n_id")
            m_id = row.get("m_id")
            
            if n_id not in nodes_dict:
                nodes_dict[n_id] = {
                    "id": n_id,
                    "label": row.get("n_label", "Unknown"),
                    "name": row.get("n_name", "Unknown")
                }
                
            if m_id not in nodes_dict:
                nodes_dict[m_id] = {
                    "id": m_id,
                    "label": row.get("m_label", "Unknown"),
                    "name": row.get("m_name", "Unknown")
                }
                
            edges.append({
                "source": n_id,
                "target": m_id,
                "type": row.get("r_type", "RELATED")
            })
            
        return {"nodes": list(nodes_dict.values()), "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest-erp-bom/", status_code=status.HTTP_201_CREATED)
async def map_erp_bom(payload: ERPBOMPayload):
    """
    Ingests structured JSON data bypassing the LLM directly into Neo4j.
    Handles Multi-Tier structured representation mappings.
    """
    try:
        return await ingest_erp_bom(payload, db_connection=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start-news-monitor/")
async def start_news_monitor(background_tasks: BackgroundTasks):
    """
    Triggers the background task to poll the news stream asynchronously.
    """
    background_tasks.add_task(poll_news_and_analyze, db)
    return {"status": "success", "message": "News monitor started in the background."}

@app.post("/simulate-risk/", status_code=status.HTTP_200_OK, response_model=List[RiskSimulationResult])
async def simulate_risk(payload: RiskSimulationRequest):
    """
    Simulates risk propagation through the Knowledge Graph.
    Finds paths from an impacted supplier up to the associated parts/factory,
    calculates Line Stoppage, and assigns a Risk Score.
    """
    results = await simulate_risk_propagation(
        supplier_name=payload.impacted_supplier_name,
        crisis_duration_days=payload.crisis_duration_days,
        db_connection=db
    )
    
    if results is None:
        raise HTTPException(
            status_code=404, 
            detail=f"Supplier '{payload.impacted_supplier_name}' not found in the Knowledge Graph."
        )
        
    return results

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
