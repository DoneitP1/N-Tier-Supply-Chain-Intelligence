from typing import List
from models.schemas import RiskSimulationResult

async def simulate_risk_propagation(supplier_name: str, crisis_duration_days: int, db_connection) -> List[RiskSimulationResult]:
    """
    Simulates recursive risk propagation across N-Tier supplier paths.
    Traverses from the impacted supplier through any number of sub-suppliers
    until reaching a Part consumed by a Factory.
    """

    # Recursive Cypher Query Logic:
    # 1. MATCH the target Supplier.
    # 2. Use variable-length path [:SUPPLIES*] to find all downstream impacts.
    # 3. Terminate at (p:Part) which is consumed by (f:Factory).
    query = """
    MATCH path = (s:Supplier {name: $supplier_name})-[:SUPPLIES*1..5]->(p:Part)
    OPTIONAL MATCH (p)<-[con:CONSUMES]-(f:Factory)
    RETURN 
        nodes(path) AS path_nodes,
        relationships(path) AS path_rels,
        f.name AS factory_name,
        con.daily_consumption AS daily_consumption
    """
    
    results = await db_connection.execute_query(query, {"supplier_name": supplier_name})
    
    if not results:
        return None
        
    simulations = []
    
    for row in results:
        path_nodes = row.get("path_nodes", [])
        path_rels = row.get("path_rels", [])
        factory = row.get("factory_name") or "Factory (Not Mapped)"
        daily_consumption = row.get("daily_consumption")
        
        # Build human-readable path and calculate depth
        formatted_path = []
        for node in path_nodes:
            label = list(node.labels)[0] if node.labels else "Unknown"
            formatted_path.append(f"{label}: {node.get('name') or node.get('code')}")
        if factory != "Factory (Not Mapped)":
            formatted_path.append(f"Factory: {factory}")
            
        tier_depth = len(path_nodes) - 2 # Supplier (0) -> ... -> Part (N)
        
        # Risk Propagation Math:
        # We look for the bottleneck (minimum days to stoppage) along the path
        min_days_to_stoppage = float('inf')
        bottleneck_reason = ""
        overall_alt_allowed = True # Assumes safe unless a bottleneck has no alt
        
        # Check each supply relationship in the path
        for rel in path_rels:
            m_stock = rel.get("minimum_stock_units")
            # For Tier-N, we don't always have daily consumption at the edge,
            # but we use the factory's consumption as a proxy for the entire chain impact.
            if m_stock is not None and daily_consumption and daily_consumption > 0:
                days = round(m_stock / daily_consumption, 1)
                if days < min_days_to_stoppage:
                    min_days_to_stoppage = days
                    overall_alt_allowed = rel.get("alt_supplier_allowed", False)
                    l_time = rel.get("lead_time_days", 0)
                    bottleneck_reason = f"Bottleneck at {rel.type} (Stock: {m_stock}, Lead Time: {l_time})"

        if min_days_to_stoppage == float('inf'):
            days_to_stoppage = "Unknown"
            risk_score = "Medium"
            recommendations = "Incomplete supply chain mapping. Manual verification required."
        else:
            days_to_stoppage = min_days_to_stoppage
            # Lead time of the immediate link
            last_rel = path_rels[-1]
            lead_time = last_rel.get("lead_time_days", 0)
            
            if days_to_stoppage < lead_time and not overall_alt_allowed:
                risk_score = "High"
                recommendations = f"CRITICAL: Line stoppage in {days_to_stoppage} days. No alternative supplier for bottleneck."
            elif days_to_stoppage < lead_time and overall_alt_allowed:
                risk_score = "Medium"
                recommendations = f"WARNING: Potential stoppage in {days_to_stoppage} days. Activate alternative sourcing."
            else:
                risk_score = "Low"
                recommendations = f"Buffer levels sufficient ({days_to_stoppage} days) for currently mapped lead times."

        # Crisis duration override
        if isinstance(days_to_stoppage, (int, float)) and crisis_duration_days > days_to_stoppage:
            if risk_score != "High":
                risk_score = "High"
                recommendations += f" Crisis duration ({crisis_duration_days}d) exceeds coverage."

        simulations.append(RiskSimulationResult(
            impacted_paths=formatted_path,
            tier_depth=tier_depth,
            days_to_line_stoppage=days_to_stoppage,
            risk_score=risk_score,
            recommendations=recommendations
        ))
        
    return simulations
