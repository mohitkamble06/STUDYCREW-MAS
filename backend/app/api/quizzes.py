"""Quiz API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_maker, Topic, QuizAttempt, TopicContent
from app.agents import QuizzerAgent, grade_quiz, update_mastery
from app.schemas import (
    QuizGenerateRequest, Quiz, QuizSubmitRequest, QuizSubmitResponse,
    QuizQuestion, TopicRead, TopicNotes
)

router = APIRouter()


async def get_db():
    async with async_session_maker() as session:
        yield session


@router.post("/generate", response_model=Quiz)
async def generate_quiz(request: QuizGenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate a quiz for a topic."""
    topic = await db.get(Topic, request.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    content = await db.get(TopicContent, request.topic_id)
    if not content or not content.notes_json:
        raise HTTPException(status_code=404, detail="Topic notes not found. Run the crew first.")

    notes = TopicNotes.model_validate(content.notes_json)

    # Create quizzer agent (need run_id for events)
    from uuid import uuid4
    from app.api.runs import get_queue

    run_id = uuid4()
    queue = get_queue(run_id)

    async def emit_event(event):
        await queue.put(event)

    quizzer = QuizzerAgent(run_id=run_id, emit_event_callback=emit_event)
    quiz = await quizzer.run({
        "topic_id": topic.id,
        "topic": TopicRead.model_validate(topic),
        "notes": notes,
        "num_questions": request.num_questions,
        "difficulty": request.difficulty,
    }, topic_id=topic.id)

    # Save quiz attempt
    attempt = QuizAttempt(
        topic_id=topic.id,
        quiz_json=quiz.model_dump(),
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    # Return quiz with attempt_id
    return Quiz(
        topic_id=quiz.topic_id,
        questions=quiz.questions,
    )


@router.post("/{attempt_id}/submit", response_model=QuizSubmitResponse)
async def submit_quiz(attempt_id: UUID, request: QuizSubmitRequest, db: AsyncSession = Depends(get_db)):
    """Submit quiz answers and get graded results."""
    if attempt_id != request.attempt_id:
        raise HTTPException(status_code=400, detail="Attempt ID mismatch")

    attempt = await db.get(QuizAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")

    if attempt.answers_json is not None:
        raise HTTPException(status_code=400, detail="Quiz already submitted")

    quiz = Quiz.model_validate(attempt.quiz_json)
    topic = await db.get(Topic, attempt.topic_id)

    # Grade quiz
    score, correct_count, explanations = grade_quiz(quiz, request.answers)

    # Update mastery
    mastery_update = await update_mastery(attempt.topic_id, score)

    # Save answers and score
    attempt.answers_json = {str(k): v for k, v in request.answers.items()}
    attempt.score = score
    await db.commit()

    return QuizSubmitResponse(
        score=score,
        correct_count=correct_count,
        total_questions=len(quiz.questions),
        explanations=explanations,
        new_mastery=mastery_update.new_mastery,
    )


@router.get("/{attempt_id}")
async def get_quiz_attempt(attempt_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get quiz attempt details."""
    attempt = await db.get(QuizAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")

    return {
        "id": str(attempt.id),
        "topic_id": str(attempt.topic_id),
        "quiz": attempt.quiz_json,
        "answers": attempt.answers_json,
        "score": attempt.score,
        "created_at": attempt.created_at.isoformat(),
    }