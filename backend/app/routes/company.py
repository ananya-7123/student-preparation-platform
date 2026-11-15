from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company
from app.schemas import CompanyResponse
from app.agent.tools import (
    get_company_details,
    get_eligibility,
    get_selection_process
)

# Initialize the router with a prefix and tags for Swagger documentation
router = APIRouter(
    prefix="/companies",
    tags=["Companies"]
)

@router.get("/", response_model=List[CompanyResponse])
def list_companies(db: Session = Depends(get_db)):
    """
    List all companies stored in the PostgreSQL database.
    """
    return db.query(Company).order_by(Company.name).all()

@router.get("/{company_name}")
def get_company(company_name: str):
    """
    Fetch general details for a specific company (e.g., TCS, Accenture).
    """
    result = get_company_details(company_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/{company_name}/eligibility")
def get_company_eligibility(company_name: str):
    """
    Fetch eligibility criteria for a specific company.
    """
    result = get_eligibility(company_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/{company_name}/selection-process")
def get_company_selection_process(company_name: str):
    """
    Fetch recruitment rounds and selection process for a specific company.
    """
    result = get_selection_process(company_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
