from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth_utils import get_current_student_optional
from app.database import get_db
from app.models import AttemptAnswer, Company, MockAttempt, Question, Student
from app.schemas import (
    MockAnswerResult,
    MockQuestionOut,
    MockStartRequest,
    MockStartResponse,
    MockSubmitRequest,
    MockSubmitResponse,
)

router = APIRouter(
    prefix="/mock",
    tags=["Mock Tests"],
)

COMPANY_ALIASES = {
    "hrc": "highradius",
    "highradius (hrc)": "highradius",
    "techmahindra": "tech mahindra",
}


def _clean_opt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip().upper()
    return cleaned if cleaned else None


def _to_mock_question_out(q: Question) -> MockQuestionOut:
    """
    Serialize Question into MockQuestionOut.
    Never exposes correct_option or explanation.
    """
    return MockQuestionOut(
        id=q.id,
        company_id=q.company_id,
        company_name=q.company.name if q.company else None,
        category=q.category,
        topic=q.topic,
        difficulty=q.difficulty,
        question_type=q.question_type,
        question_text=q.question_text,
        option_a=q.option_a,
        option_b=q.option_b,
        option_c=q.option_c,
        option_d=q.option_d,
    )


def _build_submit_response(attempt: MockAttempt, answers: List[AttemptAnswer]) -> MockSubmitResponse:
    """Build detailed graded MockSubmitResponse after submission."""
    results: List[MockAnswerResult] = []
    for aa in answers:
        q = aa.question
        results.append(
            MockAnswerResult(
                question_id=q.id,
                question_text=q.question_text,
                category=q.category,
                topic=q.topic,
                selected_option=_clean_opt(aa.selected_option),
                correct_option=_clean_opt(q.correct_option),
                is_correct=bool(aa.is_correct),
                explanation=q.explanation,
            )
        )

    return MockSubmitResponse(
        attempt_id=attempt.id,
        student_name=attempt.student_name,
        student_roll_number=attempt.student_roll_number,
        total_questions=attempt.total_questions,
        correct_answers=attempt.correct_answers,
        score_percentage=float(attempt.score_percentage),
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        time_taken_seconds=attempt.time_taken_seconds,
        results=results,
    )


@router.post("/start", response_model=MockStartResponse, status_code=status.HTTP_201_CREATED)
def start_mock_test(
    payload: MockStartRequest,
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student_optional),
):
    """
    Generate a new dynamic MCQ mock test session.
    Selects only MCQs with a valid correct_option and never returns answers or explanations.
    Automatically associates the attempt with the logged-in student (if authenticated)
    or matches by roll number in PostgreSQL.
    """
    if current_student:
        student_name = (payload.student_name or current_student.full_name).strip()
        student_roll = (
            payload.student_roll_number.strip()
            if payload.student_roll_number and payload.student_roll_number.strip()
            else current_student.roll_number
        )
        student_id = current_student.id
    else:
        student_name = (payload.student_name or "").strip()
        if not student_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="student_name must not be empty.",
            )
        student_roll = (
            payload.student_roll_number.strip()
            if payload.student_roll_number and payload.student_roll_number.strip()
            else None
        )
        matched_student = (
            db.query(Student).filter(func.lower(Student.roll_number) == student_roll.lower()).first()
            if student_roll
            else None
        )
        student_id = matched_student.id if matched_student else None

    # Strictly restrict mock tests to complete MCQs with a valid answer key
    query = (
        db.query(Question)
        .options(joinedload(Question.company))
        .filter(
            Question.correct_option.isnot(None),
            func.trim(Question.correct_option).in_(["A", "B", "C", "D"]),
            Question.option_a.isnot(None),
            Question.option_b.isnot(None),
            Question.option_c.isnot(None),
            Question.option_d.isnot(None),
        )
    )

    resolved_company: Optional[Company] = None
    if payload.company_name and payload.company_name.strip():
        cleaned_company = payload.company_name.strip().lower()
        lookup_name = COMPANY_ALIASES.get(cleaned_company, cleaned_company)
        resolved_company = db.query(Company).filter(func.lower(Company.name) == lookup_name).first()
        if not resolved_company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company '{payload.company_name}' not found.",
            )
        query = query.filter(Question.company_id == resolved_company.id)

    attempt_category = "Mixed"
    if payload.category and payload.category.strip():
        cleaned_cat = payload.category.strip()
        if cleaned_cat.lower() != "mixed":
            attempt_category = cleaned_cat
            if cleaned_cat.lower() in {"technical", "cs foundations technical"}:
                query = query.filter(
                    func.lower(Question.category).in_(["technical", "cs foundations technical"])
                )
            else:
                query = query.filter(func.lower(Question.category) == cleaned_cat.lower())

    if payload.difficulty:
        query = query.filter(Question.difficulty == payload.difficulty)

    selected_questions: List[Question] = (
        query.order_by(func.random()).limit(payload.num_questions).all()
    )

    if not selected_questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No valid MCQ questions matched the selected filters "
                f"(company={resolved_company.name if resolved_company else 'Any'}, "
                f"category={attempt_category}, difficulty={payload.difficulty or 'Any'}). "
                "Try using broader filters such as Mixed category or omitting company filter."
            ),
        )

    attempt = MockAttempt(
        student_id=student_id,
        student_name=student_name,
        student_roll_number=student_roll,
        company_id=resolved_company.id if resolved_company else None,
        category=attempt_category,
        total_questions=len(selected_questions),
        correct_answers=0,
        score_percentage=0.00,
    )
    db.add(attempt)
    db.flush()

    for q in selected_questions:
        db.add(
            AttemptAnswer(
                attempt_id=attempt.id,
                question_id=q.id,
                selected_option=None,
                written_answer=None,
                is_correct=False,
            )
        )

    db.commit()
    db.refresh(attempt)

    return MockStartResponse(
        attempt_id=attempt.id,
        student_name=attempt.student_name,
        student_roll_number=attempt.student_roll_number,
        company_name=resolved_company.name if resolved_company else None,
        category=attempt.category,
        total_questions=attempt.total_questions,
        started_at=attempt.started_at,
        questions=[_to_mock_question_out(q) for q in selected_questions],
    )


