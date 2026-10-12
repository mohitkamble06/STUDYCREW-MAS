"""Pytest configuration and shared fixtures."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.schemas import TopicRead, TopicNotes, Explanation, Quiz, QuizQuestion, DifficultyLevel, UserLevel


@pytest.fixture
def sample_topic():
    return TopicRead(
        id=uuid4(),
        course_id=uuid4(),
        name="Test Topic",
        importance=2,
        mastery=0.3,
    )


@pytest.fixture
def sample_notes():
    return TopicNotes(
        topic="Test Topic",
        summary="This is a test summary.",
        key_points=["Point 1", "Point 2"],
        definitions=["Def 1"],
        formulas_or_examples=["Example 1"],
        sources=[],
    )


@pytest.fixture
def sample_explanation():
    return Explanation(
        explanation_markdown="## Explanation\n\nThis explains the topic.",
        example="An example.",
        common_mistakes=["Mistake 1"],
        check_question="Check question?",
    )


@pytest.fixture
def sample_quiz():
    q1 = QuizQuestion(
        id=uuid4(),
        question="What is X?",
        options=["A", "B", "C", "D"],
        correct_index=0,
        explanation="X is A.",
        difficulty=DifficultyLevel.EASY,
    )
    q2 = QuizQuestion(
        id=uuid4(),
        question="What is Y?",
        options=["A", "B", "C", "D"],
        correct_index=1,
        explanation="Y is B.",
        difficulty=DifficultyLevel.MEDIUM,
    )
    return Quiz(topic_id=uuid4(), questions=[q1, q2])


# Mock LLM responses for testing agents
@pytest.fixture
def mock_planner_response():
    return {
        "days": [
            {
                "date": "2024-01-15T00:00:00",
                "topics": [],
                "minutes": 120,
                "activity": "learn",
                "reason": "First topic",
            }
        ],
        "total_days": 1,
        "total_minutes": 120,
        "warnings": [],
    }


@pytest.fixture
def mock_researcher_response():
    return {
        "topic": "Test Topic",
        "summary": "Test summary from researcher.",
        "key_points": ["Key 1"],
        "definitions": ["Def 1"],
        "formulas_or_examples": ["Ex 1"],
        "sources": [
            {"type": "model_knowledge", "excerpt": "Model knows this"}
        ],
    }


@pytest.fixture
def mock_tutor_response():
    return {
        "explanation_markdown": "## Explanation\n\nThis is the explanation.",
        "example": "An example.",
        "common_mistakes": ["Mistake 1"],
        "check_question": "What did you learn?",
    }


@pytest.fixture
def mock_quizzer_response():
    return {
        "topic_id": str(uuid4()),
        "questions": [
            {
                "id": str(uuid4()),
                "question": "Q1?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "explanation": "Expl 1",
                "difficulty": "easy",
            }
        ],
    }


# Async mock for LLM calls
@pytest.fixture
def mock_generate_json(monkeypatch):
    """Mock the generate_json function for testing agents."""
    async def mock_func(prompt, schema, **kwargs):
        # Return appropriate mock based on schema
        if schema.__name__ == "StudyPlan":
            return mock_planner_response()
        elif schema.__name__ == "TopicNotes":
            return mock_researcher_response()
        elif schema.__name__ == "Explanation":
            return mock_tutor_response()
        elif schema.__name__ == "Quiz":
            return mock_quizzer_response()
        elif schema.__name__ == "FollowUpAnswer":
            class FollowUpAnswer:
                def __init__(self, answer):
                    self.answer = answer
            return FollowUpAnswer("This is a follow-up answer.")
        else:
            return schema()
    
    monkeypatch.setattr("app.llm.generate_json", mock_func)


# Event loop for async tests
@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()