import os
import asyncio
from typing import List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# --- Data Models (Moved here to centralize News Risk schemas) ---
class EventClassification(BaseModel):
    is_supply_chain_risk: bool
    event_type: str = Field(..., description="e.g., Natural Disaster, Geopolitical")
    severity: str = Field(..., description="Low, Medium, High, Critical")
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class ImpactDetails(BaseModel):
    locations_affected: List[str]
    entities_affected: List[str]
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class NewsRiskData(BaseModel):
    document_type: str = "news_risk"
    event_classification: EventClassification
    impact_details: ImpactDetails
    summary: str
    overall_assessment_confidence: float = Field(..., ge=0.0, le=1.0)


# Initialize the free LLM for background tasks (using Gemini 1.5 Flash)
# Ensure GOOGLE_API_KEY is in your environment variables.
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

async def extract_news_risk_via_llm(raw_text: str) -> NewsRiskData:
    """
    Evaluates news risk using Gemini 1.5 Flash via LangChain.
    """
    system_prompt = """
You are a Supply Chain Risk Assessor. Your job is to evaluate news feeds for direct or indirect supply chain risks.

STRICT JSON REQUIREMENT: Output MUST exactly match the required schema. Do not include markdown formatting or conversational filler.
NO HALLUCINATIONS: Extract only facts presented in the text.
CONFIDENCE SCORING: Provide a `confidence_score` (0.0 to 1.0) for your assessments based on the explicit nature of the text.
Evaluate the severity level (Low, Medium, High, Critical) and identify affected locations and entities.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt.strip()),
        ("human", "Evaluate the supply chain risk from the following news text:\n\n{raw_text}")
    ])
    
    chain = prompt | llm.with_structured_output(NewsRiskData)
    return await chain.ainvoke({"raw_text": raw_text})

async def poll_news_and_analyze(db_connection):
    """
    Runs in the background, simulating a news stream. Loops through items,
    runs the free LLM unstructured parsing, and only updates Neo4j if Critical/High.
    """
    mock_news = [
        "A massive 7.2 earthquake hit Taiwan, disrupting major semiconductor factories across the island.",
        "Minor port strike in Hamburg resolved after one day of negotiations.",
        "Severe flooding in Bursa industrial zone caused power outages at Katman-1 Bursa Auto Parts Ltd.",
        "New trade agreement signed between Turkey and EU, reducing tariffs on electronics."
    ]
    
    print("[News Monitor] Starting asynchronous news polling...")
    
    for news in mock_news:
        try:
            print(f"\n[News Monitor] Analyzing: {news}")
            extracted_data = await extract_news_risk_via_llm(news)
            
            if extracted_data.event_classification.is_supply_chain_risk:
                severity = extracted_data.event_classification.severity
                
                # Threshold Logic: Execute Cypher ONLY if High or Critical
                if severity in ["High", "Critical"]:
                    print(f"[News Monitor] ⚠️ Threat Detected! Severity: {severity}. Flagging Knowledge Graph...")
                    
                    cypher_query = """
                    UNWIND $locations AS affected_loc
                    MATCH (s:Supplier)
                    WHERE s.location CONTAINS affected_loc OR s.name IN $entities
                    
                    MERGE (r:RiskEvent {type: $event_type, summary: $summary, severity: $severity})
                    MERGE (s)-[im:IMPACTED_BY {timestamp: timestamp()}]->(r)
                    RETURN count(s) as impacted_suppliers
                    """
                    parameters = {
                        "locations": extracted_data.impact_details.locations_affected,
                        "entities": extracted_data.impact_details.entities_affected,
                        "event_type": extracted_data.event_classification.event_type,
                        "severity": severity,
                        "summary": extracted_data.summary
                    }
                    
                    result = await db_connection.execute_query(cypher_query, parameters)
                    impacted = result[0]['impacted_suppliers'] if result else 0
                    print(f"[News Monitor] 🔥 Successfully logged to DB. Impacted {impacted} mapped supplier(s).")
                else:
                    print(f"[News Monitor] Risk is {severity}. Ignoring to avoid DB noise.")
            else:
                print(f"[News Monitor] No supply chain risk detected.")
                
            # Sleep to respect free-tier API rate limits
            await asyncio.sleep(2)
            
        except Exception as e:
            # Gracefully handle API limits or timeouts without crashing the daemon
            print(f"[News Monitor] Error analyzing news block: {e}")
            await asyncio.sleep(2)
