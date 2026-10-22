"""Opções de resposta do estudo ativo: as traduções erradas que aparecem junto com a certa.

Primeiro entram as pegadinhas do card (traduções quase certas, escritas à mão nas trilhas):
uma na primeira rodada de opções, duas na segunda, que é a última antes de digitar. O resto
vem dos outros cards da própria pessoa, os mais parecidos com a resposta certa: mais
palavras em comum, depois o mesmo tema e o tamanho parecido. Assim não dá pra acertar só
porque a certa é a única que fala do assunto.
"""

import random
import unicodedata

CHOICES = 3  # opções erradas por card (com a certa, ficam 4)
# Palavras que não dizem nada sobre o sentido: não contam como "em comum".
STOPWORDS = {"a", "o", "as", "os", "e", "de", "do", "da", "dos", "das", "um", "uma", "em", "no", "na", "nos", "nas",
             "que", "pra", "para", "por", "com", "se", "ao"}


def answer_key(text: str) -> str:
    """Pra comparar traduções: sem acento, maiúscula, pontuação nem espaço sobrando."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in plain).split())


def traps_for_round(reps: int) -> int:
    """Quantas pegadinhas usar: 1 na primeira rodada de opções (reps 0 ou 1), 2 na segunda."""
    return 1 if reps <= 1 else 2


def _words(text: str) -> set[str]:
    return set(answer_key(text).split()) - STOPWORDS


def _closeness(card: dict, other: dict, words: set[str]) -> float:
    """Quanto a outra tradução parece a certa: palavras em comum pesam mais, depois o tema e o tamanho."""
    shared = len(words & _words(other["back"]))
    same_theme = other["category"] == card["category"]
    return 10 * shared + 3 * same_theme - abs(len(other["back"]) - len(card["back"])) / 10


def distractors(card: dict, pool: list[dict], rng: random.Random, k: int = CHOICES) -> list[str]:
    """k traduções erradas pro card: pegadinhas dele e cards parecidos do pool (id, back, category)."""
    seen = {answer_key(card["back"])}
    chosen = []
    traps = [t for t in card.get("traps") or [] if answer_key(t)]
    for trap in rng.sample(traps, min(len(traps), traps_for_round(card.get("reps", 0)), k)):
        if answer_key(trap) not in seen:
            seen.add(answer_key(trap))
            chosen.append(trap)

    words = _words(card["back"])
    candidates = []
    for other in pool:
        key = answer_key(other["back"])
        if other["id"] == card["id"] or not key or key in seen:
            continue
        seen.add(key)
        # Um sorteio pequeno (até 2 pontos) varia as opções entre as parecidas, sem passar na frente das melhores.
        candidates.append((_closeness(card, other, words) + 2 * rng.random(), other["back"]))
    candidates.sort(reverse=True)
    chosen += [back for _, back in candidates[: k - len(chosen)]]
    return chosen


def add_choices(cards: list[dict], pool: list[dict], rng: random.Random | None = None) -> None:
    """Põe em cada card as opções erradas (lista vazia se a pessoa tem poucos cards)."""
    rng = rng or random.Random()
    for card in cards:
        options = distractors(card, pool, rng)
        card["choices"] = options if len(options) == CHOICES else []
