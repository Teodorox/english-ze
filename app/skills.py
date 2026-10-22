"""Nível por habilidade (vocabulário, escuta, fala, escrita): uma estimativa, não um certificado.

Cada habilidade começa no nível que a pessoa escolheu no primeiro acesso e muda com o que ela
faz no app: os acertos puxam pra cima ou pra baixo (com mais peso quanto mais dados houver) e o
volume praticado vai somando. A escala vai de 0 a 4, uma faixa do Quadro Europeu (QECR) por ponto:
A1 [0, 1), A2 [1, 2), B1 [2, 3), B2 [3, 4). Não passa de B2: o conteúdo do app não vai além disso.
"""

import re
from dataclasses import dataclass

BANDS = ("A1", "A2", "B1", "B2")
TOP = len(BANDS) - 0.01

# Ponto de partida pelo nível escolhido ("Estou começando", "Me viro", "Intermediário"). Quem se vira
# ou já é intermediário começa um pouco dentro da faixa: um erro no começo não derruba pra faixa de baixo.
START = {"iniciante": 0.0, "basico": 1.3, "intermediario": 2.3}
START_UNKNOWN = 0.3

# Acerto "normal": nem sobe nem desce. 100% de acerto sobe até MAX_UP; acertar pouco desce até MAX_DOWN.
EXPECTED = 0.75
MAX_UP = 0.5
MAX_DOWN = 0.6
MAX_GROWTH = 1.5


@dataclass(frozen=True)
class Skill:
    id: str
    # Quantos dados pra a nota de acerto valer pela metade (n / (n + half_weight)).
    half_weight: int
    # Quanto volume pra subir uma faixa inteira.
    per_band: int


SKILLS = (
    Skill("vocabulary", half_weight=30, per_band=100),  # frases dominadas (21+ dias)
    Skill("listening", half_weight=30, per_band=150),  # ditados certos no Ouvir
    Skill("speaking", half_weight=15, per_band=100),  # checagens de pronúncia com 80+
    Skill("writing", half_weight=5, per_band=40),  # entradas do diário
)

GOOD_SPEECH = 80
WORD = re.compile(r"[A-Za-z']+")


def review_score(grade: int) -> float:
    """Certo (2 ou 3) vale 1, quase (1) vale meio, errado (0) vale nada."""
    return 1.0 if grade >= 2 else 0.5 if grade == 1 else 0.0


def writing_score(text: str, mistakes: int) -> float:
    """1 sem erros; cada erro a cada 10 palavras tira meio ponto."""
    words = max(1, len(WORD.findall(text)))
    return max(0.0, 1.0 - 5.0 * mistakes / words)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def estimate(level: str | None, skill: Skill, scores: list[float], volume: int) -> dict:
    """scores: notas recentes de 0 a 1 (acertos). volume: quanto já praticou (pra crescer)."""
    start = START.get(level, START_UNKNOWN) if level else START_UNKNOWN
    n = len(scores)
    accuracy = sum(scores) / n if n else None
    weight = n / (n + skill.half_weight)
    performance = weight * _clamp((accuracy - EXPECTED) * 2, -MAX_DOWN, MAX_UP) if n else 0.0
    growth = min(MAX_GROWTH, volume / skill.per_band)
    value = _clamp(start + performance + growth, 0.0, TOP)
    band = int(value)
    return {
        "id": skill.id,
        "value": round(value, 2),
        "band": BANDS[band],
        # Quanto já andou dentro da faixa (0 a 1), pra barrinha até a próxima.
        "progress": round(value - band, 2),
        "next_band": BANDS[band + 1] if band + 1 < len(BANDS) else None,
        "samples": n,
        "accuracy": round(accuracy, 2) if accuracy is not None else None,
        "start_band": BANDS[int(start)],
    }


def estimate_all(level: str | None, evidence: dict[str, tuple[list[float], int]]) -> list[dict]:
    return [estimate(level, skill, *evidence[skill.id]) for skill in SKILLS]
