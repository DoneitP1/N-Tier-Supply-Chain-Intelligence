import pytest
from models.schemas import ERPBOMPayload, Tier1Supplier
from services.erp_integration import ingest_erp_bom

@pytest.mark.asyncio
async def test_ingest_erp_bom_success():
    payload = ERPBOMPayload(
        source="SAP",
        factory="TestFactory",
        part_code="TP-100",
        daily_consumption_units=50.5,
        tier_1_supplier=Tier1Supplier(name="TestTier1")
    )
    
    # We can use the mock db connection from conftest.py if it's imported or globally mocked
    class FakeDB:
        async def execute_query(self, query, parameters=None):
            return []
            
    result = await ingest_erp_bom(payload, db_connection=FakeDB())
    
    assert result["status"] == "success"
    assert "TestTier1" in result["message"]
