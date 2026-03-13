from typing import List
from models.schemas import RiskSimulationResult

async def simulate_risk_propagation(supplier_name: str, crisis_duration_days: int, db_connection) -> List[RiskSimulationResult]:
    """
    Simulates the risk propagation from an impacted supplier up to the parts they supply
    (and potentially to the Factory if mapped in the Knowledge Graph).
    """

    # Cypher Query Logic:
    # 1. MATCH the target Supplier by name. We use a parameterized query to prevent injections.
    # 2. Traverse the [:SUPPLIES] relationship to find the connected Part nodes.
    # 3. Use OPTIONAL MATCH to find any Factory producing those parts (simulating the full path).
    # 4. Extract required edge properties (min stock, lead time, alt supplier, daily consumption) to evaluate the math.
    query = """
    MATCH (s:Supplier {name: $supplier_name})
    OPTIONAL MATCH (s)-[rel:SUPPLIES]->(p:Part)
    OPTIONAL MATCH (p)<-[con:CONSUMES]-(f:Factory)
    RETURN 
        s.name AS supplier_name,
        p.code AS part_code,
        f.name AS factory_name,
        rel.minimum_stock_units AS minimum_stock_units,
        rel.lead_time_days AS lead_time_days,
        rel.alt_supplier_allowed AS alt_supplier_allowed,
        con.daily_consumption AS daily_consumption
    """
    
    results = await db_connection.execute_query(query, {"supplier_name": supplier_name})
    
    # If the supplier isn't found, return None so the router can throw a 404 cleanly
    if not results:
        return None
        
    simulations = []
    
    for row in results:
        supplier = row.get("supplier_name")
        part = row.get("part_code")
        factory = row.get("factory_name") or "Factory (Not Mapped)"
        
        # If the supplier exists but has no supplies relationships mapped yet
        if not part:
            simulations.append(RiskSimulationResult(
                impacted_paths=[f"Supplier: {supplier}"],
                days_to_line_stoppage="Unknown",
                risk_score="Low",
                recommendations="Supplier has no associated parts mapped in the Knowledge Graph. Risk isolated."
            ))
            continue
            
        path = [f"Supplier: {supplier}", f"Part: {part}", f"Factory: {factory}"]
        
        min_stock = row.get("minimum_stock_units")
        lead_time = row.get("lead_time_days")
        alt_supplier = row.get("alt_supplier_allowed", False)
        daily_consumption = row.get("daily_consumption")
        
        # Mathematical Accuracy: Days to Line Stoppage = Current Stock / Daily Consumption
        if min_stock is None or daily_consumption is None or daily_consumption <= 0:
            days_to_stoppage = "Unknown"
        else:
            try:
                days_to_stoppage = round(min_stock / daily_consumption, 1)
            except (ZeroDivisionError, TypeError):
                days_to_stoppage = "Unknown"
                
        # Risk scoring logic:
        # High if stoppage days < lead time and no alternative supplier exists; Low otherwise.
        if isinstance(days_to_stoppage, (int, float)) and lead_time is not None:
            if days_to_stoppage < lead_time and not alt_supplier:
                risk_score = "High"
                recommendations = (f"CRITICAL: Line stoppage in {days_to_stoppage} days "
                                   f"(Lead time {lead_time} days). No alt supplier allowed. "
                                   "Expedite sourcing immediately.")
            elif days_to_stoppage < lead_time and alt_supplier:
                risk_score = "Medium"
                recommendations = (f"Line stoppage in {days_to_stoppage} days "
                                   f"(Lead time {lead_time} days). Alt supplier ALLOWED. "
                                   "Activate alternative supplier protocol immediately.")
            else:
                risk_score = "Low"
                recommendations = (f"Stock level covers lead time "
                                   f"({days_to_stoppage} days / {lead_time} days lead). "
                                   "Monitor closely.")
        else:
            risk_score = "Medium"
            recommendations = "Lead time or stock data missing. Manual risk assessment required."
            
        # Additional contextual risk factor utilizing crisis_duration payload
        if isinstance(days_to_stoppage, (int, float)) and crisis_duration_days > days_to_stoppage and risk_score != "High":
            if not alt_supplier:
                 risk_score = "High"
                 recommendations += f" UPDATE: Crisis duration ({crisis_duration_days} days) exceeds stock."

        simulations.append(RiskSimulationResult(
            impacted_paths=path,
            days_to_line_stoppage=days_to_stoppage,
            risk_score=risk_score,
            recommendations=recommendations
        ))
        
    return simulations
