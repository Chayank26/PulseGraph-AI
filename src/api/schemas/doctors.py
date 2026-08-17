from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DoctorCreate(BaseModel):
    doctor_id: str = Field(..., example="DOC-88204", description="Unique clinician doctor_id")
    full_name: str = Field(..., example="Dr. Sarah Chen", description="Full physician name")
    department: str = Field(..., example="Emergency Medicine", description="Medical department")
    password: str = Field(..., example="password123", description="Secure account password")
    role: str = Field(default="Attending Physician", example="Attending Physician", description="Physician role")


class DoctorResponse(BaseModel):
    id: int
    doctor_id: str
    full_name: str
    department: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True
