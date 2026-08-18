from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class PatientCreate(BaseModel):
    patient_id: str = Field(..., json_schema_extra={"example": "PAT-88291"}, description="Unique medical record number / patient ID")
    age: Optional[int] = Field(default=None, json_schema_extra={"example": 58}, description="Patient age in years")
    gender: Optional[str] = Field(default=None, json_schema_extra={"example": "Male"}, description="Biological sex / gender")
    blood_type: Optional[str] = Field(default=None, json_schema_extra={"example": "A+"}, description="Blood type")
    allergies: List[str] = Field(default_factory=list, json_schema_extra={"example": ["Penicillin"]}, description="Documented drug/food allergies")
    chronic_conditions: List[str] = Field(default_factory=list, json_schema_extra={"example": ["Hypertension", "Chronic Kidney Disease"]}, description="Chronic medical conditions")
    current_medications: List[str] = Field(default_factory=list, json_schema_extra={"example": ["Warfarin 5mg", "Metoprolol 25mg"]}, description="Current medication regimen")


class PatientUpdate(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[List[str]] = None
    chronic_conditions: Optional[List[str]] = None
    current_medications: Optional[List[str]] = None


class PatientResponse(BaseModel):
    id: int
    patient_id: str
    age: Optional[int]
    gender: Optional[str]
    blood_type: Optional[str]
    allergies: List[str]
    chronic_conditions: List[str]
    current_medications: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
