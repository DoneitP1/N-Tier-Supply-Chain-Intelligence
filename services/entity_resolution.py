from rapidfuzz import process, fuzz
from core.database import db
import logging

logger = logging.getLogger("ntier_entity_resolution")

async def resolve_supplier_name(name: str, threshold: float = 90.0) -> str:
    """
    Checks the Neo4j Knowledge Graph for existing suppliers with similar names.
    Returns the resolved (existing) name if a match is found above the threshold.
    Otherwise returns the original name.
    """
    try:
        # Fetch all existing supplier names from Neo4j
        # In a massive graph, we'd use a search index or vector search
        # For this scale, a simple scan is fine
        query = "MATCH (s:Supplier) RETURN s.name as name"
        results = await db.execute_query(query)
        existing_names = [r["name"] for r in results]
        
        if not existing_names:
            return name
            
        # Perform fuzzy matching
        match = process.extractOne(name, existing_names, scorer=fuzz.WRatio)
        
        if match:
            matched_name, score, _ = match
            if score >= threshold:
                logger.info(f"Resolved entity: '{name}' -> '{matched_name}' (Confidence: {score}%)")
                return matched_name
                
        return name
    except Exception as e:
        logger.error(f"Entity resolution failed for '{name}': {e}")
        return name
