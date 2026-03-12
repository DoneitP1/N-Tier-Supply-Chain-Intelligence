from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Pydantic Data Models ---
class Tier1Supplier(BaseModel):
    name: str = Field(..., description="Name of the Tier-1 supplier.")
    location: Optional[str] = Field(None, description="Location of the Tier-1 supplier.")

class Tier2Supplier(BaseModel):
    name: str = Field(..., description="Name of the Tier-2 supplier/subcontractor.")
    location: Optional[str] = Field(None, description="Location of the Tier-2 supplier.")
    critical_material: Optional[str] = Field(None, description="Raw material provided.")

class ERPBOMPayload(BaseModel):
    source: str = Field(..., description="Source system (e.g., SAP_ERP, ORACLE)")
    factory: str = Field(..., description="Main factory consuming the part")
    part_code: str = Field(..., description="The unified part code")
    tier_1_supplier: Tier1Supplier
    tier_2_supplier: Optional[Tier2Supplier] = None

# --- Ingestion Logic ---
async def ingest_erp_bom(payload: ERPBOMPayload, db_connection) -> Dict[str, Any]:
    """
    Ingests an ERP Bill of Materials payload directly into the Knowledge Graph.
    Uses Neo4j MERGE to ensure idempotency. Can map Tier-2 "invisible" suppliers
    conditionally if the data is present.
    """
    
    # We use Neo4j's FOREACH trick to conditionally execute MERGE statements based on 
    # whether a variable is NULL or not. This handles the optional Tier-2 data in a single transaction.
    cypher_query = """
    // 1. Map the Factory
    MERGE (f:Factory {name: $factory_name})
    ON CREATE SET f.last_updated = timestamp(), f.data_source = $source
    ON MATCH SET f.last_updated = timestamp()
    
    // 2. Map the Part
    MERGE (p:Part {code: $part_code})
    ON CREATE SET p.last_updated = timestamp()
    ON MATCH SET p.last_updated = timestamp()
    
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
        
    // Connect Factory -> Part -> Tier 1
    MERGE (f)-[:CONSUMES]->(p)
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
        "t1_name": payload.tier_1_supplier.name,
        "t1_location": payload.tier_1_supplier.location,
        "t2_name": payload.tier_2_supplier.name if payload.tier_2_supplier else None,
        "t2_location": payload.tier_2_supplier.location if payload.tier_2_supplier else None,
        "t2_material": payload.tier_2_supplier.critical_material if payload.tier_2_supplier else None,
    }
    
    await db_connection.execute_query(cypher_query, parameters)
    
    added_tier_2 = payload.tier_2_supplier is not None
    return {
        "status": "success",
        "message": f"ERP BOM ingested seamlessly. mapped Tier 1: {payload.tier_1_supplier.name}",
        "tier_2_mapped": added_tier_2
    }
