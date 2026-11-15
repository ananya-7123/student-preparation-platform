from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.agent.graph import run_placement_agent
from app.auth_utils import get_current_student_optional
from app.models import Student
from app.rag.retriever import get_rag_status, search_company_docs
from app.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    RagSearchResponse,
    RagStatusResponse,
)

router = APIRouter(
    prefix="/agent",
    tags=["AI Agent & RAG"],
)


@router.post("/chat", response_model=AgentChatResponse)
def chat_with_placement_agent(
    payload: AgentChatRequest,
    current_student: Optional[Student] = Depends(get_current_student_optional),
):
    """
    Send a student placement question to the Placement Preparation Agent.
    Uses LangGraph + Gemini when GEMINI_API_KEY is configured, or falls back cleanly
    to grounded PostgreSQL + RAG document retrieval so accurate answers always work.
    """
    cleaned_message = payload.message.strip()
    if not cleaned_message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="message cannot be empty.",
        )

    effective_student_id = payload.student_identifier
    if not effective_student_id and current_student:
        effective_student_id = current_student.roll_number

    history_dicts = [m.model_dump() for m in payload.history]
    result = run_placement_agent(
        user_query=cleaned_message,
        student_identifier=effective_student_id,
        company_name=payload.company_name,
        history=history_dicts,
    )
    return AgentChatResponse(**result)


@router.get("/rag/search", response_model=RagSearchResponse)
def rag_search(
    query: str = Query(..., min_length=1, description="Search query over company notes and PDFs"),
    company_name: Optional[str] = Query(default=None, description="Optional company filter (e.g. TCS, IBM, HighRadius)"),
    top_k: int = Query(default=4, ge=1, le=10),
):
    """
    Directly query the RAG index over resources/companies/ notes and recruitment PDFs.
    """
    res = search_company_docs(query=query, company_name=company_name, top_k=top_k)
    if "error" in res:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=res["error"])
    return RagSearchResponse(**res)


@router.get("/rag/status", response_model=RagStatusResponse)
def rag_status():
    """
    Inspect RAG index statistics (indexed markdown notes, PDFs, chunk count, and warnings).
    """
    return RagStatusResponse(**get_rag_status())

