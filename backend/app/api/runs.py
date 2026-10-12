"""Run/crew execution API routes with SSE streaming."""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_maker, Run as RunModel, Course, Topic
from app.agents import Coordinator, create_run, complete_run
from app.schemas import RunRead, RunCreate, AgentEvent, AgentStatus, CourseRead, TopicRead

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory event queues for SSE (in production, use Redis)
run_queues: dict[UUID, asyncio.Queue] = {}


async def get_db():
    async with async_session_maker() as session:
        yield session


def get_queue(run_id: UUID) -> asyncio.Queue:
    """Get or create event queue for a run."""
    if run_id not in run_queues:
        run_queues[run_id] = asyncio.Queue()
    return run_queues[run_id]


async def event_generator(run_id: UUID):
    """SSE event generator for a run."""
    queue = get_queue(run_id)
    try:
        while True:
            event = await queue.get()
            if event is None:  # End signal
                break
            yield {
                "event": "agent_event",
                "data": event.model_dump_json(),
            }
    except asyncio.CancelledError:
        pass
    finally:
        # Clean up queue when client disconnects
        if run_id in run_queues:
            del run_queues[run_id]


@router.post("", response_model=RunRead, status_code=201)
async def start_run(run_data: RunCreate, db: AsyncSession = Depends(get_db)):
    """Start a new crew run for a course."""
    # Verify course exists
    course = await db.get(Course, run_data.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get topics
    result = await db.execute(select(Topic).where(Topic.course_id == run_data.course_id))
    topics = result.scalars().all()
    if not topics:
        raise HTTPException(status_code=400, detail="Course has no topics")

    # Create run record
    run = await create_run(run_data.course_id)

    return run


@router.get("/{run_id}/events")
async def stream_events(run_id: UUID):
    """SSE stream for run events."""
    # Verify run exists
    async with async_session_maker() as db:
        run = await db.get(RunModel, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

    return EventSourceResponse(event_generator(run_id))


@router.get("/{run_id}", response_model=RunRead)
async def get_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get run status."""
    run = await db.get(RunModel, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunRead.model_validate(run)


async def execute_crew(run_id: UUID, course_id: UUID):
    """Background task to execute the crew."""
    queue = get_queue(run_id)

    async def emit_event(event: AgentEvent):
        await queue.put(event)

    try:
        # Get course and topics
        async with async_session_maker() as db:
            course = await db.get(Course, course_id)
            result = await db.execute(select(Topic).where(Topic.course_id == course_id))
            topics = result.scalars().all()

        if not course or not topics:
            await emit_event(AgentEvent(
                run_id=run_id,
                agent="coordinator",
                status=AgentStatus.ERROR,
                message="Course or topics not found",
            ))
            await complete_run(run_id, "failed", "Course or topics not found")
            return

        # Run coordinator
        coordinator = Coordinator(run_id=run_id, emit_event=emit_event)
        
        course_read = CourseRead(
            id=course.id,
            subject=course.subject,
            exam_date=course.exam_date,
            hours_per_day=course.hours_per_day,
            level=course.level,
            created_at=course.created_at,
            topics=[],
        )
        topic_reads = [
            TopicRead(
                id=t.id,
                course_id=t.course_id,
                name=t.name,
                importance=t.importance,
                mastery=t.mastery,
            )
            for t in topics
        ]
        
        plan = await coordinator.run_initial_plan(
            course=course_read,
            topics=topic_reads,
        )

        await complete_run(run_id, "completed")
        await emit_event(AgentEvent(
            run_id=run_id,
            agent="coordinator",
            status=AgentStatus.DONE,
            message="Crew execution completed",
            data={"plan_id": str(plan.days[0].topics[0]) if plan.days else None},
        ))

    except Exception as e:
        logger.exception(f"Crew execution failed for run {run_id}")
        await emit_event(AgentEvent(
            run_id=run_id,
            agent="coordinator",
            status=AgentStatus.ERROR,
            message=f"Execution failed: {str(e)}",
        ))
        await complete_run(run_id, "failed", str(e))

    finally:
        # Signal end of stream
        await queue.put(None)


@router.post("/{run_id}/execute")
async def execute_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """Execute the crew for a run (background task)."""
    run = await db.get(RunModel, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status != "running":
        raise HTTPException(status_code=400, detail=f"Run already {run.status}")

    # Start background execution
    asyncio.create_task(execute_crew(run_id, run.course_id))

    return {"status": "started", "run_id": str(run_id)}