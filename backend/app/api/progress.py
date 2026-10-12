"""Progress and dashboard API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_maker, Course, Topic, QuizAttempt, StudyPlan as StudyPlanModel
from app.schemas import ProgressSnapshot, StudyPlan
from app.agents import get_all_masteries

router = APIRouter()


async def get_db():
    async with async_session_maker() as session:
        yield session


@router.get("/{course_id}/plan", response_model=StudyPlan)
async def get_latest_plan(course_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get the latest study plan for a course."""
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    result = await db.execute(
        select(StudyPlanModel)
        .where(StudyPlanModel.course_id == course_id)
        .order_by(StudyPlanModel.version.desc())
        .limit(1)
    )
    plan_model = result.scalar_one_or_none()

    if not plan_model:
        raise HTTPException(status_code=404, detail="No plan found. Run the crew first.")

    return StudyPlan.model_validate(plan_model.plan_json)


@router.post("/{course_id}/replan", response_model=StudyPlan)
async def replan_course(course_id: UUID, db: AsyncSession = Depends(get_db)):
    """Regenerate plan for remaining days with updated mastery."""
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # This would trigger the coordinator's replan workflow
    # For now, return the latest plan (full replan needs run context)
    result = await db.execute(
        select(StudyPlanModel)
        .where(StudyPlanModel.course_id == course_id)
        .order_by(StudyPlanModel.version.desc())
        .limit(1)
    )
    plan_model = result.scalar_one_or_none()

    if not plan_model:
        raise HTTPException(status_code=404, detail="No plan found. Run the crew first.")

    return StudyPlan.model_validate(plan_model.plan_json)


@router.get("/{course_id}/progress", response_model=ProgressSnapshot)
async def get_progress(course_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get progress dashboard data for a course."""
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get topics with mastery
    result = await db.execute(select(Topic).where(Topic.course_id == course_id))
    topics = result.scalars().all()

    topic_masteries = {t.id: t.mastery for t in topics}

    # Get quiz history
    quiz_result = await db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.topic_id.in_([t.id for t in topics]))
        .order_by(QuizAttempt.created_at.desc())
    )
    quiz_attempts = quiz_result.scalars().all()

    quiz_history = []
    for attempt in quiz_attempts:
        if attempt.score is not None:
            quiz_history.append({
                "topic_id": str(attempt.topic_id),
                "score": attempt.score,
                "correct_count": sum(1 for k, v in (attempt.answers_json or {}).items()
                                   if v == attempt.quiz_json["questions"][int(k)]["correct_index"]) if attempt.answers_json else 0,
                "total_questions": len(attempt.quiz_json.get("questions", [])),
                "created_at": attempt.created_at.isoformat(),
            })

    # Calculate days remaining
    today = datetime.now().date()
    exam_date = course.exam_date.date()
    days_remaining = max(0, (exam_date - today).days + 1)

    # Overall progress (average mastery)
    overall_progress = sum(topic_masteries.values()) / len(topic_masteries) if topic_masteries else 0.0

    return ProgressSnapshot(
        course_id=course_id,
        days_remaining=days_remaining,
        topic_masteries=topic_masteries,
        quiz_history=quiz_history,
        overall_progress=overall_progress,
    )