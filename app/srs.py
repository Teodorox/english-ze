"""Repetição espaçada no estilo SM-2 (o mesmo princípio do Anki).

Cada card guarda uma "facilidade" (ease) e um intervalo em dias. Quando você
acerta, o intervalo cresce multiplicado pela facilidade; quando erra, o card
volta para o começo e fica um pouco "mais difícil" daqui pra frente.
"""

from dataclasses import dataclass
from datetime import date, timedelta

AGAIN, HARD, GOOD, EASY = 0, 1, 2, 3
GRADES = (AGAIN, HARD, GOOD, EASY)

START_EASE = 2.5
MIN_EASE = 1.3


@dataclass(frozen=True)
class CardState:
    ease: float = START_EASE
    interval_days: int = 0
    reps: int = 0
    lapses: int = 0


def schedule(state: CardState, grade: int, today: date) -> tuple[CardState, date]:
    """Retorna o novo estado do card e a data da próxima revisão."""
    if grade not in GRADES:
        raise ValueError(f"nota inválida: {grade}")

    ease, interval, reps = state.ease, state.interval_days, state.reps

    if grade == AGAIN:
        # Errou: volta pro início e revisa de novo hoje mesmo.
        new_state = CardState(max(MIN_EASE, ease - 0.2), 0, 0, state.lapses + 1)
        return new_state, today

    if grade == HARD:
        interval = 1 if reps == 0 else max(interval + 1, round(interval * 1.2))
        ease = max(MIN_EASE, ease - 0.15)
    elif grade == GOOD:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = max(3, interval + 1)
        else:
            interval = max(interval + 1, round(interval * ease))
    else:  # EASY
        interval = 4 if reps == 0 else max(interval + 2, round(interval * ease * 1.3))
        ease += 0.15

    new_state = CardState(ease, interval, reps + 1, state.lapses)
    return new_state, today + timedelta(days=interval)
