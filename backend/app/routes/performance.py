from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.auth_utils import get_current_student
from app.database import get_db
from app.models import AttemptAnswer, MockAttempt, Student
from app.schemas import (
    AttemptSummary,
    CategoryBreakdown,
    StudentPerformanceResponse,
    TopicBreakdown,
)

router = APIRouter(
    prefix="/performance",
    tags=["Performance"],
)


@router.get("/")
def list_recent_performance_attempts(
    limit: int = Query(default=20, ge=1, le=100),
    completed_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """
    List recent mock test attempts across students (useful for overview dashboards).
    """
    query = db.query(MockAttempt).options(joinedload(MockAttempt.company))
    if completed_only:
        query = query.filter(MockAttempt.completed_at.isnot(None))

    attempts = (
        query.order_by(MockAttempt.started_at.desc(), MockAttempt.id.desc())
        .limit(limit)
        .all()
    )

    return {
        "total": len(attempts),
        "attempts": [
            {
                "attempt_id": a.id,
                "student_name": a.student_name,
                "student_roll_number": a.student_roll_number,
                "company_name": a.company.name if a.company else None,
                "category": a.category,
                "total_questions": a.total_questions,
                "correct_answers": a.correct_answers,
                "score_percentage": float(a.score_percentage),
                "started_at": a.started_at,
                "completed_at": a.completed_at,
                "time_taken_seconds": a.time_taken_seconds,
            }
            for a in attempts
        ],
    }


@router.get("/me", response_model=StudentPerformanceResponse)
def get_my_performance(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """
    Retrieve aggregated performance analytics for the currently authenticated student.
    """
    return get_student_performance(current_student.roll_number, db=db)


@router.get("/{student_identifier}", response_model=StudentPerformanceResponse)
def get_student_performance(student_identifier: str, db: Session = Depends(get_db)):
    """
    Retrieve aggregated performance metrics, category-wise accuracy,
    topic-wise breakdown (weakest topics first), and recent mock test history
    matched by student roll number, student name, or registered student_id.
    """
    cleaned_id = student_identifier.strip()
    lowered_id = cleaned_id.lower()

    matched_student = (
        db.query(Student)
        .filter(
            or_(
                func.lower(Student.roll_number) == lowered_id,
                func.lower(Student.full_name) == lowered_id,
            )
        )
        .first()
    )

    conditions = [
        func.lower(MockAttempt.student_roll_number) == lowered_id,
        func.lower(MockAttempt.student_name) == lowered_id,
    ]
    if matched_student:
        conditions.append(MockAttempt.student_id == matched_student.id)

    attempts: List[MockAttempt] = (
        db.query(MockAttempt)
        .options(joinedload(MockAttempt.company))
        .filter(or_(*conditions))
        .order_by(MockAttempt.started_at.desc(), MockAttempt.id.desc())
        .all()
    )

    if not attempts:
        return StudentPerformanceResponse(
            student_identifier=cleaned_id,
            total_attempts=0,
            completed_attempts=0,
            total_questions_answered=0,
            total_correct_answers=0,
            average_score_percentage=0.0,
            best_score_percentage=0.0,
            category_breakdown=[],
            topic_breakdown=[],
            recent_attempts=[],
        )

    completed_list = [a for a in attempts if a.completed_at is not None]
    completed_ids = [a.id for a in completed_list]

    if completed_list:
        avg_score = round(
            sum(float(a.score_percentage) for a in completed_list) / len(completed_list),
            2,
        )
        best_score = round(max(float(a.score_percentage) for a in completed_list), 2)
    else:
        avg_score = 0.0
        best_score = 0.0

    # Aggregate category & topic stats ONLY from completed attempts
    cat_stats: Dict[str, List[int]] = defaultdict(lambda: [0, 0])  # [attempted, correct]
    topic_stats: Dict[Tuple[str, str], List[int]] = defaultdict(lambda: [0, 0])
    total_q_answered = 0
    total_correct = 0

    if completed_ids:
        completed_answers: List[AttemptAnswer] = (
            db.query(AttemptAnswer)
            .options(joinedload(AttemptAnswer.question))
            .filter(AttemptAnswer.attempt_id.in_(completed_ids))
            .all()
        )
        for aa in completed_answers:
            q = aa.question
            total_q_answered += 1
            is_right = 1 if aa.is_correct else 0
            total_correct += is_right

            cat_stats[q.category][0] += 1
            cat_stats[q.category][1] += is_right

            topic_name = q.topic or "General"
            topic_stats[(topic_name, q.category)][0] += 1
            topic_stats[(topic_name, q.category)][1] += is_right

    category_breakdown = [
        CategoryBreakdown(
            category=cat,
            attempted=counts[0],
            correct=counts[1],
            accuracy_percentage=round((counts[1] / counts[0]) * 100, 2) if counts[0] else 0.0,
        )
        for cat, counts in sorted(cat_stats.items(), key=lambda item: item[0].lower())
    ]

    topic_breakdown = [
        TopicBreakdown(
            topic=topic_name,
            category=cat_name,
            attempted=counts[0],
            correct=counts[1],
            accuracy_percentage=round((counts[1] / counts[0]) * 100, 2) if counts[0] else 0.0,
        )
        for (topic_name, cat_name), counts in sorted(
            topic_stats.items(),
            key=lambda item: (
                round((item[1][1] / item[1][0]) * 100, 2) if item[1][0] else 0.0,
                -item[1][0],
                item[0][0].lower(),
            ),
        )
    ]

    recent_attempts = [
        AttemptSummary(
            attempt_id=a.id,
            company_name=a.company.name if a.company else None,
            category=a.category,
            total_questions=a.total_questions,
            correct_answers=a.correct_answers,
            score_percentage=float(a.score_percentage),
            started_at=a.started_at,
            completed_at=a.completed_at,
            time_taken_seconds=a.time_taken_seconds,
        )
        for a in attempts[:10]
    ]

    return StudentPerformanceResponse(
        student_identifier=cleaned_id,
        total_attempts=len(attempts),
        completed_attempts=len(completed_list),
        total_questions_answered=total_q_answered,
        total_correct_answers=total_correct,
        average_score_percentage=avg_score,
        best_score_percentage=best_score,
        category_breakdown=category_breakdown,
        topic_breakdown=topic_breakdown,
        recent_attempts=recent_attempts,
    )

