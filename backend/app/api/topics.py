"""Topic content API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_maker, Topic, TopicContent
from app.schemas import TopicRead, TopicNotes, Explanation, FollowUpRequest, FollowUpResponse, UserLevel
from app.agents import handle_follow_up
from app.api.runs import get_queue

router = APIRouter()


async def get_db():
    async with async_session_maker() as session:
        yield session


@router.get("/{topic_id}", response_model=TopicRead)
async def get_topic(topic_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get topic details."""
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return TopicRead.model_validate(topic)


@router.get("/{topic_id}/content")
async def get_topic_content(topic_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get notes and explanation for a topic."""
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    content = await db.get(TopicContent, topic_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found. Run the crew first.")

    return {
        "notes": content.notes_json,
        "explanation": content.explanation_json,
    }


@router.post("/{topic_id}/ask", response_model=FollowUpResponse)
async def ask_follow_up(
    topic_id: UUID,
    request: FollowUpRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ask a follow-up question to the Tutor."""
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Load course to get level
    from app.db import Course
    course = await db.get(Course, topic.course_id)
    level = course.level if course else "beginner"

    content = await db.get(TopicContent, topic_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found. Run the crew first.")

    # Parse stored content
    notes = TopicNotes.model_validate(content.notes_json)
    explanation = Explanation.model_validate(content.explanation_json)

    # Get conversation history from request (or empty)
    history = []  # Could be stored in session/db in future

    # Use a dummy run_id for follow-up (or get from session)
    from uuid import uuid4
    run_id = uuid4()
    queue = get_queue(run_id)

    async def emit_event(event):
        await queue.put(event)

    answer = await handle_follow_up(
        topic=TopicRead.model_validate(topic),
        notes=notes,
        level=level,
        question=request.question,
        history=history,
        run_id=run_id,
        emit_event=emit_event,
    )

    return FollowUpResponse(answer=answer)