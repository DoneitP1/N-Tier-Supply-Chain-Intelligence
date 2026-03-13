import pytest
from pydantic import ValidationError
from models.schemas import SupplierInfo, ContractData, PartInfo, ClauseInfo, RiskSimulationRequest

def test_supplier_info_validation():
    # Valid
    supplier = SupplierInfo(name="AutoCorp", location="Bursa", confidence_score=0.85)
    assert supplier.name == "AutoCorp"
    
    # Invalid: confidence_score out of bounds
    with pytest.raises(ValidationError):
        SupplierInfo(name="AutoCorp", confidence_score=1.5)

def test_contract_data_validation():
    # Invalid: missing overall_extraction_confidence
    with pytest.raises(ValidationError):
        ContractData(
            supplier=SupplierInfo(name="AutoCorp", confidence_score=0.9),
            parts=[PartInfo(part_code="P-123", confidence_score=0.9)],
            clauses=ClauseInfo(force_majeure_present=True, alternative_supplier_allowed=True, confidence_score=0.9)
        )

def test_risk_simulation_request():
    req = RiskSimulationRequest(impacted_supplier_name="Bursa Parts", crisis_duration_days=14)
    assert req.impacted_supplier_name == "Bursa Parts"
    assert req.crisis_duration_days == 14
    
    # Test typing validation
    with pytest.raises(ValidationError):
        RiskSimulationRequest(impacted_supplier_name="Bursa Parts", crisis_duration_days="two weeks")
