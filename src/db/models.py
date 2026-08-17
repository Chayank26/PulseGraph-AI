from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    DateTime,
    Text,
    JSON,
    ForeignKey
)
from sqlalchemy.orm import relationship
from src.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DoctorModel(Base):
    """SQLAlchemy model for authenticated clinicians / doctors."""
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id = Column(String(64), unique=True, nullable=False, index=True)
    full_name = Column(String(128), nullable=False)
    department = Column(String(128), nullable=False)
    role = Column(String(64), nullable=False, default="Attending Physician")
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    sessions = relationship("ClinicalSessionModel", back_populates="doctor", cascade="all, delete-orphan")


class PatientModel(Base):
    """SQLAlchemy model for patient demographics and baseline clinical data."""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(64), unique=True, nullable=False, index=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(32), nullable=True)
    blood_type = Column(String(16), nullable=True)
    allergies = Column(JSON, default=list, nullable=False)
    chronic_conditions = Column(JSON, default=list, nullable=False)
    current_medications = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    sessions = relationship("ClinicalSessionModel", back_populates="patient", cascade="all, delete-orphan")


class ClinicalSessionModel(Base):
    """SQLAlchemy model representing a PulseGraph clinical decision support session."""
    __tablename__ = "clinical_sessions"

    session_id = Column(String(64), primary_key=True, index=True)
    patient_id = Column(String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(String(64), ForeignKey("doctors.doctor_id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(64), nullable=False, default="INITIALIZED", index=True)
    current_step = Column(String(64), nullable=False, default="initialized")
    thread_id = Column(String(128), unique=True, nullable=False, index=True)
    iteration_count = Column(Integer, default=0, nullable=False)
    clinician_notes = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    patient = relationship("PatientModel", back_populates="sessions")
    doctor = relationship("DoctorModel", back_populates="sessions")
    data_requests = relationship("ClinicalDataRequestModel", back_populates="session", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogModel", back_populates="session", cascade="all, delete-orphan")
    cds_result = relationship("CDSResultModel", back_populates="session", uselist=False, cascade="all, delete-orphan")


class ClinicalDataRequestModel(Base):
    """SQLAlchemy model for persistent ClinicalDataRequests."""
    __tablename__ = "clinical_data_requests"

    request_id = Column(String(64), primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("clinical_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    requesting_agent = Column(String(64), nullable=False)
    pathway_name = Column(String(128), nullable=False)
    reason = Column(Text, nullable=False)
    priority = Column(String(32), default="HIGH", nullable=False)
    required_fields = Column(JSON, default=list, nullable=False)
    optional_fields = Column(JSON, default=list, nullable=False)
    status = Column(String(32), default="PENDING", nullable=False, index=True)
    clinician_response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("ClinicalSessionModel", back_populates="data_requests")


class AuditLogModel(Base):
    """SQLAlchemy model for append-only clinical audit logs."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("clinical_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    agent_name = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    summary = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)

    session = relationship("ClinicalSessionModel", back_populates="audit_logs")


class CDSResultModel(Base):
    """SQLAlchemy model for persisting final generated clinical decision-support output."""
    __tablename__ = "cds_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("clinical_sessions.session_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    risk_scores = Column(JSON, default=list, nullable=False)
    differentials = Column(JSON, default=list, nullable=False)
    imaging_findings = Column(JSON, default=list, nullable=False)
    evidence = Column(JSON, default=list, nullable=False)
    safety_flags = Column(JSON, default=list, nullable=False)
    symbolic_overrides = Column(JSON, default=list, nullable=False)
    final_status = Column(String(64), nullable=False, default="IN_PROGRESS")
    clinician_approval = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    session = relationship("ClinicalSessionModel", back_populates="cds_result")
