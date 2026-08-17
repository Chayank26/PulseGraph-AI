from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class VitalsPayload(BaseModel):
    heart_rate_bpm: Optional[float] = Field(default=None, example=48.0)
    blood_pressure_sys: Optional[float] = Field(default=None, example=135.0)
    blood_pressure_dia: Optional[float] = Field(default=None, example=85.0)
    temperature_c: Optional[float] = Field(default=None, example=37.1)
    respiratory_rate: Optional[float] = Field(default=None, example=22.0)
    spo2_percent: Optional[float] = Field(default=None, example=91.0)


class SessionCreateRequest(BaseModel):
    patient_id: str = Field(..., example="PAT-88291", description="Patient identifier")
    raw_notes: List[str] = Field(default_factory=list, example=["Patient presents with sudden onset chest pain."], description="Clinical intake notes")
    vitals: Optional[VitalsPayload] = Field(default=None, description="Initial physiological vitals")
    image_path: Optional[str] = Field(default=None, example="data/mock_patients/patient_001_cxr.png", description="Path to Chest X-Ray DICOM/PNG")


class SessionResponse(BaseModel):
    session_id: str
    patient_id: str
    doctor_id: str
    status: str
    current_step: str
    thread_id: str
    iteration_count: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DataRequestResolvePayload(BaseModel):
    response_data: Dict[str, Any] = Field(..., example={"history_score": 2, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2}, description="Field-value responses resolving the ClinicalDataRequest")


class ClinicianReviewPayload(BaseModel):
    notes: Optional[str] = Field(default=None, example="Risk scores and imaging findings reviewed. Proceeding with PE protocol.", description="Attending physician notes")


class ClinicianReevaluatePayload(BaseModel):
    notes: str = Field(..., example="Re-evaluate differential diagnoses considering recent troponin trend.", description="Physician re-evaluation instructions")
