from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from core.security import RoleChecker, get_current_user
from models.schemas import TokenData
from core.database import db, logger

# RBAC Dependencies
analyst_or_admin = RoleChecker(["analyst", "admin"])

router = APIRouter(prefix="/api/graph", tags=["Graph Visualization"])

@router.get("/data", status_code=status.HTTP_200_OK, dependencies=[Depends(analyst_or_admin)])
async def get_graph_data(limit: int = Query(200, description="Limit max relationships evaluated to prevent UI freeze")):
    """
    Fetches Knowledge Graph nodes and edges for visualization with a hard limit on relationships
    to prevent overwhelming the neo4j engine and the browser.
    """
    query = """
    MATCH (n)-[r]->(m)
    RETURN 
        id(n) AS n_id, labels(n)[0] AS n_label, coalesce(n.name, n.code, n.type, "Unknown") AS n_name,
        id(m) AS m_id, labels(m)[0] AS m_label, coalesce(m.name, m.code, m.type, "Unknown") AS m_name,
        type(r) AS r_type
    LIMIT $limit
    """
    try:
        results = await db.execute_query(query, {"limit": limit})
        nodes_dict = {}
        edges = []
        
        for row in results:
            n_id = row.get("n_id")
            m_id = row.get("m_id")
            
            if n_id not in nodes_dict:
                nodes_dict[n_id] = {
                    "id": n_id,
                    "label": row.get("n_label", "Unknown"),
                    "name": row.get("n_name", "Unknown")
                }
                
            if m_id not in nodes_dict:
                nodes_dict[m_id] = {
                    "id": m_id,
                    "label": row.get("m_label", "Unknown"),
                    "name": row.get("m_name", "Unknown")
                }
                
            edges.append({
                "source": n_id,
                "target": m_id,
                "type": row.get("r_type", "RELATED")
            })
            
        return {"nodes": list(nodes_dict.values()), "edges": edges}
    except Exception as e:
        logger.error(f"Error retrieving graph data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes", status_code=status.HTTP_200_OK, dependencies=[Depends(analyst_or_admin)])
async def get_nodes(label: Optional[str] = Query(None, description="Filter nodes by label (e.g., Supplier)")):
    """
    Fetches nodes, optionally filtered by label.
    """
    try:
        if label:
            # Using elementId() for modern Neo4j compatibility
            query = f"MATCH (n:{label}) RETURN elementId(n) AS id, labels(n)[0] AS label, coalesce(n.name, n.code, n.type, 'Unknown') AS name"
        else:
            query = "MATCH (n) RETURN elementId(n) AS id, labels(n)[0] AS label, coalesce(n.name, n.code, n.type, 'Unknown') AS name"
        
        results = await db.execute_query(query)
        # Ensure we return a list of objects that the frontend expects
        return [
            {
                "id": row["id"], 
                "label": row["label"] or (label if label else "Unknown"), 
                "name": row["name"]
            } for row in results
        ]
    except Exception as e:
        logger.error(f"Error retrieving nodes for label '{label}': {str(e)}", exc_info=True)
        # Provide a more helpful error message
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve {label if label else 'graph'} nodes from database."
        )
