from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from models.schemas import RiskSimulationRequest, RiskSimulationResult
from services.risk_engine import simulate_risk_propagation
from core.database import db, logger
from core.security import RoleChecker

# RBAC Dependencies
analyst_or_admin = RoleChecker(["analyst", "admin"])

router = APIRouter(prefix="/api/risk", tags=["Risk Simulation"])

@router.post("/simulate", status_code=status.HTTP_200_OK, response_model=List[RiskSimulationResult], dependencies=[Depends(analyst_or_admin)])
async def simulate_risk(payload: RiskSimulationRequest):
    """
    Simulates risk propagation through the Knowledge Graph.
    Finds paths from an impacted supplier up to the associated parts/factory,
    calculates Line Stoppage, and assigns a Risk Score.
    """
    try:
        results = await simulate_risk_propagation(
            supplier_name=payload.impacted_supplier_name,
            crisis_duration_days=payload.crisis_duration_days,
            db_connection=db
        )
        
        if results is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Supplier '{payload.impacted_supplier_name}' not found in the Knowledge Graph."
            )
            
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing risk simulation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
