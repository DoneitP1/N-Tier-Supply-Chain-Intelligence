from typing import Dict, Any
from models.schemas import ERPBOMPayload, TokenData

# --- Ingestion Logic ---
async def ingest_erp_bom(payload: ERPBOMPayload, db_sql, current_user: TokenData) -> Dict[str, Any]:
    """
    Refactored to use the Outbox Pattern for consistency.
    """
    from core.outbox import push_to_outbox
    
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
    
    await push_to_outbox(db_sql, "sync_erp_bom", parameters)
    
    return {
        "status": "success",
        "message": f"ERP BOM queued for Knowledge Graph sync. mapped Tier 1: {payload.tier_1_supplier.name}",
    }
