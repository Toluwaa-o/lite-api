from typing import Annotated, Any, List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic.functional_validators import BeforeValidator
from bson import ObjectId
from datetime import datetime, timezone
import asyncio
from fastapi import HTTPException, status

# For handling MongoDB ObjectId in Pydantic v2
PyObjectId = Annotated[str, BeforeValidator(str)]


# Fixed company info - static structure
class CompanyInfoFixed(BaseModel):
    annual_revenue: str = Field(..., alias="annual revenue")
    venture_funding: str = Field(..., alias="venture funding")
    revenue_per_employee: str = Field(..., alias="revenue per employee")
    total_funding: str = Field(..., alias="total funding")
    current_valuation: str = Field(..., alias="current valuation")
    employee_count: str = Field(..., alias="employee count")
    investors: str
    industry: str


# Competitor data model
class CompetitorData(BaseModel):
    competitor_name: List[str] = Field(..., alias="Competitor Name")
    revenue: List[str] = Field(..., alias="Revenue")
    number_of_employees: List[str] = Field(..., alias="Number of Employees")
    employee_growth: List[str] = Field(..., alias="Employee Growth")
    total_funding: List[str] = Field(..., alias="Total Funding")
    valuation: List[str] = Field(..., alias="Valuation")


# Funding round model
class FundingRound(BaseModel):
    # Keeping as string for flexibility
    date: List[str] = Field(..., alias="Date")
    amount: List[str] = Field(..., alias="Amount")
    round: List[str] = Field(..., alias="Round")
    lead_investors: List[str] = Field(..., alias="Lead Investors")
    reference: List[str] = Field(..., alias="Reference")

# Main company model


class Company(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    company: str
    description: str
    country: str
    company_info_fixed: CompanyInfoFixed
    company_info: Dict[str, Any]
    competitors: CompetitorData
    funding: FundingRound
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "company": "Andela",
                "description": "Private marketplace for technical talent...",
                "country": "Nigeria",
                "company_info_fixed": {
                    "annual revenue": "$246.4M",
                    "venture funding": "$100.0M",
                    "revenue per employee": "$200,20",
                    "total funding": "$381M.",
                    "current valuation": "$1.5B.",
                    "employee count": "-44%",
                    "investors": "53",
                    "industry": "HRTech"
                },
                # ... rest of example data ...
            }
        }
    )
