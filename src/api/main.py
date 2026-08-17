import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.db.database import init_db
from src.api.routes.auth import router as auth_router
from src.api.routes.doctors import router as doctors_router
from src.api.routes.patients import router as patients_router
from src.api.routes.sessions import router as sessions_router
from src.api.routes.clinical import router as clinical_router

logger = logging.getLogger("PulseGraph.API")

app = FastAPI(
    title="PulseGraph AI — Clinical Decision Support Backend API",
    description=(
        "API for PulseGraph AI Neuro-Symbolic Multimodal Clinical Decision Support System. "
        "Provides physician authentication, patient data management, LangGraph workflow execution, "
        "sequential blocking data acquisition, and Human-in-the-Loop clinical review."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(doctors_router)
app.include_router(patients_router)
app.include_router(sessions_router)
app.include_router(clinical_router)


@app.on_event("startup")
def startup_event():
    logger.info("Starting PulseGraph AI Backend API Service...")
    init_db()


@app.get("/health", tags=["Health & Status"])
def health_check():
    """Service health check endpoint."""
    return {
        "status": "HEALTHY",
        "service": "PulseGraph AI Backend API",
        "environment": settings.environment,
        "database_host": settings.postgres_host
    }
