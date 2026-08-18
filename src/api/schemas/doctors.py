from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class DoctorCreate(BaseModel):
    doctor_id: str = Field(..., min_length=1, json_schema_extra={"example": "DOC-88204"}, description="Unique clinician doctor_id")
    full_name: str = Field(..., min_length=1, json_schema_extra={"example": "Dr. Sarah Chen"}, description="Full physician name")
    department: str = Field(..., min_length=1, json_schema_extra={"example": "Emergency Medicine"}, description="Medical department")
    password: str = Field(..., min_length=6, json_schema_extra={"example": "password123"}, description="Secure account password")
    role: str = Field(default="Attending Physician", json_schema_extra={"example": "Attending Physician"}, description="Physician role")


class DoctorResponse(BaseModel):
    id: int
    doctor_id: str
    full_name: str
    department: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
