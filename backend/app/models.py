from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    industry = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        nullable=True,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    # Relationships
    eligibility = relationship(
        "EligibilityCriteria",
        back_populates="company",
        uselist=False,
        cascade="all, delete-orphan",
    )
    selection_rounds = relationship(
        "SelectionRound",
        back_populates="company",
        order_by="SelectionRound.round_number",
        cascade="all, delete-orphan",
    )
    questions = relationship("Question", back_populates="company")
    mock_attempts = relationship("MockAttempt", back_populates="company")


class EligibilityCriteria(Base):
    __tablename__ = "eligibility_criteria"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    cgpa_cutoff = Column(Numeric(4, 2), nullable=False)
    backlogs_allowed = Column(Integer, nullable=False, default=0, server_default="0")
    branches = Column(Text, nullable=False)
    additional_notes = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("cgpa_cutoff >= 0 AND cgpa_cutoff <= 10", name="chk_cgpa_cutoff"),
        CheckConstraint("backlogs_allowed >= 0", name="chk_backlogs_allowed"),
    )

    company = relationship("Company", back_populates="eligibility")


class SelectionRound(Base):
    __tablename__ = "selection_rounds"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_number = Column(Integer, nullable=False)
    round_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("round_number >= 1", name="chk_round_number"),
        UniqueConstraint("company_id", "round_number", name="uq_company_round"),
    )

    company = relationship("Company", back_populates="selection_rounds")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category = Column(String(50), nullable=False)
    topic = Column(String(100), nullable=True)
    difficulty = Column(String(20), nullable=False, default="Medium", server_default="Medium")
    question_type = Column(String(20), nullable=False, default="Practice", server_default="Practice")
    year = Column(Integer, nullable=True)
    source = Column(Text, nullable=True)
    question_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=True)
    option_b = Column(Text, nullable=True)
    option_c = Column(Text, nullable=True)
    option_d = Column(Text, nullable=True)
    correct_option = Column(CHAR(1), nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    __table_args__ = (
        CheckConstraint("difficulty IN ('Easy', 'Medium', 'Hard')", name="chk_question_difficulty"),
        CheckConstraint(
            "question_type IN ('PYQ', 'Practice', 'PRACTICE', 'REPORTED')",
            name="chk_question_type",
        ),
        CheckConstraint("year IS NULL OR (year >= 2000 AND year <= 2100)", name="chk_question_year"),
        CheckConstraint(
            "correct_option IS NULL OR correct_option IN ('A', 'B', 'C', 'D')",
            name="chk_question_correct_option",
        ),
    )

    company = relationship("Company", back_populates="questions")
    attempt_answers = relationship(
        "AttemptAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    roll_number = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(150), nullable=True, unique=True)
    branch = Column(String(80), nullable=True)
    cgpa = Column(Numeric(4, 2), nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    __table_args__ = (
        CheckConstraint("cgpa IS NULL OR (cgpa >= 0 AND cgpa <= 10)", name="chk_student_cgpa"),
    )

    attempts = relationship("MockAttempt", back_populates="student")


class MockAttempt(Base):
    __tablename__ = "mock_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    student_name = Column(String(100), nullable=False, index=True)
    student_roll_number = Column(String(50), nullable=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category = Column(String(50), nullable=False, default="Mixed", server_default="Mixed")
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False, default=0, server_default="0")
    score_percentage = Column(Numeric(5, 2), nullable=False, default=0.00, server_default="0.00")
    started_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    completed_at = Column(DateTime, nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint("total_questions > 0", name="chk_total_questions"),
        CheckConstraint("correct_answers >= 0", name="chk_correct_answers"),
        CheckConstraint("score_percentage >= 0 AND score_percentage <= 100", name="chk_score_percentage"),
        CheckConstraint("time_taken_seconds IS NULL OR time_taken_seconds >= 0", name="chk_time_taken"),
        CheckConstraint("correct_answers <= total_questions", name="chk_correct_le_total"),
    )

    student = relationship("Student", back_populates="attempts")
    company = relationship("Company", back_populates="mock_attempts")
    answers = relationship(
        "AttemptAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(
        Integer,
        ForeignKey("mock_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selected_option = Column(CHAR(1), nullable=True)
    written_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False, default=False, server_default="false")

    __table_args__ = (
        CheckConstraint(
            "selected_option IS NULL OR selected_option IN ('A', 'B', 'C', 'D')",
            name="chk_selected_option",
        ),
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
    )

    attempt = relationship("MockAttempt", back_populates="answers")
    question = relationship("Question", back_populates="attempt_answers")

