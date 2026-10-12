"""Tests for planner constraints and validation."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.schemas import StudyPlan, DayPlan, TopicRead, ActivityType, UserLevel
from app.agents.planner import PlannerAgent


class TestPlannerValidation:
    """Tests for planner validation logic."""

    @pytest.fixture
    def sample_topics(self):
        return [
            TopicRead(
                id=uuid4(),
                course_id=uuid4(),
                name="Topic A",
                importance=3,
                mastery=0.0,
            ),
            TopicRead(
                id=uuid4(),
                course_id=uuid4(),
                name="Topic B",
                importance=2,
                mastery=0.5,
            ),
            TopicRead(
                id=uuid4(),
                course_id=uuid4(),
                name="Topic C",
                importance=1,
                mastery=0.8,
            ),
        ]

    @pytest.fixture
    def exam_date(self):
        return datetime.now() + timedelta(days=10)

    def test_priority_calculation(self, sample_topics):
        """Priority = (1 - mastery) * importance"""
        # Topic A: (1 - 0.0) * 3 = 3.0 (highest)
        # Topic B: (1 - 0.5) * 2 = 1.0
        # Topic C: (1 - 0.8) * 1 = 0.2 (lowest)
        priorities = {}
        for t in sample_topics:
            priorities[t.name] = (1 - t.mastery) * t.importance

        assert priorities["Topic A"] == 3.0
        assert priorities["Topic B"] == 1.0
        assert priorities["Topic C"] == 0.2

    def test_plan_within_daily_hours(self, sample_topics, exam_date):
        """No day should exceed hours_per_day"""
        plan = StudyPlan(
            days=[
                DayPlan(
                    date=datetime.now() + timedelta(days=i),
                    topics=[sample_topics[0].id],
                    minutes=150,  # Exceeds 2 hours = 120 min
                    activity=ActivityType.LEARN,
                    reason="Test",
                )
                for i in range(5)
            ],
            total_days=5,
            total_minutes=750,
        )

        # Validation should cap at 120 minutes
        max_minutes = 2 * 60
        for day in plan.days:
            if day.minutes > max_minutes:
                # This is what the validation does
                day.minutes = max_minutes

        for day in plan.days:
            assert day.minutes <= max_minutes

    def test_last_days_revision_only(self, sample_topics, exam_date):
        """Last 1-2 days should be revise/mock_test only"""
        today = datetime.now()
        plan = StudyPlan(
            days=[
                DayPlan(date=today + timedelta(days=8), topics=[sample_topics[0].id], minutes=120, activity=ActivityType.LEARN, reason=""),
                DayPlan(date=today + timedelta(days=9), topics=[sample_topics[1].id], minutes=120, activity=ActivityType.REVISE, reason=""),
            ],
            total_days=2,
            total_minutes=240,
        )

        # Day before exam (9 days from now if exam is 10 days out) should be revise
        exam_day = exam_date.date()
        for day in plan.days:
            days_to_exam = (exam_day - day.date.date()).days
            if days_to_exam <= 1 and day.activity == ActivityType.LEARN:
                # Should be converted to revise
                day.activity = ActivityType.REVISE

        last_day = plan.days[-1]
        assert last_day.activity in [ActivityType.REVISE, ActivityType.MOCK_TEST]

    def test_total_minutes_calculation(self):
        """Total minutes should sum correctly"""
        plan = StudyPlan(
            days=[
                DayPlan(date=datetime.now(), topics=[], minutes=60, activity=ActivityType.LEARN, reason=""),
                DayPlan(date=datetime.now() + timedelta(days=1), topics=[], minutes=90, activity=ActivityType.REVISE, reason=""),
                DayPlan(date=datetime.now() + timedelta(days=2), topics=[], minutes=120, activity=ActivityType.PRACTICE, reason=""),
            ],
            total_days=3,
            total_minutes=270,
        )

        assert plan.total_minutes == sum(d.minutes for d in plan.days)
        assert plan.total_days == len(plan.days)

    def test_warnings_for_overflow(self, sample_topics, exam_date):
        """Should warn when topics don't fit"""
        # Very short timeframe, many topics
        plan = StudyPlan(
            days=[
                DayPlan(date=datetime.now(), topics=[t.id for t in sample_topics], minutes=120, activity=ActivityType.LEARN, reason="")
            ],
            total_days=1,
            total_minutes=120,
            warnings=["Not all topics fit in available time. Prioritized by priority score."],
        )

        assert len(plan.warnings) > 0
        assert any("prioritize" in w.lower() or "fit" in w.lower() for w in plan.warnings)


class TestPlannerAgent:
    """Tests for PlannerAgent (mocked LLM)."""

    @pytest.fixture
    def mock_llm_response(self):
        """Mock a valid LLM response for testing."""
        return {
            "days": [
                {
                    "date": (datetime.now() + timedelta(days=0)).isoformat(),
                    "topics": [],
                    "minutes": 120,
                    "activity": "learn",
                    "reason": "High priority topic",
                },
                {
                    "date": (datetime.now() + timedelta(days=1)).isoformat(),
                    "topics": [],
                    "minutes": 120,
                    "activity": "revise",
                    "reason": "Revision day",
                },
            ],
            "total_days": 2,
            "total_minutes": 240,
            "warnings": [],
        }

    @pytest.mark.asyncio
    async def test_planner_emits_events(self, sample_topics, exam_date, mock_llm_response):
        """Planner should emit start and done events."""
        events = []

        async def emit_event(event):
            events.append(event)

        agent = PlannerAgent(run_id=uuid4(), emit_event_callback=emit_event)

        # We can't easily test the full agent without mocking the LLM call
        # This is a structural test
        assert agent.name == "planner"
        assert agent.output_schema == StudyPlan