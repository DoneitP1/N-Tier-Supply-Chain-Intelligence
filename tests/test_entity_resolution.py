import pytest
from unittest.mock import MagicMock, patch
from services.entity_resolution import resolve_supplier_name

@pytest.mark.asyncio
async def test_resolve_supplier_name_high_score(mock_db_connection):
    # Mock Neo4j FTS result with high score
    mock_db_connection.execute_query.side_effect = None
    mock_db_connection.execute_query.return_value = [
        {"name": "Samsung Electronics", "score": 0.8}
    ]
    
    resolved = await resolve_supplier_name("Samsung")
    assert resolved == "Samsung Electronics"

@pytest.mark.asyncio
async def test_resolve_supplier_name_low_score(mock_db_connection):
    # Mock Neo4j FTS result with low score
    mock_db_connection.execute_query.side_effect = None
    mock_db_connection.execute_query.return_value = [
        {"name": "Something Else", "score": 0.2} # 0.2 * 100 = 20 < 50
    ]
    
    resolved = await resolve_supplier_name("Samsung")
    # Should return original name if score is low
    assert resolved == "Samsung"

@pytest.mark.asyncio
async def test_resolve_supplier_name_no_results(mock_db_connection):
    mock_db_connection.execute_query.side_effect = None
    mock_db_connection.execute_query.return_value = []
    
    resolved = await resolve_supplier_name("New Supplier")
    assert resolved == "New Supplier"

@pytest.mark.asyncio
async def test_resolve_supplier_name_exception(mock_db_connection):
    mock_db_connection.execute_query.side_effect = Exception("Neo4j error")
    
    resolved = await resolve_supplier_name("Any Name")
    # Should fall back to original name on error
    assert resolved == "Any Name"
