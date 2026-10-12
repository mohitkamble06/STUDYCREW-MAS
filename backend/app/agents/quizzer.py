"""Quizzer agent: generates multiple-choice quizzes."""

import logging
from uuid import UUID

from app.agents.base import BaseAgent
from app.prompts.quizzer import QUIZZER_SYSTEM_PROMPT
from app.schemas import Quiz, QuizQuestion, DifficultyLevel, TopicRead, TopicNotes

logger = logging.getLogger(__name__)


class QuizzerAgent(BaseAgent[dict, Quiz]):
    name = "quizzer"
    system_prompt = QUIZZER_SYSTEM_PROMPT
    output_schema = Quiz

    async def _execute(self, input_data: dict) -> Quiz:
        topic_id = input_data["topic_id"]
        topic = input_data["topic"]
        notes = input_data["notes"]
        num_questions = input_data.get("num_questions", 5)
        difficulty = input_data.get("difficulty")

        # Determine difficulty from mastery if not specified
        if difficulty is None:
            mastery = topic.mastery
            if mastery < 0.3:
                difficulty = DifficultyLevel.EASY
            elif mastery < 0.7:
                difficulty = DifficultyLevel.MEDIUM
            else:
                difficulty = DifficultyLevel.HARD

        notes_text = self._format_notes(notes)

        prompt = f"""Generate {num_questions} multiple-choice questions for: {topic.name}

DIFFICULTY: {difficulty.value}
NOTES:
{notes_text}

Requirements:
- Exactly 4 options per question, 1 correct
- Vary question types (definition, concept, application, analysis)
- Each question needs clear explanation
- Match the target difficulty: {difficulty.value}
- Output ONLY valid JSON matching Quiz schema"""

        result = await self._call_llm(prompt, Quiz)

        # Ensure topic_id is set
        result.topic_id = topic_id

        # Validate each question has 4 options
        for q in result.questions:
            if len(q.options) != 4:
                raise ValueError(f"Question {q.id} must have exactly 4 options, got {len(q.options)}")
            if not 0 <= q.correct_index <= 3:
                raise ValueError(f"Question {q.id} correct_index must be 0-3, got {q.correct_index}")

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


def grade_quiz(quiz: Quiz, answers: dict[UUID, int]) -> tuple[float, int, dict[UUID, str]]:
    """
    Grade a quiz submission in pure Python.

    Returns:
        (score: 0.0-1.0, correct_count, explanations_dict)
    """
    correct_count = 0
    explanations = {}

    for question in quiz.questions:
        qid = question.id
        chosen = answers.get(qid)
        is_correct = chosen == question.correct_index

        if is_correct:
            correct_count += 1

        explanations[qid] = question.explanation

    score = correct_count / len(quiz.questions) if quiz.questions else 0.0
    return score, correct_count, explanations