from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth_utils import (
    create_access_token,
    get_current_student,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import MockAttempt, Student
from app.schemas import (
    AuthTokenResponse,
    StudentLoginRequest,
    StudentResponse,
    StudentSignupRequest,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def _to_student_response(student: Student) -> StudentResponse:
    return StudentResponse(
        id=student.id,
        full_name=student.full_name,
        roll_number=student.roll_number,
        email=student.email,
        branch=student.branch,
        cgpa=float(student.cgpa) if student.cgpa is not None else None,
        created_at=student.created_at,
    )


def _link_existing_attempts_to_student(db: Session, student: Student) -> None:
    """Attach any previously recorded mock attempts matching this roll_number to student.id."""
    if not student.roll_number:
        return
    (
        db.query(MockAttempt)
        .filter(
            MockAttempt.student_id.is_(None),
            func.lower(MockAttempt.student_roll_number) == student.roll_number.strip().lower(),
        )
        .update({"student_id": student.id}, synchronize_session=False)
    )


@router.post("/signup", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def signup_student(payload: StudentSignupRequest, db: Session = Depends(get_db)):
    """
    Register a new student account in PostgreSQL and return a bearer access token.
    Links any past mock attempts matching the student's roll number.
    """
    full_name = payload.full_name.strip()
    roll_number = payload.roll_number.strip()
    email = payload.email.strip().lower() if payload.email and payload.email.strip() else None
    branch = payload.branch.strip() if payload.branch and payload.branch.strip() else None

    if not full_name or not roll_number:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Full name and roll number cannot be blank.",
        )

    existing_roll = (
        db.query(Student).filter(func.lower(Student.roll_number) == roll_number.lower()).first()
    )
    if existing_roll:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with roll number '{roll_number}' already exists. Please log in.",
        )

    if email:
        existing_email = db.query(Student).filter(func.lower(Student.email) == email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{email}' already exists.",
            )

    student = Student(
        full_name=full_name,
        roll_number=roll_number,
        email=email,
        branch=branch,
        cgpa=payload.cgpa,
        password_hash=hash_password(payload.password),
    )
    db.add(student)
    db.flush()
    _link_existing_attempts_to_student(db, student)
    db.commit()
    db.refresh(student)

    token = create_access_token(student.id, student.roll_number)
    return AuthTokenResponse(
        access_token=token,
        student=_to_student_response(student),
    )


@router.post("/login", response_model=AuthTokenResponse)
def login_student(payload: StudentLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate an existing student by roll number or email and return a bearer token.
    """
    ident = payload.identifier.strip().lower()
    student = (
        db.query(Student)
        .filter(
            or_(
                func.lower(Student.roll_number) == ident,
                func.lower(Student.email) == ident,
            )
        )
        .first()
    )

    if not student or not verify_password(payload.password, student.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid roll number/email or password.",
        )

    _link_existing_attempts_to_student(db, student)
    db.commit()
    db.refresh(student)

    token = create_access_token(student.id, student.roll_number)
    return AuthTokenResponse(
        access_token=token,
        student=_to_student_response(student),
    )


@router.get("/me", response_model=StudentResponse)
def get_my_profile(current_student: Student = Depends(get_current_student)):
    """
    Return the currently logged-in student's profile from PostgreSQL.
    """
    return _to_student_response(current_student)

