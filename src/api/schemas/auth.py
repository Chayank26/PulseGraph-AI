from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    doctor_id: str = Field(..., json_schema_extra={"example": "DOC-88204"}, description="Clinician identifier")
    password: str = Field(..., json_schema_extra={"example": "password123"}, description="Clinician password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doctor_id: str
    full_name: str
    department: str
    role: str
