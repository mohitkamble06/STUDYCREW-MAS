"""Tests for tracker (mastery updates)."""

import pytest

from app.agents.tracker import calculate_new_mastery, MASTERY_DECAY, MASTERY_WEIGHT


class TestCalculateNewMastery:
    """Tests for mastery calculation formula."""

    def test_initial_mastery_zero(self):
        """New topic starts at 0.0, first quiz updates correctly."""
        new_mastery = calculate_new_mastery(0.0, 1.0)  # Perfect score
        expected = MASTERY_DECAY * 0.0 + MASTERY_WEIGHT * 1.0
        assert new_mastery == pytest.approx(expected)
        assert new_mastery == 0.3

    def test_perfect_score_increases_mastery(self):
        """Perfect quiz scores gradually increase mastery."""
        mastery = 0.0
        for _ in range(5):
            mastery = calculate_new_mastery(mastery, 1.0)
        # After 5 perfect scores: approaches 1.0 but never reaches it
        assert 0.8 < mastery < 1.0

    def test_zero_score_decreases_mastery(self):
        """Zero quiz scores decay mastery toward 0."""
        mastery = 1.0
        for _ in range(5):
            mastery = calculate_new_mastery(mastery, 0.0)
        assert 0.0 < mastery < 0.2

    def test_mixed_scores(self):
        """Mixed scores converge to average performance."""
        mastery = 0.5
        scores = [0.8, 0.6, 0.9, 0.7, 0.8]
        for score in scores:
            mastery = calculate_new_mastery(mastery, score)
        # Should be around the weighted average of recent scores
        assert 0.6 < mastery < 0.9

    def test_bounds_enforced(self):
        """Mastery always stays in [0, 1]."""
        # Test upper bound
        mastery = calculate_new_mastery(0.99, 1.0)
        assert mastery <= 1.0

        # Test lower bound
        mastery = calculate_new_mastery(0.01, 0.0)
        assert mastery >= 0.0

    def test_formula_weights(self):
        """Verify the exact formula weights."""
        # new = 0.7 * old + 0.3 * score
        old = 0.5
        score = 1.0
        new = calculate_new_mastery(old, score)
        expected = 0.7 * old + 0.3 * score
        assert new == pytest.approx(expected)

        old = 0.5
        score = 0.0
        new = calculate_new_mastery(old, score)
        expected = 0.7 * old + 0.3 * score
        assert new == pytest.approx(expected)