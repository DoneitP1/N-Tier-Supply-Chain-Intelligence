from typing import Dict, Any
from models.schemas import ERPBOMPayload, TokenData

# --- Ingestion Logic ---
async def ingest_erp_bom(payload: ERPBOMPayload, db_connection, current_user: TokenData) -> Dict[str, Any]:
    """
    Ingests an ERP Bill of Materials payload directly into the Knowledge Graph.
    Uses Neo4j MERGE to ensure idempotency. Can map Tier-2 "invisible" suppliers
    conditionally if the data is present.
    """
    
    # We use Neo4j's FOREACH trick to conditionally execute MERGE statements based on 
    # whether a variable is NULL or not. This handles the optional Tier-2 data in a single transaction.
    cypher_query = """
    MERGE (u:User {username: $username})
    // 1. Map the Factory
    MERGE (f:Factory {name: $factory_name})
    ON CREATE SET f.last_updated = timestamp(), f.data_source = $source
    ON MATCH SET f.last_updated = timestamp()
    MERGE (f)-[:CREATED_BY]->(u)
    
    // 2. Map the Part
    MERGE (p:Part {code: $part_code})
    ON CREATE SET p.last_updated = timestamp()
    ON MATCH SET p.last_updated = timestamp()
    MERGE (p)-[:CREATED_BY]->(u)
    
    // 3. Map the Tier-1 Supplier
    MERGE (t1:Supplier {name: $t1_name})
    ON CREATE SET 
        t1.location = $t1_location, 
        t1.tier = 1,
        t1.last_updated = timestamp(), 
        t1.data_source = $source
    ON MATCH SET 
        t1.location = coalesce($t1_location, t1.location), 
        t1.last_updated = timestamp()
    MERGE (t1)-[:CREATED_BY]->(u)
        
    // Connect Factory -> Part -> Tier 1
    MERGE (f)-[con:CONSUMES]->(p)
    ON CREATE SET con.daily_consumption = $daily_consumption, con.last_updated = timestamp()
    ON MATCH SET con.daily_consumption = coalesce($daily_consumption, con.daily_consumption), con.last_updated = timestamp()
    
    MERGE (t1)-[:SUPPLIES]->(p)
    
    // 4. Conditionally Map Tier-2 Supplier (if provided)
    FOREACH (ignoreMe IN CASE WHEN $t2_name IS NOT NULL THEN [1] ELSE [] END |
        MERGE (t2:Supplier {name: $t2_name})
        ON CREATE SET 
            t2.location = coalesce($t2_location, t2.location), 
            t2.tier = 2,
            t2.last_updated = timestamp(), 
            t2.data_source = $source
        ON MATCH SET 
            t2.location = coalesce($t2_location, t2.location), 
            t2.last_updated = timestamp()
        MERGE (t2)-[:CREATED_BY]->(u)
            
        MERGE (t2)-[rel:SUPPLIES_MATERIAL]->(t1)
        ON CREATE SET 
            rel.material = $t2_material, 
            rel.last_updated = timestamp()
        ON MATCH SET 
            rel.material = coalesce($t2_material, rel.material), 
            rel.last_updated = timestamp()
    )
    """
    
    parameters = {
        "source": payload.source,
        "factory_name": payload.factory,
        "part_code": payload.part_code,
        "daily_consumption": payload.daily_consumption_units,
        "t1_name": payload.tier_1_supplier.name,
        "t1_location": payload.tier_1_supplier.location,
        "t2_name": payload.tier_2_supplier.name if payload.tier_2_supplier else None,
        "t2_location": payload.tier_2_supplier.location if payload.tier_2_supplier else None,
        "t2_material": payload.tier_2_supplier.critical_material if payload.tier_2_supplier else None,
        "username": current_user.username,
    }
    
    await db_connection.execute_query(cypher_query, parameters)
    
    added_tier_2 = payload.tier_2_supplier is not None
    return {
        "status": "success",
        "message": f"ERP BOM ingested seamlessly. mapped Tier 1: {payload.tier_1_supplier.name}",
        "tier_2_mapped": added_tier_2
    }