@router.post("/{attempt_id}/submit", response_model=MockSubmitResponse)
def submit_mock_test(
    attempt_id: int,
    payload: MockSubmitRequest,
    db: Session = Depends(get_db),
):
    """
    Submit answers for an active mock test attempt, evaluate correctness against
    stored MCQs, persist per-question results, and reveal answers + explanations.
    """
    attempt = db.query(MockAttempt).filter(MockAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock attempt {attempt_id} not found.",
        )

    if attempt.completed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mock attempt {attempt_id} has already been submitted.",
        )

    attempt_answers: List[AttemptAnswer] = (
        db.query(AttemptAnswer)
        .options(joinedload(AttemptAnswer.question))
        .filter(AttemptAnswer.attempt_id == attempt.id)
        .order_by(AttemptAnswer.id.asc())
        .all()
    )

    if not attempt_answers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mock attempt {attempt_id} has no assigned questions.",
        )

    assigned_by_qid: Dict[int, AttemptAnswer] = {aa.question_id: aa for aa in attempt_answers}
    submitted_by_qid = {ans.question_id: ans for ans in payload.answers}

    unknown_qids = [qid for qid in submitted_by_qid if qid not in assigned_by_qid]
    if unknown_qids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question ID(s) {unknown_qids} do not belong to mock attempt {attempt_id}.",
        )

    correct_count = 0
    for aa in attempt_answers:
        submitted = submitted_by_qid.get(aa.question_id)
        selected_opt = _clean_opt(submitted.selected_option) if submitted else None
        written_ans = submitted.written_answer.strip() if submitted and submitted.written_answer else None
        correct_opt = _clean_opt(aa.question.correct_option)

        is_correct = bool(selected_opt and correct_opt and selected_opt == correct_opt)
        if is_correct:
            correct_count += 1

        aa.selected_option = selected_opt
        aa.written_answer = written_ans
        aa.is_correct = is_correct

    total_q = attempt.total_questions
    score_pct = round((correct_count / total_q) * 100, 2)

    attempt.correct_answers = correct_count
    attempt.score_percentage = score_pct
    attempt.completed_at = func.current_timestamp()
    db.flush()
    db.refresh(attempt)

    if payload.time_taken_seconds is not None:
        attempt.time_taken_seconds = payload.time_taken_seconds
    elif attempt.completed_at and attempt.started_at:
        elapsed = int((attempt.completed_at - attempt.started_at).total_seconds())
        attempt.time_taken_seconds = max(0, elapsed)

    db.commit()
    db.refresh(attempt)

    refreshed_answers: List[AttemptAnswer] = (
        db.query(AttemptAnswer)
        .options(joinedload(AttemptAnswer.question))
        .filter(AttemptAnswer.attempt_id == attempt.id)
        .order_by(AttemptAnswer.id.asc())
        .all()
    )

    return _build_submit_response(attempt, refreshed_answers)


@router.get("/{attempt_id}", response_model=Union[MockSubmitResponse, MockStartResponse])
def get_mock_attempt(attempt_id: int, db: Session = Depends(get_db)):
    """
    Fetch a mock attempt by ID.
    Before submission, returns only MockQuestionOut (without answers or explanations).
    After submission, returns the full graded MockSubmitResponse.
    """
    attempt = (
        db.query(MockAttempt)
        .options(joinedload(MockAttempt.company))
        .filter(MockAttempt.id == attempt_id)
        .first()
    )
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock attempt {attempt_id} not found.",
        )

    attempt_answers: List[AttemptAnswer] = (
        db.query(AttemptAnswer)
        .options(joinedload(AttemptAnswer.question).joinedload(Question.company))
        .filter(AttemptAnswer.attempt_id == attempt.id)
        .order_by(AttemptAnswer.id.asc())
        .all()
    )

    if attempt.completed_at is None:
        return MockStartResponse(
            attempt_id=attempt.id,
            student_name=attempt.student_name,
            student_roll_number=attempt.student_roll_number,
            company_name=attempt.company.name if attempt.company else None,
            category=attempt.category,
            total_questions=attempt.total_questions,
            started_at=attempt.started_at,
            questions=[_to_mock_question_out(aa.question) for aa in attempt_answers],
        )

    return _build_submit_response(attempt, attempt_answers)
