from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field

# --- Contract & General Models ---
class SupplierInfo(BaseModel):
    name: str = Field(..., description="Name of the supplier or factory.")
    location: Optional[str] = Field(None, description="Physical location of the supplier.")
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class PartInfo(BaseModel):
    part_code: str
    lead_time_days: Optional[int] = None
    minimum_stock_units: Optional[int] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class ClauseInfo(BaseModel):
    force_majeure_present: bool
    force_majeure_details: Optional[str] = None
    alternative_supplier_allowed: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class ContractData(BaseModel):
    document_type: str = "contract"
    supplier: SupplierInfo
    parts: List[PartInfo]
    clauses: ClauseInfo
    overall_extraction_confidence: float = Field(..., ge=0.0, le=1.0)

class RawTextPayload(BaseModel):
    text: str = Field(..., description="Raw text prefixed with [TYPE: CONTRACT_PDF] or [TYPE: NEWS_FEED]")

# --- News Models ---
class EventClassification(BaseModel):
    is_supply_chain_risk: bool
    event_type: str = Field(..., description="e.g., Natural Disaster, Geopolitical")
    severity: str = Field(..., description="Low, Medium, High, Critical")
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class ImpactDetails(BaseModel):
    locations_affected: List[str]
    entities_affected: List[str]
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class NewsRiskData(BaseModel):
    document_type: str = "news_risk"
    event_classification: EventClassification
    impact_details: ImpactDetails
    summary: str
    overall_assessment_confidence: float = Field(..., ge=0.0, le=1.0)

# --- ERP Models ---
class Tier1Supplier(BaseModel):
    name: str = Field(..., description="Name of the Tier-1 supplier.")
    location: Optional[str] = Field(None, description="Location of the Tier-1 supplier.")

class Tier2Supplier(BaseModel):
    name: str = Field(..., description="Name of the Tier-2 supplier/subcontractor.")
    location: Optional[str] = Field(None, description="Location of the Tier-2 supplier.")
    critical_material: Optional[str] = Field(None, description="Raw material provided.")

class ERPBOMPayload(BaseModel):
    source: str = Field(..., description="Source system (e.g., SAP_ERP, ORACLE)")
    factory: str = Field(..., description="Main factory consuming the part")
    part_code: str = Field(..., description="The unified part code")
    daily_consumption_units: float = Field(..., description="Daily consumption rate of the part by the factory")
    tier_1_supplier: Tier1Supplier
    tier_2_supplier: Optional[Tier2Supplier] = None

# --- Risk Engine Models ---
class RiskSimulationRequest(BaseModel):
    supplier_name: str
    duration_days: int
    severity: str = "medium"

class WeakestLink(BaseModel):
    supplier: str
    part: str
    stock: int
    lead_time: int

class RiskSimulationResult(BaseModel):
    cascading_impact_depth: int
    impacted_factories: List[str]
    total_impacted_nodes: int
    bottlenecks: List[str]
    weakest_links: List[WeakestLink]

# --- Auth & User Models ---
class UserBase(BaseModel):
    username: str
    role: Literal["admin", "analyst"] = Field("analyst", description="Role of the user: admin or analyst")

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    hashed_password: str

class User(UserBase):
    id: Optional[int] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str
    role: Literal["admin", "analyst"]
