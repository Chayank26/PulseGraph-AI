from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    doctor_id: str = Field(..., example="DOC-88204", description="Clinician identifier")
    password: str = Field(..., example="password123", description="Clinician password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doctor_id: str
    full_name: str
    department: str
    role: str
