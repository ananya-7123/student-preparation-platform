from pydantic import BaseModel
from typing import Optional, List

class CompanyBase(BaseModel):
    name: str
    description: Optional[str] = None
    industry: Optional[str] = None

class CompanyResponse(CompanyBase):
    id: int
    
    # This allows Pydantic to read data directly from SQLAlchemy DB models later
    class Config:
        from_attributes = True

class CompanySearchRequest(BaseModel):
    company_name: str
