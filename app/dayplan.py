"""Plano de hoje: o que estudar, no tamanho do tempo escolhido e com a cara dos objetivos.

Cada passo diz quanto falta e se já foi feito; os "feitos" saem do que o servidor já
registra (revisões, checagens de pronúncia, entradas do diário, frases mineradas hoje).
"""

from datetime import date

# Quanto de cada coisa cabe no tempo do dia (as frases do Estudar vêm do NEW_PER_DAY do main).
SPEECH_PER_DAY = {5: 1, 10: 2, 15: 3, 20: 3, 30: 5}
JOURNAL_PER_DAY = {5: 0, 10: 0, 15: 1, 20: 1, 30: 1}
MINE_PER_DAY = {5: 0, 10: 0, 15: 0, 20: 1, 30: 2}

# O diário e o "minerar" ganham a cara do objetivo do dia (os objetivos se revezam).
JOURNAL_PROMPTS = {
    "streamers": "Conte em inglês o que você assistiu ou jogou hoje.",
    "conversar": "Escreva 3 frases sobre o seu dia, como se contasse pra um amigo.",
    "trabalho": "Escreva 3 frases sobre o seu dia de trabalho.",
    "musica": "Escreva sobre uma música que você ouviu hoje e por que gosta dela.",
    "viagem": "Descreva uma viagem que você fez ou quer fazer.",
    "series": "Conte o que aconteceu no último episódio que você viu.",
    "provas": "Dê sua opinião sobre um assunto em 3 frases, usando um conectivo (however, therefore...).",
}
MINE_SOURCES = {
    "streamers": "de uma live",
    "conversar": "de um vídeo ou podcast",
    "trabalho": "de uma reunião, e-mail ou documentação",
    "musica": "de uma música",
    "viagem": "de um vídeo de viagem",
    "series": "de uma série",
    "provas": "de um texto em inglês",
}
DEFAULT_GOAL = "conversar"


def goal_of_the_day(goals: list[str], day: date) -> str:
    """Um objetivo por dia, em rodízio: quem escolheu vários vê um tema diferente a cada dia."""
    return goals[day.toordinal() % len(goals)] if goals else DEFAULT_GOAL


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def plan(minutes: int, goals: list[str], day: date, progress: dict) -> dict:
    """Os passos de hoje. progress: reviewed, due_left, new_left, speech, journal, mined (contagens de hoje)."""
    goal = goal_of_the_day(goals, day)
    items = []

    left = progress["due_left"] + progress["new_left"]
    parts = []
    if progress["due_left"]:
        parts.append(_plural(progress["due_left"], "revisão", "revisões"))
    if progress["new_left"]:
        parts.append(_plural(progress["new_left"], "frase nova", "frases novas"))
    items.append({
        "id": "study",
        "title": "Estudar as frases",
        "detail": " e ".join(parts) if parts else "Tudo revisado por hoje.",
        "path": "/estudar",
        "count": progress["reviewed"],
        "target": progress["reviewed"] + left,
        "done": left == 0,
    })

    speech = SPEECH_PER_DAY[minutes]
    items.append({
        "id": "speak",
        "title": "Falar em voz alta",
        "detail": f"Fale {_plural(speech, 'frase', 'frases')} e confira a pronúncia.",
        "path": "/falar",
        "count": min(progress["speech"], speech),
        "target": speech,
        "done": progress["speech"] >= speech,
    })

    if JOURNAL_PER_DAY[minutes]:
        items.append({
            "id": "journal",
            "title": "Escrever no diário",
            "detail": JOURNAL_PROMPTS[goal],
            "path": "/diario",
            "count": min(progress["journal"], 1),
            "target": 1,
            "done": progress["journal"] >= 1,
        })

    mine = MINE_PER_DAY[minutes]
    if mine:
        items.append({
            "id": "mine",
            "title": "Minerar frases",
            "detail": f"Anote {_plural(mine, 'frase', 'frases')} {MINE_SOURCES[goal]} que você não entendeu.",
            "path": "/minerar",
            "count": min(progress["mined"], mine),
            "target": mine,
            "done": progress["mined"] >= mine,
        })

    return {"minutes": minutes, "goal": goal, "items": items, "done": all(i["done"] for i in items)}
