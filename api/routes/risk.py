from typing import List, Union, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from models.schemas import RiskSimulationRequest, RiskSimulationResult, TokenData
from services.risk_engine import simulate_risk_propagation
from core.database import db, logger
from core.security import RoleChecker, get_current_user

# RBAC Dependencies
analyst_or_admin = RoleChecker(["analyst", "admin"])

router = APIRouter(prefix="/api/risk", tags=["Risk Simulation"])

@router.post("/simulate", status_code=status.HTTP_200_OK, response_model=RiskSimulationResult, dependencies=[Depends(analyst_or_admin)], summary="Simulate supply chain risk", description="Performs recursive traversal from an impacted supplier to detect bottlenecks and cascading factory impacts.")
async def simulate_risk(payload: RiskSimulationRequest):
    """
    Simulates risk propagation through the Knowledge Graph.
    Aggregates cascading impact depth, total nodes, factories, and weakest links.
    """
    try:
        result = await simulate_risk_propagation(
            supplier_name=payload.supplier_name,
            crisis_duration_days=payload.duration_days,
            db_connection=db
        )
        
        if result is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Supplier '{payload.supplier_name}' not found in the Knowledge Graph."
            )
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing risk simulation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
