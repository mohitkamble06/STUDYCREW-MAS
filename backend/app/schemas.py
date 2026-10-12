"""Pydantic schemas for all agent inputs, outputs, and API contracts."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class ActivityType(str, Enum):
    LEARN = "learn"
    REVISE = "revise"
    PRACTICE = "practice"
    MOCK_TEST = "mock_test"


class AgentStatus(str, Enum):
    STARTED = "started"
    DONE = "done"
    ERROR = "error"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class UserLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ============================================================================
# Core Domain Models
# ============================================================================

class TopicBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    importance: int = Field(default=1, ge=1, le=3)
    mastery: float = Field(default=0.0, ge=0.0, le=1.0)


class TopicCreate(TopicBase):
    pass


class TopicRead(TopicBase):
    id: UUID
    course_id: UUID

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    exam_date: datetime
    hours_per_day: float = Field(..., gt=0, le=12)
    level: UserLevel = UserLevel.BEGINNER


class CourseCreate(CourseBase):
    topics: list[TopicCreate] = Field(default_factory=list, min_length=1)


class CourseRead(CourseBase):
    id: UUID
    created_at: datetime
    topics: list[TopicRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ============================================================================
# Planner Schemas
# ============================================================================

class DayPlan(BaseModel):
    date: datetime
    topics: list[UUID] = Field(default_factory=list)
    minutes: int = Field(..., ge=0)
    activity: ActivityType
    reason: str = Field(default="")


class StudyPlan(BaseModel):
    days: list[DayPlan]
    total_days: int
    total_minutes: int
    warnings: list[str] = Field(default_factory=list)


class PlannerInput(BaseModel):
    topics: list[TopicRead]
    exam_date: datetime
    hours_per_day: float
    current_mastery: dict[UUID, float] = Field(default_factory=dict)


# ============================================================================
# Researcher Schemas
# ============================================================================

class SourceRef(BaseModel):
    type: Literal["uploaded", "model_knowledge"]
    doc_id: UUID | None = None
    chunk_id: UUID | None = None
    excerpt: str = Field(default="", max_length=500)


class TopicNotes(BaseModel):
    topic: str
    summary: str = Field(..., max_length=2000)
    key_points: list[str] = Field(default_factory=list)
    definitions: list[str] = Field(default_factory=list)
    formulas_or_examples: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)


class ResearcherInput(BaseModel):
    topic: TopicRead
    retrieved_chunks: list[dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# Tutor Schemas
# ============================================================================

class Explanation(BaseModel):
    explanation_markdown: str
    example: str = Field(default="")
    common_mistakes: list[str] = Field(default_factory=list)
    check_question: str = Field(default="")


class TutorInput(BaseModel):
    topic: TopicRead
    notes: TopicNotes
    level: UserLevel
    follow_up_question: str | None = None
    conversation_history: list[dict[str, str]] = Field(default_factory=list)


class FollowUpRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class FollowUpResponse(BaseModel):
    answer: str


# ============================================================================
# Quizzer Schemas
# ============================================================================

class QuizQuestion(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    question: str
    options: Annotated[list[str], Field(min_length=4, max_length=4)]
    correct_index: int = Field(..., ge=0, le=3)
    explanation: str
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM


class Quiz(BaseModel):
    topic_id: UUID
    questions: Annotated[list[QuizQuestion], Field(min_length=1, max_length=10)]


class QuizGenerateRequest(BaseModel):
    topic_id: UUID
    num_questions: int = Field(default=5, ge=1, le=10)
    difficulty: DifficultyLevel | None = None


class QuizSubmitRequest(BaseModel):
    attempt_id: UUID
    answers: dict[UUID, int] = Field(...)  # question_id -> chosen_index


class QuizSubmitResponse(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    correct_count: int
    total_questions: int
    explanations: dict[UUID, str]  # question_id -> explanation
    new_mastery: float


# ============================================================================
# Tracker Schemas
# ============================================================================

class MasteryUpdate(BaseModel):
    topic_id: UUID
    old_mastery: float
    new_mastery: float
    quiz_score: float
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProgressSnapshot(BaseModel):
    course_id: UUID
    days_remaining: int
    topic_masteries: dict[UUID, float]
    quiz_history: list[dict[str, Any]]
    overall_progress: float = Field(..., ge=0.0, le=1.0)


# ============================================================================
# RAG / Upload Schemas
# ============================================================================

class UploadedDocRead(BaseModel):
    id: UUID
    course_id: UUID
    filename: str
    chunk_count: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class ChunkData(BaseModel):
    id: UUID
    content: str
    metadata: dict[str, Any]


# ============================================================================
# Coordinator / Run Schemas
# ============================================================================

class AgentEvent(BaseModel):
    run_id: UUID
    agent: str
    status: AgentStatus
    message: str
    topic_id: UUID | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = Field(default_factory=dict)


class RunCreate(BaseModel):
    course_id: UUID


class RunRead(BaseModel):
    id: UUID
    course_id: UUID
    status: Literal["running", "completed", "failed"]
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


# ============================================================================
# API Response Wrappers
# ============================================================================

class APIResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: str | None = None


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int