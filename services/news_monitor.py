import os
import asyncio
from typing import List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from core.config import settings
import feedparser
import logging

from core.prompt_loader import load_prompt

logger = logging.getLogger("ntier_news_monitor")

from models.schemas import NewsRiskData
from core.celery_app import celery_app
from core.database import db # For graph updates
from services.entity_resolution import resolve_supplier_name
from core.telemetry import track_llm_performance


def get_llm():
    """Lazy initialization of Gemini to prevent import-time crashes if API keys are missing."""
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", 
        temperature=0, 
        google_api_key=settings.google_api_key
    )

@track_llm_performance(provider="Gemini/Anthropic", task_type="NewsExtraction")
async def extract_news_risk_via_llm(news_text: str) -> NewsRiskData:
    """
    Evaluates news risk using Gemini 1.5 Flash via LangChain.
    """
    prompts = load_prompt("news_extraction")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompts["system_prompt"].strip()),
        ("human", prompts["human_prompt"].strip())
    ])
    
    llm = get_llm()
    chain = prompt | llm.with_structured_output(NewsRiskData)
    return await chain.ainvoke({"raw_text": news_text})

async def get_real_news() -> List[str]:
    """Fetches real-time supply chain news from Google News RSS."""
    url = "https://news.google.com/rss/search?q=supply+chain+disruption+OR+factory+strike+OR+material+shortage+OR+logistics+delay&hl=en-US&gl=US&ceid=US:en"
    
    # Run feedparser in a thread since it's synchronous block
    feed = await asyncio.to_thread(feedparser.parse, url)
    
    news_items = []
    # Take top 5 recent news to process to avoid rate limits
    for entry in feed.entries[:5]:
        news_items.append(entry.title)
        
    return news_items

@celery_app.task(name="services.news_monitor.poll_news_task")
def poll_news_task():
    """
    Celery wrapper for news polling.
    Runs the async logic in the event loop.
    """
    return asyncio.run(poll_news_and_analyze())

async def poll_news_and_analyze():
    """
    Runs in the background, fetching real news from Google RSS,
    runs the free LLM unstructured parsing, and only updates Neo4j if Critical/High.
    """
    logger.info("Starting asynchronous news polling...")
    
    try:
        news_list = await get_real_news()
    except Exception as e:
        logger.error(f"Failed to fetch RSS news: {e}", exc_info=True)
        return
        
    if not news_list:
        logger.info("No news found in RSS feed.")
        return
    
    for news in news_list:
        try:
            logger.info(f"Analyzing: {news}")
            extracted_data = await extract_news_risk_via_llm(news)
            
            if extracted_data.event_classification.is_supply_chain_risk:
                severity = extracted_data.event_classification.severity
                
                # Threshold Logic: Execute Cypher ONLY if High or Critical
                if severity in ["High", "Critical"]:
                    logger.warning(f"Threat Detected! Severity: {severity}. Flagging Knowledge Graph...")
                    
                    # Entity Resolution for affected entities
                    resolved_entities = []
                    for entity in extracted_data.impact_details.entities_affected:
                        resolved_entity = await resolve_supplier_name(entity)
                        resolved_entities.append(resolved_entity)
                    
                    cypher_query = """
                    UNWIND $locations AS affected_loc
                    MATCH (s:Supplier)
                    WHERE s.location CONTAINS affected_loc OR s.name IN $resolved_entities
                    
                    MERGE (r:RiskEvent {type: $event_type, summary: $summary, severity: $severity})
                    MERGE (s)-[im:IMPACTED_BY {timestamp: timestamp()}]->(r)
                    RETURN count(s) as impacted_suppliers
                    """
                    parameters = {
                        "locations": extracted_data.impact_details.locations_affected,
                        "resolved_entities": resolved_entities,
                        "event_type": extracted_data.event_classification.event_type,
                        "severity": severity,
                        "summary": extracted_data.summary
                    }
                    
                    result = await db.execute_query(cypher_query, parameters)
                    impacted = result[0]['impacted_suppliers'] if result else 0
                    logger.info(f"Successfully logged to DB. Impacted {impacted} mapped supplier(s).")
                else:
                    logger.info(f"Risk is {severity}. Ignoring to avoid DB noise.")
            else:
                logger.info("No supply chain risk detected.")
                
            # Sleep to respect free-tier API rate limits
            await asyncio.sleep(2)
            
        except Exception as e:
            # Gracefully handle API limits or timeouts without crashing the daemon
            logger.error(f"Error analyzing news block: {e}", exc_info=True)
            await asyncio.sleep(2)
