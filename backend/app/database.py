import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables from the project root .env file
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def get_database_url() -> str:
    """
    Build or retrieve the PostgreSQL connection URL from environment variables.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url and "${" not in db_url:
        return db_url

    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "student_prep_db")

    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


DATABASE_URL = get_database_url()

# Create the SQLAlchemy Engine (pool_pre_ping checks stale connections automatically)
connect_args = {}
if DATABASE_URL.startswith("postgresql"):
    connect_args["connect_timeout"] = 3

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)

# Session factory for creating per-request database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class that all ORM models in models.py will inherit from
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session per request
    and guarantees it closes when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Execute a lightweight query to verify PostgreSQL is reachable.
    """
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True

