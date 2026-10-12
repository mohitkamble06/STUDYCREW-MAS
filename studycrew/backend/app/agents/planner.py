"""Planner agent: creates day-by-day study plans."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from app.agents.base import BaseAgent
from app.prompts.planner import PLANNER_SYSTEM_PROMPT
from app.schemas import PlannerInput, StudyPlan, DayPlan, TopicRead, ActivityType

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent[PlannerInput, StudyPlan]):
    name = "planner"
    system_prompt = PLANNER_SYSTEM_PROMPT
    output_schema = StudyPlan

    async def _execute(self, input_data: PlannerInput) -> StudyPlan:
        # Build prompt with all necessary data
        topics_info = []
        for topic in input_data.topics:
            mastery = input_data.current_mastery.get(topic.id, topic.mastery)
            priority = (1 - mastery) * topic.importance
            topics_info.append({
                "id": str(topic.id),
                "name": topic.name,
                "importance": topic.importance,
                "mastery": mastery,
                "priority": round(priority, 3),
            })

        # Sort by priority descending
        topics_info.sort(key=lambda x: x["priority"], reverse=True)

        prompt = f"""Create a study plan for the following topics.

EXAM DATE: {input_data.exam_date.strftime('%Y-%m-%d')}
HOURS PER DAY: {input_data.hours_per_day}
TOTAL MINUTES PER DAY: {int(input_data.hours_per_day * 60)}

TOPICS (sorted by priority = (1-mastery)*importance):
{self._format_topics(topics_info)}

Generate a day-by-day plan from today ({datetime.now().strftime('%Y-%m-%d')}) to the exam date.
Each day: date, topics[], minutes, activity (learn/revise/practice/mock_test), reason.
Last 1-2 days: only revise/mock_test.
Never exceed minutes per day.
If not all topics fit, add warnings and prioritize by priority score.

Output ONLY valid JSON matching StudyPlan schema."""

        # Call LLM
        result = await self._call_llm(prompt, StudyPlan)

        # Validate constraints
        validated = self._validate_plan(result, input_data)
        return validated

    def _format_topics(self, topics_info: list[dict]) -> str:
        lines = []
        for t in topics_info:
            lines.append(f"  - {t['name']} (id: {t['id']}, importance: {t['importance']}, mastery: {t['mastery']:.2f}, priority: {t['priority']})")
        return "\n".join(lines)

    def _validate_plan(self, plan: StudyPlan, input_data: PlannerInput) -> StudyPlan:
        """Validate plan constraints and fix if needed."""
        max_minutes_per_day = int(input_data.hours_per_day * 60)
        today = datetime.now().date()
        exam_date = input_data.exam_date.date()

        # Check each day
        for day in plan.days:
            day_date = day.date.date() if isinstance(day.date, datetime) else day.date

            # Check date range
            if day_date < today:
                day.date = datetime.combine(today, datetime.min.time())
            if day_date > exam_date:
                day.date = datetime.combine(exam_date, datetime.min.time())

            # Check minutes
            if day.minutes > max_minutes_per_day:
                logger.warning(f"Day {day_date} exceeds max minutes: {day.minutes} > {max_minutes_per_day}")
                day.minutes = max_minutes_per_day
                plan.warnings.append(f"Day {day_date}: reduced minutes to {max_minutes_per_day}")

            # Check activity for last days
            days_to_exam = (exam_date - day_date).days
            if days_to_exam <= 1 and day.activity == ActivityType.LEARN:
                day.activity = ActivityType.REVISE
                plan.warnings.append(f"Day {day_date}: changed activity to revise (exam in {days_to_exam} days)")

        # Recalculate totals
        plan.total_days = len(plan.days)
        plan.total_minutes = sum(d.minutes for d in plan.days)

        return plan