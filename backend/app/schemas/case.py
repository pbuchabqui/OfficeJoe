from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class CasePartyCreate(BaseModel):
    name: str
    role: str
    cpf_cnpj: Optional[str] = None
    lawyer_name: Optional[str] = None
    lawyer_oab: Optional[str] = None


class CasePartyResponse(CasePartyCreate):
    id: str
    case_id: str
    model_config = {"from_attributes": True}


class CaseCreate(BaseModel):
    case_number: str
    case_type: str
    title: str
    description: Optional[str] = None
    court: Optional[str] = None
    court_district: Optional[str] = None
    judge_name: Optional[str] = None
    appointment_date: Optional[str] = None
    deadline_date: Optional[str] = None
    filing_date: Optional[str] = None
    honorarium_proposed: Optional[int] = None
    parties: List[CasePartyCreate] = []


class CaseUpdate(BaseModel):
    case_number: Optional[str] = None
    case_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    court: Optional[str] = None
    court_district: Optional[str] = None
    judge_name: Optional[str] = None
    deadline_date: Optional[str] = None
    honorarium_approved: Optional[int] = None


class CaseSummary(BaseModel):
    id: str
    case_number: str
    case_type: str
    status: str
    title: str
    court: Optional[str]
    deadline_date: Optional[str]
    responsible_user_id: Optional[str]
    model_config = {"from_attributes": True}


class CaseDetail(CaseSummary):
    description: Optional[str]
    court_district: Optional[str]
    judge_name: Optional[str]
    appointment_date: Optional[str]
    filing_date: Optional[str]
    honorarium_proposed: Optional[int]
    honorarium_approved: Optional[int]
    parties: List[CasePartyResponse] = []
    model_config = {"from_attributes": True}
