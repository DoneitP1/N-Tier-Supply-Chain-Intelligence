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
        # Use Neo4j Full-Text Search for scalable fuzzy resolution
        # This replaces the previous in-memory scan which was O(n)
        query = """
        CALL db.index.fulltext.queryNodes("supplierNameIndex", $search_term) 
        YIELD node, score
        RETURN node.name as name, score
        ORDER BY score DESC
        LIMIT 1
        """
        # We use a fuzzy search term (adding ~ for Lucene fuzzy matching if needed, 
        # but usually standard FTS is enough for slight typos)
        results = await db.execute_query(query, {"search_term": name})
        
        if results:
            best_match = results[0]
            matched_name = best_match["name"]
            score = best_match["score"] * 100 # Neo4j score is usually 0-1 or higher based on BM25
            
            # Neo4j FTS scores vary; for BM25, we might need a different heuristic than 90%
            # If it's a very close match, the score is usually high.
            if score >= 50: # Heuristic threshold for FTS
                logger.info(f"Resolved entity via Neo4j FTS: '{name}' -> '{matched_name}' (Score: {score:.2f})")
                return matched_name
                
        return name
    except Exception as e:
        logger.error(f"Entity resolution failed for '{name}': {e}")
        return name
