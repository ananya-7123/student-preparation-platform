from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Company, Question
from app.schemas import (
    DifficultyLevel,
    QuestionBankListResponse,
    QuestionCreate,
    QuestionResponse,
)

router = APIRouter(
    prefix="/questions",
    tags=["Questions"],
)

COMPANY_ALIASES = {
    "hrc": "highradius",
    "highradius (hrc)": "highradius",
    "techmahindra": "tech mahindra",
}

COMMON_COMPANY_KEYWORDS = {"common", "common / multiple companies", "general", "none"}


def _to_question_response(q: Question) -> QuestionResponse:
    """Serialize a Question ORM object (with optional joined Company) into QuestionResponse."""
    return QuestionResponse(
        id=q.id,
        company_id=q.company_id,
        company_name=q.company.name if q.company else None,
        category=q.category,
        topic=q.topic,
        difficulty=q.difficulty,
        question_type=q.question_type,
        year=q.year,
        source=q.source,
        question_text=q.question_text,
        option_a=q.option_a,
        option_b=q.option_b,
        option_c=q.option_c,
        option_d=q.option_d,
        correct_option=q.correct_option.strip() if q.correct_option else None,
        explanation=q.explanation,
        created_at=q.created_at,
    )


@router.get("/", response_model=QuestionBankListResponse)
def list_questions(
    company_name: Optional[str] = Query(
        default=None,
        description="Filter by company name (e.g., TCS, Accenture, Amazon) or 'Common' for general questions.",
    ),
    category: Optional[str] = Query(
        default=None,
        description="Filter by category/section (e.g., Aptitude, Reasoning, Verbal, Technical, CS Foundations Technical, Coding).",
    ),
    topic: Optional[str] = Query(
        default=None,
        description="Filter by topic (case-insensitive partial match).",
    ),
    difficulty: Optional[DifficultyLevel] = Query(
        default=None,
        description="Filter by difficulty (Easy, Medium, Hard).",
    ),
    question_type: Optional[str] = Query(
        default=None,
        description="Filter by question type/status (PYQ, PRACTICE, REPORTED).",
    ),
    mcq_only: Optional[bool] = Query(
        default=None,
        description="True = only MCQs with correct_option; False = only non-MCQs; omitted = both.",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Search keyword across question text, topic, and source.",
    ),
    limit: int = Query(default=50, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List questions from the PostgreSQL Question Bank (both MCQ and non-MCQ questions)
    with optional filtering and pagination.
    """
    query = db.query(Question).options(joinedload(Question.company))

    if company_name:
        cleaned_company = company_name.strip().lower()
        if cleaned_company in COMMON_COMPANY_KEYWORDS:
            query = query.filter(Question.company_id.is_(None))
        else:
            lookup_name = COMPANY_ALIASES.get(cleaned_company, cleaned_company)
            company = db.query(Company).filter(func.lower(Company.name) == lookup_name).first()
            if not company:
                return QuestionBankListResponse(total=0, questions=[])
            query = query.filter(Question.company_id == company.id)

    if category:
        cleaned_cat = category.strip().lower()
        if cleaned_cat == "technical":
            query = query.filter(
                func.lower(Question.category).in_(["technical", "cs foundations technical"])
            )
        else:
            query = query.filter(func.lower(Question.category) == cleaned_cat)

    if topic:
        query = query.filter(Question.topic.ilike(f"%{topic.strip()}%"))

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    if question_type:
        query = query.filter(func.lower(Question.question_type) == question_type.strip().lower())

    if mcq_only is True:
        query = query.filter(Question.correct_option.isnot(None))
    elif mcq_only is False:
        query = query.filter(Question.correct_option.is_(None))

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Question.question_text.ilike(pattern),
                Question.topic.ilike(pattern),
                Question.source.ilike(pattern),
            )
        )

    total = query.count()
    rows: List[Question] = query.order_by(Question.id.asc()).offset(offset).limit(limit).all()

    return QuestionBankListResponse(
        total=total,
        questions=[_to_question_response(row) for row in rows],
    )


@router.get("/filters")
def get_question_filters(db: Session = Depends(get_db)):
    """
    Return available filter values and Question Bank summary counts
    for UI dropdowns and exploration.
    """
    company_names = [
        row[0]
        for row in (
            db.query(Company.name)
            .join(Question, Question.company_id == Company.id)
            .distinct()
            .order_by(Company.name.asc())
            .all()
        )
    ]

    categories = [
        row[0]
        for row in db.query(Question.category).distinct().order_by(Question.category.asc()).all()
    ]

    topics = [
        row[0]
        for row in (
            db.query(Question.topic)
            .filter(Question.topic.isnot(None))
            .distinct()
            .order_by(Question.topic.asc())
            .all()
        )
    ]

    question_types = [
        row[0]
        for row in db.query(Question.question_type).distinct().order_by(Question.question_type.asc()).all()
    ]

    total_questions = db.query(func.count(Question.id)).scalar() or 0
    total_mcqs = (
        db.query(func.count(Question.id))
        .filter(Question.correct_option.isnot(None))
        .scalar()
        or 0
    )

    return {
        "total_questions": total_questions,
        "total_mcqs": total_mcqs,
        "total_non_mcqs": total_questions - total_mcqs,
        "companies": company_names,
        "has_common_questions": (
            db.query(Question.id).filter(Question.company_id.is_(None)).first() is not None
        ),
        "categories": categories,
        "topics": topics,
        "difficulties": ["Easy", "Medium", "Hard"],
        "question_types": question_types,
    }


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(question_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single question by its ID.
    """
    question = (
        db.query(Question)
        .options(joinedload(Question.company))
        .filter(Question.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with id {question_id} not found.",
        )
    return _to_question_response(question)


@router.post("/", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)):
    """
    Add a new question (MCQ or non-MCQ) to the PostgreSQL Question Bank.
    """
    if payload.company_id is not None:
        company = db.query(Company).filter(Company.id == payload.company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with id {payload.company_id} not found.",
            )

    if payload.correct_option is not None and not all(
        [payload.option_a, payload.option_b, payload.option_c, payload.option_d]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="All four options (option_a, option_b, option_c, option_d) are required when correct_option is specified.",
        )

    db_question = Question(
        company_id=payload.company_id,
        category=payload.category.strip(),
        topic=payload.topic.strip() if payload.topic else None,
        difficulty=payload.difficulty,
        question_type=payload.question_type,
        year=payload.year,
        source=payload.source.strip() if payload.source else None,
        question_text=payload.question_text.strip(),
        option_a=payload.option_a,
        option_b=payload.option_b,
        option_c=payload.option_c,
        option_d=payload.option_d,
        correct_option=payload.correct_option,
        explanation=payload.explanation,
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    created = (
        db.query(Question)
        .options(joinedload(Question.company))
        .filter(Question.id == db_question.id)
        .first()
    )
    return _to_question_response(created)

