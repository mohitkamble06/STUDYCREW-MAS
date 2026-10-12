"""Course API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_maker, Course, Topic
from app.schemas import CourseCreate, CourseRead, TopicCreate, TopicRead

router = APIRouter()


async def get_db():
    async with async_session_maker() as session:
        yield session


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(course_data: CourseCreate, db: AsyncSession = Depends(get_db)):
    """Create a new course with topics."""
    course = Course(
        subject=course_data.subject,
        exam_date=course_data.exam_date,
        hours_per_day=course_data.hours_per_day,
        level=course_data.level.value,
    )
    db.add(course)
    await db.flush()

    topics = []
    for topic_data in course_data.topics:
        topic = Topic(
            course_id=course.id,
            name=topic_data.name,
            importance=topic_data.importance,
            mastery=topic_data.mastery,
        )
        db.add(topic)
        topics.append(topic)

    await db.commit()
    await db.refresh(course)
    for t in topics:
        await db.refresh(t)

    return CourseRead(
        id=course.id,
        subject=course.subject,
        exam_date=course.exam_date,
        hours_per_day=course.hours_per_day,
        level=course.level,
        created_at=course.created_at,
        topics=[TopicRead.model_validate(t) for t in topics],
    )


@router.get("", response_model=list[CourseRead])
async def list_courses(db: AsyncSession = Depends(get_db)):
    """List all courses."""
    result = await db.execute(select(Course).order_by(Course.created_at.desc()))
    courses = result.scalars().all()

    response = []
    for course in courses:
        topic_result = await db.execute(select(Topic).where(Topic.course_id == course.id))
        topics = topic_result.scalars().all()
        response.append(CourseRead(
            id=course.id,
            subject=course.subject,
            exam_date=course.exam_date,
            hours_per_day=course.hours_per_day,
            level=course.level,
            created_at=course.created_at,
            topics=[TopicRead.model_validate(t) for t in topics],
        ))

    return response


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(course_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a course with its topics."""
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    topic_result = await db.execute(select(Topic).where(Topic.course_id == course_id))
    topics = topic_result.scalars().all()

    return CourseRead(
        id=course.id,
        subject=course.subject,
        exam_date=course.exam_date,
        hours_per_day=course.hours_per_day,
        level=course.level,
        created_at=course.created_at,
        topics=[TopicRead.model_validate(t) for t in topics],
    )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(course_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a course and all related data."""
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    await db.delete(course)
    await db.commit()