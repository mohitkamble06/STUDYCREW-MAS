"""Seed script to create a demo course for testing."""

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from app.db import async_session_maker, Course, Topic, init_db
from app.config import settings


async def seed_demo_course():
    """Create a demo DBMS course with 8 topics over 10 days."""
    async with async_session_maker() as session:
        # Check if demo already exists
        from sqlalchemy import select
        result = await session.execute(select(Course).where(Course.subject == "Database Management Systems (Demo)"))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Demo course already exists: {existing.id}")
            return existing.id

        # Create course
        exam_date = datetime.now() + timedelta(days=10)
        course = Course(
            subject="Database Management Systems (Demo)",
            exam_date=exam_date,
            hours_per_day=2.0,
            level="beginner",
        )
        session.add(course)
        await session.flush()

        # Demo topics
        topics_data = [
            ("Introduction to Databases & DBMS", 3),
            ("Entity-Relationship Model", 3),
            ("Relational Model & Algebra", 3),
            ("SQL - DDL, DML, DCL", 3),
            ("Normalization (1NF, 2NF, 3NF, BCNF)", 3),
            ("Transaction Management & ACID", 2),
            ("Concurrency Control & Locking", 2),
            ("Indexing & Query Optimization", 2),
        ]

        for name, importance in topics_data:
            topic = Topic(
                course_id=course.id,
                name=name,
                importance=importance,
                mastery=0.0,
            )
            session.add(topic)

        await session.commit()
        print(f"Created demo course: {course.id}")
        print(f"Exam date: {exam_date.strftime('%Y-%m-%d')}")
        print(f"Topics: {len(topics_data)}")
        return course.id


async def main():
    await init_db()
    await seed_demo_course()


if __name__ == "__main__":
    asyncio.run(main())