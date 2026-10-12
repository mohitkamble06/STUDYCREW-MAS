"""Coordinator agent: orchestrates the multi-agent crew."""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from app.agents.base import BaseAgent
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.tutor import TutorAgent
from app.agents.quizzer import QuizzerAgent, grade_quiz
from app.agents.tracker import update_mastery, get_all_masteries
from app.prompts.coordinator import COORDINATOR_SYSTEM_PROMPT
from app.schemas import (
    AgentEvent, AgentStatus, CourseRead, TopicRead, StudyPlan, TopicNotes,
    Explanation, Quiz, QuizSubmitResponse, RunRead, PlannerInput,
    ResearcherInput, TutorInput
)
from app.db import async_session_maker, StudyPlan as StudyPlanModel, Run as RunModel, TopicContent
from app.rag import rag_service

logger = logging.getLogger(__name__)


class Coordinator:
    """Orchestrates the study crew agents."""

    def __init__(self, run_id: UUID, emit_event):
        self.run_id = run_id
        self.emit_event = emit_event
        self.course: CourseRead | None = None
        self.topics: list[TopicRead] = []
        self.plan: StudyPlan | None = None

    async def _emit(self, agent: str, status: AgentStatus, message: str, topic_id: UUID | None = None, data: dict | None = None) -> None:
        event = AgentEvent(
            run_id=self.run_id,
            agent=agent,
            status=status,
            message=message,
            topic_id=topic_id,
            data=data or {},
        )
        await self.emit_event(event)

    # -------------------------------------------------------------------------
    # Main Workflows
    # -------------------------------------------------------------------------

    async def run_initial_plan(self, course: CourseRead, topics: list[TopicRead]) -> StudyPlan:
        """Run the full initial planning workflow."""
        self.course = course
        self.topics = topics

        # 1. Get current masteries
        masteries = await get_all_masteries(course.id)

        # 2. Run Planner
        planner = PlannerAgent(run_id=self.run_id, emit_event_callback=self.emit_event)
        planner_input = PlannerInput(
            topics=topics,
            exam_date=course.exam_date,
            hours_per_day=course.hours_per_day,
            current_mastery=masteries,
        )
        self.plan = await planner.run(planner_input)

        # Save plan to database
        await self._save_plan(self.plan)

        # 3. For each topic in plan, run Researcher + Tutor (parallel per topic)
        topic_ids_in_plan = set()
        for day in self.plan.days:
            topic_ids_in_plan.update(day.topics)

        # Run Researcher + Tutor for each unique topic
        tasks = []
        for topic_id in topic_ids_in_plan:
            topic = next(t for t in topics if t.id == topic_id)
            tasks.append(self._process_topic(topic))

        await asyncio.gather(*tasks)

        return self.plan

    async def _process_topic(self, topic: TopicRead) -> tuple[TopicNotes, Explanation]:
        """Run Researcher then Tutor for a single topic."""
        # Researcher
        researcher = ResearcherAgent(run_id=self.run_id, emit_event_callback=self.emit_event)
        
        # Retrieve relevant chunks
        chunks = await rag_service.retrieve(
            query=topic.name,
            course_id=self.course.id,
            top_k=5,
            topic_filter=topic.name,
        )

        researcher_input = ResearcherInput(topic=topic, retrieved_chunks=chunks)
        notes = await researcher.run(researcher_input, topic_id=topic.id)

        # Tutor
        tutor = TutorAgent(run_id=self.run_id, emit_event_callback=self.emit_event)
        tutor_input = TutorInput(
            topic=topic,
            notes=notes,
            level=self.course.level,
            follow_up_question=None,
            conversation_history=[],
        )
        explanation = await tutor.run(tutor_input, topic_id=topic.id)

        # Save to database
        await self._save_topic_content(topic.id, notes, explanation)

        return notes, explanation

    async def run_quiz_generation(self, topic: TopicRead, notes: TopicNotes, num_questions: int = 5) -> Quiz:
        """Generate a quiz for a topic."""
        quizzer = QuizzerAgent(run_id=self.run_id, emit_event_callback=self.emit_event)
        
        quiz = await quizzer.run({
            "topic_id": topic.id,
            "topic": topic,
            "notes": notes,
            "num_questions": num_questions,
        }, topic_id=topic.id)

        return quiz

    async def run_quiz_submission(self, topic: TopicRead, quiz: Quiz, answers: dict[UUID, int]) -> QuizSubmitResponse:
        """Grade quiz and update mastery."""
        # Grade in Python
        score, correct_count, explanations = grade_quiz(quiz, answers)

        # Update mastery
        mastery_update = await update_mastery(topic.id, score)

        return QuizSubmitResponse(
            score=score,
            correct_count=correct_count,
            total_questions=len(quiz.questions),
            explanations=explanations,
            new_mastery=mastery_update.new_mastery,
        )

    async def run_replan(self) -> StudyPlan:
        """Regenerate plan for remaining days with updated mastery."""
        # Get updated masteries
        masteries = await get_all_masteries(self.course.id)

        # Calculate remaining days
        today = datetime.now().date()
        exam_date = self.course.exam_date.date()
        days_remaining = (exam_date - today).days + 1

        if days_remaining <= 0:
            raise ValueError("Exam date has passed")

        # Filter plan to remaining days
        remaining_topics = set()
        for day in self.plan.days:
            if day.date.date() >= today:
                remaining_topics.update(day.topics)

        remaining_topic_objs = [t for t in self.topics if t.id in remaining_topics]

        # Run planner again
        planner = PlannerAgent(run_id=self.run_id, emit_event_callback=self.emit_event)
        planner_input = PlannerInput(
            topics=remaining_topic_objs,
            exam_date=self.course.exam_date,
            hours_per_day=self.course.hours_per_day,
            current_mastery=masteries,
        )
        new_plan = await planner.run(planner_input)

        # Save new plan version
        await self._save_plan(new_plan, version=2)
        self.plan = new_plan

        # Process any new topics not yet researched
        existing_content = await self._get_topics_with_content()
        new_topics = [t for t in remaining_topic_objs if t.id not in existing_content]

        if new_topics:
            tasks = [self._process_topic(t) for t in new_topics]
            await asyncio.gather(*tasks)

        return new_plan

    # -------------------------------------------------------------------------
    # Database Helpers
    # -------------------------------------------------------------------------

    async def _save_plan(self, plan: StudyPlan, version: int = 1) -> None:
        async with async_session_maker() as session:
            plan_model = StudyPlanModel(
                course_id=self.course.id,
                plan_json=plan.model_dump(),
                version=version,
            )
            session.add(plan_model)
            await session.commit()

    async def _save_topic_content(self, topic_id: UUID, notes: TopicNotes, explanation: Explanation) -> None:
        async with async_session_maker() as session:
            content = TopicContent(
                topic_id=topic_id,
                notes_json=notes.model_dump(),
                explanation_json=explanation.model_dump(),
            )
            session.add(content)
            await session.commit()

    async def _get_topics_with_content(self) -> set[UUID]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(TopicContent.topic_id)
            )
            return {row[0] for row in result.all()}


async def create_run(course_id: UUID) -> RunRead:
    """Create a new run record."""
    async with async_session_maker() as session:
        run = RunModel(course_id=course_id, status="running")
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return RunRead(
            id=run.id,
            course_id=run.course_id,
            status=run.status,
            created_at=run.created_at,
            completed_at=run.completed_at,
            error=run.error,
        )


async def complete_run(run_id: UUID, status: str = "completed", error: str | None = None) -> None:
    """Mark run as completed or failed."""
    async with async_session_maker() as session:
        run = await session.get(RunModel, run_id)
        if run:
            run.status = status
            run.completed_at = datetime.utcnow()
            run.error = error
            await session.commit()