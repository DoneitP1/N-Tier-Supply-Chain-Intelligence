from typing import List, Optional, Set
from models.schemas import RiskSimulationResult, WeakestLink

async def simulate_risk_propagation(supplier_name: str, crisis_duration_days: int, db_connection) -> Optional[RiskSimulationResult]:
    """
    Simulates recursive risk propagation across N-Tier supplier paths.
    Traverses from the impacted supplier through any number of sub-suppliers
    until reaching a Part consumed by a Factory.
    Aggregates results into a single comprehensive risk assessment.
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
        
    impacted_factories = set()
    impacted_nodes = set()
    weakest_links = []
    max_depth = 0
    bottlenecks = set()
    
    for row in results:
        path_nodes = row.get("path_nodes", [])
        path_rels = row.get("path_rels", [])
        factory = row.get("factory_name")
        daily_consumption = row.get("daily_consumption")
        
        if factory:
            impacted_factories.add(factory)
            
        # Track all unique nodes impacted
        for node in path_nodes:
            # Using internal ID (element_id or id) as unique identifier
            node_id = node.get("id") or node.element_id
            impacted_nodes.add(node_id)
            
        tier_depth = len(path_nodes) - 1 # Depth of the chain
        if tier_depth > max_depth:
            max_depth = tier_depth
            
        # Check each supply relationship in the path
        for i, rel in enumerate(path_rels):
            m_stock = rel.get("minimum_stock_units")
            l_time = rel.get("lead_time_days", 0)
            
            # Identify weakest links and bottlenecks
            if m_stock is not None and daily_consumption and daily_consumption > 0:
                days_coverage = m_stock / daily_consumption
                if days_coverage < crisis_duration_days or days_coverage < l_time:
                    # This is a weak link
                    supplier_node = path_nodes[i]
                    part_node = path_nodes[i+1]
                    
                    link = WeakestLink(
                        supplier=supplier_node.get("name") or "Unknown Supplier",
                        part=part_node.get("name") or part_node.get("code") or "Unknown Part",
                        stock=int(m_stock),
                        lead_time=int(l_time)
                    )
                    
                    # Avoid duplicates in weakest links
                    link_key = (link.supplier, link.part)
                    if not any(l.supplier == link.supplier and l.part == link.part for l in weakest_links):
                        weakest_links.append(link)
                        bottlenecks.add(f"Low stock for {link.part} at {link.supplier}")

    return RiskSimulationResult(
        cascading_impact_depth=max_depth,
        impacted_factories=list(impacted_factories),
        total_impacted_nodes=len(impacted_nodes),
        bottlenecks=list(bottlenecks),
        weakest_links=weakest_links
    )
