import os
import shutil
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends
from models.schemas import ContractData, RawTextPayload, ERPBOMPayload, NewsRiskData
from core.database import db, logger
from core.config import settings
from fastapi.security import APIKeyHeader
from services.pdf_processor import process_pdf_and_extract
from services.news_monitor import extract_news_risk_via_llm
from services.erp_integration import ingest_erp_bom
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

# API Key Validation Dependency
api_key_header = APIKeyHeader(name="X-App-Api-Key", auto_error=True)

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.app_api_key:
        logger.warning(f"Unauthorized access attempt with key: {api_key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key

# Initialize LLM for local extraction
llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0, anthropic_api_key=settings.anthropic_api_key)

async def extract_contract_via_llm(raw_text: str) -> ContractData:
    system_prompt = """
You are an expert Supply Chain Data Extractor. Your job is to extract supplier information, parts details, and clauses from the provided contract text.

STRICT JSON REQUIREMENT: Output MUST exactly match the required schema. Do not include markdown formatting or conversational filler.
NO HALLUCINATIONS: If a specific data point is missing from the input text, set its value to null. Do not invent names, locations, or lead times.
CONFIDENCE SCORING: Calculate and attach a `confidence_score` (0.0 to 1.0) for every major entity extracted, based on the clarity and explicit nature of the text.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt.strip()),
        ("human", "Extract the supply chain data from the following contract text:\n\n{raw_text}")
    ])
    chain = prompt | llm.with_structured_output(ContractData)
    return await chain.ainvoke({"raw_text": raw_text})

@router.post("/process-contract", status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_api_key)])
async def process_contract(contract: ContractData):
    if contract.overall_extraction_confidence < 0.5:
        raise HTTPException(status_code=422, detail="Extraction confidence too low. Requires manual review.")

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
        logger.error(f"Error processing contract in Cypher: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-news", status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_api_key)])
async def process_news(news: NewsRiskData):
    if not news.event_classification.is_supply_chain_risk:
        return {"status": "ignored", "message": "Event classified as low/no supply chain risk."}
        
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
        logger.error(f"Error processing news in Cypher: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-pdf", status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_api_key)])
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
    temp_file_path = f"/tmp/{file.filename}"
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        contract_text = await process_pdf_and_extract(temp_file_path)
        extracted_data = await extract_contract_via_llm(contract_text)
        return await process_contract(extracted_data)
        
    except Exception as e:
        logger.error(f"Error uploading PDF: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.post("/analyze-raw-text", status_code=status.HTTP_200_OK, dependencies=[Depends(get_api_key)])
async def analyze_raw_text(payload: RawTextPayload):
    raw_text = payload.text.strip()
    if raw_text.startswith("[TYPE: CONTRACT_PDF]"):
        extracted_data = await extract_contract_via_llm(raw_text)
        return await process_contract(extracted_data)
    elif raw_text.startswith("[TYPE: NEWS_FEED]"):
        extracted_data = await extract_news_risk_via_llm(raw_text)
        return await process_news(extracted_data)
    else:
        raise HTTPException(status_code=400, detail="Unknown input format.")

@router.post("/erp-bom", status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_api_key)])
async def map_erp_bom(payload: ERPBOMPayload):
    try:
        return await ingest_erp_bom(payload, db_connection=db)
    except Exception as e:
        logger.error(f"Error ingesting ERP BOM: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
