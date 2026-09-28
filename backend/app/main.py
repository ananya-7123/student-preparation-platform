from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize the FastAPI application
app = FastAPI(
    title="Student Preparation Platform API",
    description="Agentic AI-Based backend for KIIT Placement Preparation",
    version="1.0.0"
)

# Set up CORS middleware to allow the frontend to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins during development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def read_root():
    """
    Root endpoint to verify the API is reachable.
    """
    return {"message": "Welcome to the Student Preparation Platform API!"}

@app.get("/health")
def health_check():
    """
    Health check endpoint to ensure the server is running smoothly.
    """
    return {"status": "healthy"}
