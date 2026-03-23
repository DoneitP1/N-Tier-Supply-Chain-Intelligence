from typing import List, Optional, Set
from models.schemas import RiskSimulationResult, WeakestLink
from core.config import settings

async def simulate_risk_propagation(supplier_name: str, crisis_duration_days: int, db_connection) -> Optional[RiskSimulationResult]:
    """
    Simulates recursive risk propagation across N-Tier supplier paths.
    Traverses from the impacted supplier through any number of sub-suppliers
    until reaching a Part consumed by a Factory.
    Aggregates results into a single comprehensive risk assessment.
    """

    # Rewritten to explicitly return scalar values instead of raw Node/Relationship objects.
    # result.data() only serializes node/relationship *properties*, not internal IDs,
    # so we extract elementId() and specific properties inline in the Cypher query.
    query = f"""
    MATCH path = (s:Supplier {{name: $supplier_name}})-[:SUPPLIES*1..{settings.risk_simulation_depth}]->(p:Part)
    WITH path, nodes(path) AS path_nodes, relationships(path) AS path_rels, length(path) AS depth
    OPTIONAL MATCH (p)<-[con:CONSUMES]-(f:Factory)
    RETURN
        depth,
        f.name AS factory_name,
        con.daily_consumption AS daily_consumption,
        [n IN path_nodes | {{
            elem_id: elementId(n),
            name: coalesce(n.name, n.code, n.type, 'Unknown')
        }}] AS nodes_info,
        [r IN path_rels | {{
            minimum_stock_units: r.minimum_stock_units,
            lead_time_days: r.lead_time_days
        }}] AS rels_info
    """
    
    results = await db_connection.execute_query(query, {"supplier_name": supplier_name})
    
    if not results:
        return None
        
    impacted_factories: Set[str] = set()
    impacted_node_ids: Set[str] = set()
    weakest_links: List[WeakestLink] = []
    max_depth = 0
    bottlenecks: Set[str] = set()
    
    for row in results:
        depth = row.get("depth", 0)
        factory = row.get("factory_name")
        daily_consumption = row.get("daily_consumption")
        nodes_info = row.get("nodes_info", [])
        rels_info = row.get("rels_info", [])
        
        if factory:
            impacted_factories.add(factory)
            
        # Track all unique nodes in this path
        for node in nodes_info:
            elem_id = node.get("elem_id")
            if elem_id:
                impacted_node_ids.add(elem_id)
            
        if depth > max_depth:
            max_depth = depth
            
        # Evaluate each supply relationship for weakness
        for i, rel in enumerate(rels_info):
            m_stock = rel.get("minimum_stock_units")
            l_time = rel.get("lead_time_days") or 0
            
            if m_stock is not None and daily_consumption and daily_consumption > 0:
                days_coverage = m_stock / daily_consumption
                if days_coverage < crisis_duration_days or days_coverage < l_time:
                    if i < len(nodes_info) and i + 1 < len(nodes_info):
                        supplier_node = nodes_info[i]
                        part_node = nodes_info[i + 1]
                        
                        link = WeakestLink(
                            supplier=supplier_node.get("name") or "Unknown Supplier",
                            part=part_node.get("name") or "Unknown Part",
                            stock=int(m_stock),
                            lead_time=int(l_time)
                        )
                        
                        # Avoid duplicates
                        if not any(l.supplier == link.supplier and l.part == link.part for l in weakest_links):
                            weakest_links.append(link)
                            bottlenecks.add(f"Low stock for {link.part} at {link.supplier}")

    return RiskSimulationResult(
        cascading_impact_depth=max_depth,
        impacted_factories=list(impacted_factories),
        total_impacted_nodes=len(impacted_node_ids),
        bottlenecks=list(bottlenecks),
        weakest_links=weakest_links
    )
