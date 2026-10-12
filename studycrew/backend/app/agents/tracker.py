"""Tracker agent: manages topic mastery scores (deterministic, no LLM)."""

import logging
from datetime import datetime
from uuid import UUID

from app.schemas import MasteryUpdate, TopicRead
from app.db import async_session_maker, Topic
from sqlalchemy import select

logger = logging.getLogger(__name__)


# Mastery update formula: new_mastery = 0.7 * old_mastery + 0.3 * quiz_score
MASTERY_DECAY = 0.7
MASTERY_WEIGHT = 0.3


def calculate_new_mastery(old_mastery: float, quiz_score: float) -> float:
    """
    Calculate updated mastery using exponential moving average.

    Args:
        old_mastery: Current mastery (0.0 to 1.0)
        quiz_score: Quiz score (0.0 to 1.0)

    Returns:
        New mastery (0.0 to 1.0)
    """
    new_mastery = MASTERY_DECAY * old_mastery + MASTERY_WEIGHT * quiz_score
    return max(0.0, min(1.0, new_mastery))


async def update_mastery(topic_id: UUID, quiz_score: float) -> MasteryUpdate:
    """
    Update topic mastery in database.

    Args:
        topic_id: Topic UUID
        quiz_score: Score from 0.0 to 1.0

    Returns:
        MasteryUpdate with old and new values
    """
    async with async_session_maker() as session:
        topic = await session.get(Topic, topic_id)
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")

        old_mastery = topic.mastery
        new_mastery = calculate_new_mastery(old_mastery, quiz_score)
        topic.mastery = new_mastery

        await session.commit()
        await session.refresh(topic)

        logger.info(f"Updated mastery for topic {topic_id}: {old_mastery:.3f} -> {new_mastery:.3f}")

        return MasteryUpdate(
            topic_id=topic_id,
            old_mastery=old_mastery,
            new_mastery=new_mastery,
            quiz_score=quiz_score,
            updated_at=datetime.utcnow(),
        )


async def get_mastery(topic_id: UUID) -> float:
    """Get current mastery for a topic."""
    async with async_session_maker() as session:
        topic = await session.get(Topic, topic_id)
        return topic.mastery if topic else 0.0


async def get_all_masteries(course_id: UUID) -> dict[UUID, float]:
    """Get mastery for all topics in a course."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Topic.id, Topic.mastery).where(Topic.course_id == course_id)
        )
        return {row.id: row.mastery for row in result.all()}


async def reset_mastery(course_id: UUID) -> None:
    """Reset all topic masteries to 0.0 for a course."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Topic).where(Topic.course_id == course_id)
        )
        for topic in result.scalars().all():
            topic.mastery = 0.0
        await session.commit()