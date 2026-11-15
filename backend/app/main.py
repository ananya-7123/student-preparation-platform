from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.auth_utils import ensure_auth_schema
from app.database import check_db_connection
from app.routes.agent import router as agent_router
from app.routes.auth import router as auth_router
from app.routes.company import router as company_router
from app.routes.mock import router as mock_router
from app.routes.performance import router as performance_router
from app.routes.questions import router as questions_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        ensure_auth_schema()
    except Exception:
        pass
    yield


# Initialize the FastAPI application
app = FastAPI(
    title="Student Preparation Platform API",
    description="Agentic AI-Based backend for KIIT Placement Preparation",
    version="1.0.0",
    lifespan=lifespan,
)

# Set up CORS middleware to allow the frontend to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins during development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Register API Routers
app.include_router(auth_router)
app.include_router(company_router)
app.include_router(questions_router)
app.include_router(mock_router)
app.include_router(performance_router)
app.include_router(agent_router)

# Serve Frontend UI cleanly at /ui without affecting API root
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

@app.get("/")
def read_root():
    """
    Redirect root to the frontend UI.
    """
    return RedirectResponse(url="/ui/")

@app.get("/health")
def health_check():
    """
    Health check endpoint to verify the API and PostgreSQL database connection.
    """
    try:
        check_db_connection()
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}
