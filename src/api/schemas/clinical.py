from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ClinicalDataRequestResponse(BaseModel):
    request_id: str
    session_id: str
    requesting_agent: str
    pathway_name: str
    reason: str
    priority: str
    required_fields: List[Dict[str, Any]]
    optional_fields: List[Dict[str, Any]]
    status: str
    clinician_response: Optional[Dict[str, Any]] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    session_id: str
    timestamp: datetime
    agent_name: str
    action: str
    summary: str
    metadata_json: Dict[str, Any]

    class Config:
        from_attributes = True


class CDSResultResponse(BaseModel):
    session_id: str
    risk_scores: List[Dict[str, Any]]
    differentials: List[Dict[str, Any]]
    imaging_findings: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    safety_flags: List[Dict[str, Any]]
    symbolic_overrides: List[Dict[str, Any]]
    final_status: str
    clinician_approval: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
