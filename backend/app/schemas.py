from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Company Schemas (Existing)
# ============================================================================

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


# ============================================================================
# Question Bank Schemas
# ============================================================================

DifficultyLevel = Literal["Easy", "Medium", "Hard"]
QuestionTypeValue = Literal["PYQ", "Practice", "PRACTICE", "REPORTED"]
OptionLetter = Literal["A", "B", "C", "D"]


class QuestionBase(BaseModel):
    company_id: Optional[int] = None
    category: str = Field(..., min_length=1, max_length=50)
    topic: Optional[str] = Field(default=None, max_length=100)
    difficulty: DifficultyLevel = "Medium"
    question_type: QuestionTypeValue = "Practice"
    year: Optional[int] = Field(default=None, ge=2000, le=2100)
    source: Optional[str] = None
    question_text: str = Field(..., min_length=1)
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None


class QuestionCreate(QuestionBase):
    correct_option: Optional[OptionLetter] = None
    explanation: Optional[str] = None


class QuestionResponse(QuestionBase):
    id: int
    company_name: Optional[str] = None
    correct_option: Optional[OptionLetter] = None
    explanation: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionBankListResponse(BaseModel):
    total: int
    questions: List[QuestionResponse]


# ============================================================================
# Mock Test Schemas
# ============================================================================

class MockQuestionOut(BaseModel):
    """
    Question payload sent during an active mock test.
    Intentionally excludes correct_option and explanation.
    """
    id: int
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    category: str
    topic: Optional[str] = None
    difficulty: str
    question_type: str
    question_text: str
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MockStartRequest(BaseModel):
    student_name: Optional[str] = Field(default=None, max_length=100)
    student_roll_number: Optional[str] = Field(default=None, max_length=50)
    company_name: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    num_questions: int = Field(default=5, ge=1, le=50)


class MockStartResponse(BaseModel):
    attempt_id: int
    student_name: str
    student_roll_number: Optional[str] = None
    company_name: Optional[str] = None
    category: str
    total_questions: int
    started_at: datetime
    questions: List[MockQuestionOut]


class MockAnswerSubmit(BaseModel):
    question_id: int
    selected_option: Optional[OptionLetter] = None
    written_answer: Optional[str] = None


class MockSubmitRequest(BaseModel):
    answers: List[MockAnswerSubmit]
    time_taken_seconds: Optional[int] = Field(default=None, ge=0)

    @field_validator("answers")
    @classmethod
    def check_unique_question_ids(cls, value: List[MockAnswerSubmit]) -> List[MockAnswerSubmit]:
        seen = set()
        for item in value:
            if item.question_id in seen:
                raise ValueError(f"Duplicate answer provided for question_id {item.question_id}.")
            seen.add(item.question_id)
        return value


class MockAnswerResult(BaseModel):
    question_id: int
    question_text: str
    category: str
    topic: Optional[str] = None
    selected_option: Optional[OptionLetter] = None
    correct_option: Optional[OptionLetter] = None
    is_correct: bool
    explanation: Optional[str] = None


class MockSubmitResponse(BaseModel):
    attempt_id: int
    student_name: str
    student_roll_number: Optional[str] = None
    total_questions: int
    correct_answers: int
    score_percentage: float
    started_at: datetime
    completed_at: datetime
    time_taken_seconds: Optional[int] = None
    results: List[MockAnswerResult]


# ============================================================================
# Performance Tracking Schemas
# ============================================================================

class AttemptSummary(BaseModel):
    attempt_id: int
    company_name: Optional[str] = None
    category: str
    total_questions: int
    correct_answers: int
    score_percentage: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    time_taken_seconds: Optional[int] = None


class CategoryBreakdown(BaseModel):
    category: str
    attempted: int
    correct: int
    accuracy_percentage: float


class TopicBreakdown(BaseModel):
    topic: str
    category: str
    attempted: int
    correct: int
    accuracy_percentage: float


class StudentPerformanceResponse(BaseModel):
    student_identifier: str
    total_attempts: int
    completed_attempts: int
    total_questions_answered: int
    total_correct_answers: int
    average_score_percentage: float
    best_score_percentage: float
    category_breakdown: List[CategoryBreakdown]
    topic_breakdown: List[TopicBreakdown]
    recent_attempts: List[AttemptSummary]


# ============================================================================
# AI Agent & RAG Schemas
# ============================================================================

class AgentChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    student_identifier: Optional[str] = Field(default=None, max_length=100)
    company_name: Optional[str] = Field(default=None, max_length=100)
    history: List[AgentChatMessage] = Field(default_factory=list)


class AgentChatResponse(BaseModel):
    response: str
    mode: str
    tools_used: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)


class RagChunkResult(BaseModel):
    chunk_id: int
    company: str
    doc_type: str
    source_file: str
    relative_path: str
    page: Optional[int] = None
    score: float
    content: str


class RagSearchResponse(BaseModel):
    query: str
    company_filter: Optional[str] = None
    pypdf_installed: bool
    total_results: int
    results: List[RagChunkResult]


class RagStatusResponse(BaseModel):
    pypdf_installed: bool
    indexed_files_count: int
    pdf_files_found: int
    pdf_files_extracted: int
    total_chunks: int
    indexed_companies: List[str]
    indexed_files: List[str]
    warnings: List[str]


# ============================================================================
# Student Authentication Schemas
# ============================================================================

class StudentSignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    roll_number: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[str] = Field(default=None, max_length=150)
    branch: Optional[str] = Field(default=None, max_length=80)
    cgpa: Optional[float] = Field(default=None, ge=0.0, le=10.0)


class StudentLoginRequest(BaseModel):
    identifier: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=128)


class StudentResponse(BaseModel):
    id: int
    full_name: str
    roll_number: str
    email: Optional[str] = None
    branch: Optional[str] = None
    cgpa: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    student: StudentResponse
