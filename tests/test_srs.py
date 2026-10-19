from datetime import date, timedelta

import pytest

from app import srs
from app.progress import compute_streak

TODAY = date(2026, 10, 18)


def test_first_good_is_one_day():
    state, due = srs.schedule(srs.CardState(), srs.GOOD, TODAY)
    assert state.interval_days == 1
    assert state.reps == 1
    assert due == TODAY + timedelta(days=1)


def test_intervals_grow_with_good_answers():
    state = srs.CardState()
    intervals = []
    for _ in range(5):
        state, _ = srs.schedule(state, srs.GOOD, TODAY)
        intervals.append(state.interval_days)
    assert intervals == sorted(intervals)
    assert intervals[:2] == [1, 3]
    assert intervals[-1] > 20


def test_again_resets_and_lowers_ease():
    state = srs.CardState(ease=2.5, interval_days=10, reps=4)
    state, due = srs.schedule(state, srs.AGAIN, TODAY)
    assert (state.reps, state.interval_days, state.lapses) == (0, 0, 1)
    assert state.ease == pytest.approx(2.3)
    assert due == TODAY


def test_ease_never_below_minimum():
    state = srs.CardState(ease=1.35)
    for _ in range(5):
        state, _ = srs.schedule(state, srs.AGAIN, TODAY)
    assert state.ease == srs.MIN_EASE


def test_easy_beats_good():
    base = srs.CardState(interval_days=10, reps=3)
    good, _ = srs.schedule(base, srs.GOOD, TODAY)
    easy, _ = srs.schedule(base, srs.EASY, TODAY)
    assert easy.interval_days > good.interval_days


def test_invalid_grade():
    with pytest.raises(ValueError):
        srs.schedule(srs.CardState(), 7, TODAY)


def test_streak_counts_from_yesterday_if_not_studied_today():
    days = {TODAY - timedelta(days=i) for i in (1, 2, 3)}
    assert compute_streak(days, TODAY) == 3
    assert compute_streak(days | {TODAY}, TODAY) == 4
    assert compute_streak({TODAY - timedelta(days=2)}, TODAY) == 0
