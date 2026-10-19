from datetime import date, timedelta


def compute_streak(study_days: set[date], today: date) -> int:
    """Dias seguidos de estudo. Se ainda não estudou hoje, conta a partir de ontem."""
    current = today if today in study_days else today - timedelta(days=1)
    streak = 0
    while current in study_days:
        streak += 1
        current -= timedelta(days=1)
    return streak
