import pytest
from unittest.mock import MagicMock, AsyncMock
from services.risk_engine import simulate_risk_propagation
from models.schemas import RiskSimulationResult

@pytest.mark.asyncio
async def test_simulate_risk_propagation_with_impact(mock_db_connection):
    # Mock Neo4j results for a 2-tier chain
    # Tier 0 (Supplier) -> Tier 1 (Sub-supplier) -> Tier 2 (Part) -> Factory
    mock_results = [
        {
            "path_nodes": [
                {"name": "Tier 0 Supplier", "id": 1, "element_id": "1"},
                {"name": "Tier 1 Supplier", "id": 2, "element_id": "2"},
                {"name": "Impacted Part", "id": 3, "element_id": "3"}
            ],
            "path_rels": [
                {"minimum_stock_units": 100, "lead_time_days": 10},
                {"minimum_stock_units": 10, "lead_time_days": 5} # Bottleneck: stock 10 < crisis 30
            ],
            "factory_name": "Main Factory",
            "daily_consumption": 1.0 # 1 unit per day
        }
    ]
    
    mock_db_connection.execute_query.side_effect = None # Remove conftest side effect
    mock_db_connection.execute_query.return_value = mock_results
    
    result = await simulate_risk_propagation("Tier 0 Supplier", 30, mock_db_connection)
    
    assert result is not None
    assert isinstance(result, RiskSimulationResult)
    assert result.cascading_impact_depth == 2 # 3 nodes, depth is 2
    assert "Main Factory" in result.impacted_factories
    assert result.total_impacted_nodes == 3
    
    # Check for bottleneck (stock 10 / consumption 1.0 = 10 days < 30 days)
    assert len(result.weakest_links) > 0
    assert any("Tier 1 Supplier" == link.supplier for link in result.weakest_links)
    assert any("Low stock" in b for b in result.bottlenecks)

@pytest.mark.asyncio
async def test_simulate_risk_propagation_no_path(mock_db_connection):
    mock_db_connection.execute_query.side_effect = None
    mock_db_connection.execute_query.return_value = []
    
    result = await simulate_risk_propagation("Unknown Supplier", 30, mock_db_connection)
    
    assert result is None
