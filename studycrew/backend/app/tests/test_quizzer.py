"""Tests for quiz grading."""

import pytest
from uuid import uuid4

from app.agents.quizzer import grade_quiz, Quiz, QuizQuestion, DifficultyLevel


class TestGradeQuiz:
    """Tests for quiz grading logic."""

    def test_all_correct(self):
        """All answers correct -> score 1.0"""
        quiz = Quiz(
            topic_id=uuid4(),
            questions=[
                QuizQuestion(
                    id=uuid4(),
                    question="Q1",
                    options=["A", "B", "C", "D"],
                    correct_index=0,
                    explanation="E1",
                    difficulty=DifficultyLevel.EASY,
                ),
                QuizQuestion(
                    id=uuid4(),
                    question="Q2",
                    options=["A", "B", "C", "D"],
                    correct_index=1,
                    explanation="E2",
                    difficulty=DifficultyLevel.MEDIUM,
                ),
            ],
        )
        answers = {quiz.questions[0].id: 0, quiz.questions[1].id: 1}
        score, correct, explanations = grade_quiz(quiz, answers)

        assert score == 1.0
        assert correct == 2
        assert len(explanations) == 2

    def test_all_wrong(self):
        """All answers wrong -> score 0.0"""
        quiz = Quiz(
            topic_id=uuid4(),
            questions=[
                QuizQuestion(
                    id=uuid4(),
                    question="Q1",
                    options=["A", "B", "C", "D"],
                    correct_index=0,
                    explanation="E1",
                ),
            ],
        )
        answers = {quiz.questions[0].id: 1}  # Wrong answer
        score, correct, explanations = grade_quiz(quiz, answers)

        assert score == 0.0
        assert correct == 0

    def test_partial_correct(self):
        """Some correct, some wrong"""
        quiz = Quiz(
            topic_id=uuid4(),
            questions=[
                QuizQuestion(id=uuid4(), question="Q1", options=["A", "B", "C", "D"], correct_index=0, explanation="E1"),
                QuizQuestion(id=uuid4(), question="Q2", options=["A", "B", "C", "D"], correct_index=1, explanation="E2"),
                QuizQuestion(id=uuid4(), question="Q3", options=["A", "B", "C", "D"], correct_index=2, explanation="E3"),
                QuizQuestion(id=uuid4(), question="Q4", options=["A", "B", "C", "D"], correct_index=3, explanation="E4"),
            ],
        )
        answers = {
            quiz.questions[0].id: 0,  # Correct
            quiz.questions[1].id: 0,  # Wrong
            quiz.questions[2].id: 2,  # Correct
            quiz.questions[3].id: 2,  # Wrong
        }
        score, correct, explanations = grade_quiz(quiz, answers)

        assert score == 0.5
        assert correct == 2

    def test_missing_answers_counted_wrong(self):
        """Missing answers should be treated as wrong"""
        quiz = Quiz(
            topic_id=uuid4(),
            questions=[
                QuizQuestion(id=uuid4(), question="Q1", options=["A", "B", "C", "D"], correct_index=0, explanation="E1"),
                QuizQuestion(id=uuid4(), question="Q2", options=["A", "B", "C", "D"], correct_index=1, explanation="E2"),
            ],
        )
        answers = {quiz.questions[0].id: 0}  # Only answered first
        score, correct, explanations = grade_quiz(quiz, answers)

        assert score == 0.5
        assert correct == 1

    def test_explanations_returned(self):
        """Explanations for all questions should be returned"""
        q1_id = uuid4()
        q2_id = uuid4()
        quiz = Quiz(
            topic_id=uuid4(),
            questions=[
                QuizQuestion(id=q1_id, question="Q1", options=["A", "B", "C", "D"], correct_index=0, explanation="Expl 1"),
                QuizQuestion(id=q2_id, question="Q2", options=["A", "B", "C", "D"], correct_index=1, explanation="Expl 2"),
            ],
        )
        answers = {q1_id: 0, q2_id: 1}
        _, _, explanations = grade_quiz(quiz, answers)

        assert explanations[q1_id] == "Expl 1"
        assert explanations[q2_id] == "Expl 2"

    def test_empty_quiz(self):
        """Empty quiz should return 0 score"""
        quiz = Quiz(topic_id=uuid4(), questions=[])
        score, correct, explanations = grade_quiz(quiz, {})

        assert score == 0.0
        assert correct == 0
        assert explanations == {}