from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models import AttemptAnswer, Company, MockAttempt, Question
from app.rag.retriever import search_company_docs

# Friendly aliases so searches like "hrc" resolve cleanly
COMPANY_ALIASES = {
    "hrc": "highradius",
    "highradius (hrc)": "highradius",
    "techmahindra": "tech mahindra",
}


def _find_company(db, company_name: str):
    """Case-insensitive lookup helper for a company by name (with alias support)."""
    cleaned = company_name.strip().lower()
    lookup_name = COMPANY_ALIASES.get(cleaned, cleaned)
    company = db.query(Company).filter(func.lower(Company.name) == lookup_name).first()
    if company:
        return company
    return db.query(Company).filter(Company.name.ilike(f"%{lookup_name}%")).first()


def list_all_companies() -> dict:
    """List all registered companies from PostgreSQL."""
    db = SessionLocal()
    try:
        companies = db.query(Company).order_by(Company.name.asc()).all()
        return {
            "total": len(companies),
            "companies": [
                {
                    "id": c.id,
                    "name": c.name,
                    "industry": c.industry,
                    "has_eligibility": c.eligibility is not None,
                    "rounds_count": len(c.selection_rounds),
                }
                for c in companies
            ],
        }
    except SQLAlchemyError as exc:
        return {"error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def get_company_details(company_name: str) -> dict:
    """Retrieve general company details from the PostgreSQL database."""
    db = SessionLocal()
    try:
        company = _find_company(db, company_name)
        if not company:
            return {"error": f"Company '{company_name}' not found in database."}

        return {
            "id": company.id,
            "name": company.name,
            "industry": company.industry,
            "description": company.description,
        }
    except SQLAlchemyError as exc:
        return {"error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def get_eligibility(company_name: str) -> dict:
    """Retrieve eligibility criteria for a company from the PostgreSQL database."""
    db = SessionLocal()
    try:
        company = _find_company(db, company_name)
        if not company or not company.eligibility:
            return {"error": f"Eligibility criteria for '{company_name}' not found."}

        elig = company.eligibility
        return {
            "company": company.name,
            "cgpa_cutoff": float(elig.cgpa_cutoff),
            "backlogs_allowed": elig.backlogs_allowed,
            "branches": elig.branches,
            "additional_notes": elig.additional_notes,
        }
    except SQLAlchemyError as exc:
        return {"error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def get_selection_process(company_name: str) -> dict:
    """Retrieve ordered recruitment rounds and selection process for a company from PostgreSQL."""
    db = SessionLocal()
    try:
        company = _find_company(db, company_name)
        if not company or not company.selection_rounds:
            return {"error": f"Selection process for '{company_name}' not found."}

        rounds = company.selection_rounds
        return {
            "company": company.name,
            "rounds": [r.round_name for r in rounds],
            "round_details": [
                {
                    "round_number": r.round_number,
                    "round_name": r.round_name,
                    "description": r.description,
                }
                for r in rounds
            ],
        }
    except SQLAlchemyError as exc:
        return {"error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def search_questions(
    company_name: str = "",
    category: str = "",
    topic: str = "",
    question_type: str = "",
    search: str = "",
    limit: int = 5,
) -> dict:
    """
    Search the PostgreSQL Question Bank (both MCQs and non-MCQ coding/theory questions).
    Preserves exact question_type (PYQ, PRACTICE, REPORTED) and original source.
    """
    db = SessionLocal()
    try:
        safe_limit = max(1, min(limit, 15))
        query = db.query(Question).options(joinedload(Question.company))

        if company_name and company_name.strip():
            cleaned = company_name.strip().lower()
            if cleaned in {"common", "common / multiple companies", "general"}:
                query = query.filter(Question.company_id.is_(None))
            else:
                comp = _find_company(db, company_name)
                if not comp:
                    return {
                        "total_matching": 0,
                        "questions": [],
                        "note": f"No company named '{company_name}' found.",
                    }
                query = query.filter(Question.company_id == comp.id)

        if category and category.strip():
            cleaned_cat = category.strip().lower()
            if cleaned_cat == "technical":
                query = query.filter(
                    func.lower(Question.category).in_(["technical", "cs foundations technical"])
                )
            else:
                query = query.filter(func.lower(Question.category) == cleaned_cat)

        if topic and topic.strip():
            query = query.filter(Question.topic.ilike(f"%{topic.strip()}%"))

        if question_type and question_type.strip():
            query = query.filter(func.lower(Question.question_type) == question_type.strip().lower())

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Question.question_text.ilike(pattern),
                    Question.topic.ilike(pattern),
                )
            )

        total = query.count()
        rows: List[Question] = query.order_by(Question.id.asc()).limit(safe_limit).all()

        return {
            "total_matching": total,
            "returned": len(rows),
            "questions": [
                {
                    "id": q.id,
                    "company": q.company.name if q.company else "Common",
                    "category": q.category,
                    "topic": q.topic,
                    "difficulty": q.difficulty,
                    "question_type": q.question_type,
                    "source": q.source,
                    "is_mcq": bool(q.correct_option),
                    "question_text": q.question_text,
                }
                for q in rows
            ],
            "note": "REPORTED denotes candidate-reported questions (not official verified company papers).",
        }
    except SQLAlchemyError as exc:
        return {"error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def get_student_performance(student_identifier: str) -> dict:
    """
    Retrieve aggregated mock test scores, category accuracy, and weakest topics
    for a student by roll number or name from PostgreSQL.
    """
    cleaned = (student_identifier or "").strip()
    if not cleaned:
        return {"error": "Student identifier (roll number or name) is required."}

    db = SessionLocal()
    try:
        lowered = cleaned.lower()
        attempts: List[MockAttempt] = (
            db.query(MockAttempt)
            .options(joinedload(MockAttempt.company))
            .filter(
                or_(
                    func.lower(MockAttempt.student_roll_number) == lowered,
                    func.lower(MockAttempt.student_name) == lowered,
                )
            )
            .order_by(MockAttempt.started_at.desc(), MockAttempt.id.desc())
            .all()
        )

        if not attempts:
            return {"error": f"No mock test attempts found for '{cleaned}'."}

        completed = [a for a in attempts if a.completed_at is not None]
        completed_ids = [a.id for a in completed]
        avg_score = (
            round(sum(float(a.score_percentage) for a in completed) / len(completed), 2)
            if completed
            else 0.0
        )
        best_score = round(max(float(a.score_percentage) for a in completed), 2) if completed else 0.0

        cat_stats: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
        topic_stats: Dict[Tuple[str, str], List[int]] = defaultdict(lambda: [0, 0])

        if completed_ids:
            answers = (
                db.query(AttemptAnswer)
                .options(joinedload(AttemptAnswer.question))
                .filter(AttemptAnswer.attempt_id.in_(completed_ids))
                .all()
            )
            for aa in answers:
                q = aa.question
                right = 1 if aa.is_correct else 0
                cat_stats[q.category][0] += 1
                cat_stats[q.category][1] += right
                topic_stats[(q.topic or "General", q.category)][0] += 1
                topic_stats[(q.topic or "General", q.category)][1] += right

        weak_topics = [
            {
                "topic": topic,
                "category": cat,
                "attempted": counts[0],
                "correct": counts[1],
                "accuracy_percentage": round((counts[1] / counts[0]) * 100, 2) if counts[0] else 0.0,
            }
            for (topic, cat), counts in sorted(
                topic_stats.items(),
                key=lambda item: (item[1][1] / item[1][0] if item[1][0] else 0.0),
            )
        ]

        return {
            "student_identifier": cleaned,
            "student_name": attempts[0].student_name,
            "student_roll_number": attempts[0].student_roll_number,
            "total_attempts": len(attempts),
            "completed_attempts": len(completed),
            "average_score_percentage": avg_score,
            "best_score_percentage": best_score,
            "category_accuracy": [
                {
                    "category": cat,
                    "attempted": counts[0],
                    "correct": counts[1],
                    "accuracy_percentage": round((counts[1] / counts[0]) * 100, 2)
                    if counts[0]
                    else 0.0,
                }
                for cat, counts in sorted(cat_stats.items())
            ],
            "weakest_topics": weak_topics[:5],
        }
    except SQLAlchemyError as exc:
        return {"error": f"Database error: {str(exc)}"}
    finally:
        db.close()


def search_recruitment_docs(query: str, company_name: Optional[str] = None, top_k: int = 4) -> dict:
    """
    Search unstructured company recruitment PDFs, brochures, KIIT notices, and markdown notes
    for details such as CTC packages, deadlines, exam syllabi, role responsibilities, and rules.
    """
    return search_company_docs(query=query, company_name=company_name, top_k=top_k)
