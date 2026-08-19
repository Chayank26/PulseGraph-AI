import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.settings import settings
from src.db.database import init_db
from src.api.routes.auth import router as auth_router
from src.api.routes.doctors import router as doctors_router
from src.api.routes.patients import router as patients_router
from src.api.routes.sessions import router as sessions_router
from src.api.routes.clinical import router as clinical_router

logger = logging.getLogger("PulseGraph.API")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI application lifespan event handler."""
    logger.info("Starting PulseGraph AI Backend API Service...")
    init_db()
    yield
    logger.info("Shutting down PulseGraph AI Backend API Service...")
    from src.core.checkpointer import close_checkpointer_pool
    close_checkpointer_pool()


app = FastAPI(
    title="PulseGraph AI — Clinical Decision Support Backend API",
    description=(
        "API for PulseGraph AI Neuro-Symbolic Multimodal Clinical Decision Support System. "
        "Provides physician authentication, patient data management, LangGraph workflow execution, "
        "sequential blocking data acquisition, and Human-in-the-Loop clinical review."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_msg = "; ".join([f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}" for err in errors])
    logger.warning(f"Validation failure on {request.url}: {error_msg}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"Request validation failure: {error_msg}"}
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"Business logic validation error on {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled internal server error processing request: {request.method} {request.url}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred while processing the clinical request."}
    )


# Include Routers
app.include_router(auth_router)
app.include_router(doctors_router)
app.include_router(patients_router)
app.include_router(sessions_router)
app.include_router(clinical_router)


@app.get("/health", tags=["Health & Status"])
def health_check():
    """Service health check endpoint."""
    return {
        "status": "HEALTHY",
        "service": "PulseGraph AI Backend API",
        "environment": settings.environment,
        "database_host": settings.postgres_host
    }
