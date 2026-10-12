"""Tutor agent: explains topics and answers follow-up questions."""

import logging
from uuid import UUID

from app.agents.base import BaseAgent
from app.prompts.tutor import TUTOR_SYSTEM_PROMPT
from app.schemas import TutorInput, Explanation, FollowUpRequest, FollowUpResponse, TopicRead, TopicNotes, UserLevel

logger = logging.getLogger(__name__)


class TutorAgent(BaseAgent[TutorInput, Explanation]):
    name = "tutor"
    system_prompt = TUTOR_SYSTEM_PROMPT
    output_schema = Explanation

    async def _execute(self, input_data: TutorInput) -> Explanation:
        topic = input_data.topic
        notes = input_data.notes
        level = input_data.level
        follow_up = input_data.follow_up_question
        history = input_data.conversation_history

        # Format notes for prompt
        notes_text = self._format_notes(notes)

        # Build conversation history text
        history_text = ""
        if history:
            history_text = "\n\nCONVERSATION HISTORY:\n"
            for msg in history[-6:]:  # Last 6 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_text += f"{role}: {content}\n"

        if follow_up:
            prompt = f"""The student has a follow-up question about {topic.name}.

TOPIC: {topic.name}
STUDENT LEVEL: {level.value}
NOTES SUMMARY: {notes.summary[:500]}...
{history_text}

FOLLOW-UP QUESTION: {follow_up}

Provide a short, conversational answer (2-3 paragraphs). Address the question directly.
Output ONLY valid JSON with: {{"answer": "..."}}"""
            
            # For follow-ups, we use a simpler schema
            from app.llm import generate_json
            from pydantic import BaseModel
            
            class FollowUpAnswer(BaseModel):
                answer: str
            
            result = await generate_json(
                prompt=prompt,
                schema=FollowUpAnswer,
                system_prompt="You are a helpful tutor. Answer follow-up questions conversationally in 2-3 paragraphs.",
            )
            
            # Return minimal explanation for follow-up
            return Explanation(
                explanation_markdown=result.answer,
                example="",
                common_mistakes=[],
                check_question="",
            )

        # Initial explanation
        prompt = f"""Explain the topic "{topic.name}" for a {level.value} level student.

CONCISE NOTES:
{notes_text}

Provide a clear explanation with analogies, a concrete example, common mistakes, and a check question.
Output ONLY valid JSON matching Explanation schema."""

        result = await self._call_llm(prompt, Explanation)
        return result

    def _format_notes(self, notes: TopicNotes) -> str:
        parts = [f"Summary: {notes.summary}"]
        if notes.key_points:
            parts.append("Key Points:\n- " + "\n- ".join(notes.key_points))
        if notes.definitions:
            parts.append("Definitions:\n- " + "\n- ".join(notes.definitions))
        if notes.formulas_or_examples:
            parts.append("Formulas/Examples:\n- " + "\n- ".join(notes.formulas_or_examples))
        return "\n\n".join(parts)


async def handle_follow_up(
    topic: TopicRead,
    notes: TopicNotes,
    level: UserLevel,
    question: str,
    history: list[dict[str, str]],
    run_id: UUID,
    emit_event,
) -> str:
    """Convenience function for handling follow-up questions."""
    agent = TutorAgent(run_id=run_id, emit_event_callback=emit_event)
    input_data = TutorInput(
        topic=topic,
        notes=notes,
        level=level,
        follow_up_question=question,
        conversation_history=history,
    )
    result = await agent.run(input_data, topic_id=topic.id)
    return result.explanation_markdown