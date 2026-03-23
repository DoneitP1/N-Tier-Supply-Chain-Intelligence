from fastapi import APIRouter, HTTPException, Depends, status
from core.database import db, logger
from core.security import RoleChecker

# RBAC Dependencies
analyst_or_admin = RoleChecker(["analyst", "admin"])

router = APIRouter(prefix="/api/stats", tags=["Dashboard Statistics"])

@router.get("", status_code=status.HTTP_200_OK, dependencies=[Depends(analyst_or_admin)], summary="Get dashboard summary stats", description="Calculates real-time supply chain health, total entities, and active risks for the dashboard.")
async def get_dashboard_stats():
    """
    Fetches real-time statistics for the dashboard.
    """
    try:
        # 1. Total Suppliers
        suppliers_query = "MATCH (s:Supplier) RETURN count(s) as count"
        suppliers_res = await db.execute_query(suppliers_query)
        total_suppliers = suppliers_res[0].get("count", 0) if suppliers_res else 0

        # 2. Total Parts
        parts_query = "MATCH (p:Part) RETURN count(p) as count"
        parts_res = await db.execute_query(parts_query)
        total_parts = parts_res[0].get("count", 0) if parts_res else 0

        # 3. Active Risks (High/Critical RiskEvents)
        risks_query = "MATCH (r:RiskEvent) WHERE r.severity IN ['High', 'Critical'] RETURN count(r) as count"
        risks_res = await db.execute_query(risks_query)
        active_risks = risks_res[0].get("count", 0) if risks_res else 0

        # 4. Supply Health (Calculated based on suppliers NOT impacted by active risks)
        # Formula: (Total Suppliers - Impacted Suppliers) / Total Suppliers
        impacted_query = """
        MATCH (s:Supplier)-[:IMPACTED_BY]->(r:RiskEvent)
        WHERE r.severity IN ['High', 'Critical']
        RETURN count(DISTINCT s) as count
        """
        impacted_res = await db.execute_query(impacted_query)
        impacted_suppliers = impacted_res[0].get("count", 0) if impacted_res else 0

        supply_health = 100.0
        if total_suppliers > 0:
            supply_health = ((total_suppliers - impacted_suppliers) / total_suppliers) * 100

        return {
            "total_suppliers": total_suppliers,
            "total_parts": total_parts,
            "active_risks": active_risks,
            "supply_health": round(supply_health, 1),
            "trends": {
                "suppliers": "+0%", # Placeholder for now as we don't track historical snapshots yet
                "parts": "+0%",
                "risks": "0",
                "health": "+0%"
            }
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard statistics.")

@router.get("/system", status_code=status.HTTP_200_OK, dependencies=[Depends(analyst_or_admin)], summary="Get system connectivity status", description="Returns health and connection status of PostgreSQL, Neo4j, and LLM.")
async def get_system_status():
    system_status = {
        "graph": "inactive",
        "postgres": "inactive",
        "llm": "inactive"
    }
    
    try:
        res = await db.execute_query("RETURN 1 as val")
        if res and res[0].get("val") == 1:
            system_status["graph"] = "active"
    except Exception:
        pass
        
    from core.postgres import engine
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            system_status["postgres"] = "active"
    except Exception:
        pass
        
    from core.config import settings
    # For LLM, if api key is provided and not placeholder
    if settings.google_api_key and settings.google_api_key != "placeholder":
        system_status["llm"] = "active"
    elif settings.anthropic_api_key and settings.anthropic_api_key != "placeholder" and settings.anthropic_api_key != "sk-ant-placeholder":
        system_status["llm"] = "active"
        
    return system_status
