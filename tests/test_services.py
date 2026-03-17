import pytest
from unittest.mock import patch, AsyncMock
from models.schemas import ERPBOMPayload, Tier1Supplier, TokenData
from services.erp_integration import ingest_erp_bom

@pytest.mark.asyncio
async def test_ingest_erp_bom_success(mock_sql_session):
    payload = ERPBOMPayload(
        source="SAP",
        factory="TestFactory",
        part_code="TP-100",
        daily_consumption_units=50.5,
        tier_1_supplier=Tier1Supplier(name="TestTier1", location="Istanbul")
    )
    user = TokenData(username="testadmin", role="admin")
    
    with patch("core.outbox.push_to_outbox", new_callable=AsyncMock) as mock_push:
        result = await ingest_erp_bom(payload, db_sql=mock_sql_session, current_user=user)
        
        assert result["status"] == "success"
        assert "TestTier1" in result["message"]
        mock_push.assert_called_once()
