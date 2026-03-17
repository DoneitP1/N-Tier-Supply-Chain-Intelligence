import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from services.ingestion_core import process_pdf_and_extract, process_contract
from models.schemas import ContractData, SupplierInfo, PartInfo, ClauseInfo, TokenData
from models.pg_models import AuditLog, OutboxEvent

@pytest.mark.asyncio
async def test_process_pdf_and_extract_success():
    # Mock pypdf reader
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Extracted text content"
    mock_reader.pages = [mock_page]
    
    with patch("pypdf.PdfReader", return_value=mock_reader):
        text = await process_pdf_and_extract("mock.pdf")
        assert "Extracted text content" in text

@pytest.mark.asyncio
async def test_process_pdf_and_extract_failure():
    with patch("pypdf.PdfReader", side_effect=Exception("Read error")):
        with pytest.raises(ValueError, match="Could not read PDF"):
            await process_pdf_and_extract("bad.pdf")

@pytest.mark.asyncio
async def test_process_contract_outbox_and_audit(mock_sql_session):
    contract = ContractData(
        supplier=SupplierInfo(name="Old Name", location="Istanbul", confidence_score=0.9),
        parts=[PartInfo(part_code="P1", confidence_score=0.9)],
        clauses=ClauseInfo(force_majeure_present=True, alternative_supplier_allowed=False, confidence_score=0.9),
        overall_extraction_confidence=0.95
    )
    user = TokenData(username="testadmin", role="admin")
    
    # Mock entity resolution to return the same name or resolved name
    with patch("services.ingestion_core.resolve_supplier_name", return_value="Resolved Supplier"):
        with patch("core.outbox.push_to_outbox", new_callable=AsyncMock) as mock_push:
            await process_contract(contract, user, mock_sql_session, ip_address="127.0.0.1")
            
            # Verify entity resolution was applied
            assert contract.supplier.name == "Resolved Supplier"
            
            # Verify outbox push
            mock_push.assert_called_once()
            args, kwargs = mock_push.call_args
            assert args[1] == "sync_contract"
            assert args[2]["supplier_name"] == "Resolved Supplier"
            
            # Verify audit log was added to session
            # (conftest mock_sql_session provides add method through AsyncMock)
            assert mock_sql_session.add.called
            audit = mock_sql_session.add.call_args[0][0]
            assert isinstance(audit, AuditLog)
            assert audit.action == "ingest_contract"
            assert audit.target_node == "Resolved Supplier"
