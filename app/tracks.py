"""Trilhas de estudo: as frases escritas à mão pra cada objetivo, por nível e situação.

Cada arquivo de data/tracks é uma trilha: um objetivo do primeiro acesso, ou a "base"
que todo mundo recebe. A conta ganha as frases dos objetivos dela, a partir do nível dela,
quando termina o primeiro acesso ou muda os objetivos. Nada é apagado quando um objetivo
sai: as frases ficam, só perdem a prioridade na fila de novos.
"""

import json
import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import psycopg

from . import db

DEFAULT_DIR = db.ROOT / "data" / "tracks"
BASE_TRACK = "base"
# As mesmas listas do banco (migrações 004 e 007) e da API.
GOALS = ("streamers", "conversar", "trabalho", "musica", "viagem", "series", "provas")
LEVELS = ("iniciante", "basico", "intermediario")
# A partir do nível da pessoa. Ainda não há frases de intermediário escritas à mão
# (vêm da IA na etapa 6), então quem é intermediário começa pelo básico.
LEVELS_FOR = {"iniciante": ("iniciante", "basico"), "basico": ("basico",), "intermediario": ("basico",)}
MAX_FRONT, MAX_BACK, MAX_NOTE, MAX_CATEGORY, MAX_SITUATION = 500, 500, 1000, 40, 80


class TrackError(ValueError):
    """Arquivo de trilha com problema (mensagem diz qual e onde)."""


@dataclass(frozen=True)
class TrackCard:
    track: str
    level: str
    situation: str
    step: int  # ordem dentro da trilha: o nível mais fácil primeiro, depois a ordem do arquivo
    front: str
    back: str
    note: str
    category: str


def tracks_dir() -> Path:
    return Path(os.environ.get("ENGLISH_ZE_TRACKS_DIR") or DEFAULT_DIR)


def _text(value, limit: int, where: str, *, required: bool = True) -> str:
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > limit:
        raise TrackError(f"{where}: texto vazio, inválido ou maior que {limit} caracteres")
    return value.strip()


def _load_file(path: Path) -> list[TrackCard]:
    track = path.stem
    if track not in (BASE_TRACK, *GOALS):
        raise TrackError(f"{path.name}: trilha desconhecida (o nome do arquivo tem que ser um objetivo ou 'base')")
    data = json.loads(path.read_text(encoding="utf-8"))
    default_category = _text(data.get("category"), MAX_CATEGORY, f"{path.name} category")
    situations = data.get("situations")
    if not isinstance(situations, list) or not situations:
        raise TrackError(f"{path.name}: sem situações")
    for i, s in enumerate(situations):
        if s.get("level") not in LEVELS:
            raise TrackError(f"{path.name} situação {i + 1}: nível desconhecido")
    # sorted é estável: dentro do mesmo nível vale a ordem do arquivo
    situations = sorted(situations, key=lambda s: LEVELS.index(s["level"]))
    cards = []
    for s in situations:
        title = _text(s.get("title"), MAX_SITUATION, f"{path.name} título")
        category = _text(s.get("category", default_category), MAX_CATEGORY, f"{path.name} {title} category")
        if not isinstance(s.get("cards"), list) or not s["cards"]:
            raise TrackError(f"{path.name} {title}: sem frases")
        for c in s["cards"]:
            where = f"{path.name} {title}"
            cards.append(TrackCard(
                track=track,
                level=s["level"],
                situation=title,
                step=len(cards),
                front=_text(c.get("front"), MAX_FRONT, f"{where} front"),
                back=_text(c.get("back"), MAX_BACK, f"{where} back"),
                note=_text(c.get("note", ""), MAX_NOTE, f"{where} note", required=False),
                category=category,
            ))
    return cards


@cache
def _load(directory: Path) -> dict[str, list[TrackCard]]:
    tracks = {path.stem: _load_file(path) for path in sorted(directory.glob("*.json"))}
    # Cada conta tem no máximo um card por frase: a mesma frase em duas trilhas brigaria pelo lugar.
    seen: dict[str, str] = {}
    for track, cards in tracks.items():
        for card in cards:
            if card.front in seen:
                raise TrackError(f"A frase {card.front!r} aparece duas vezes ({seen[card.front]}.json e {track}.json)")
            seen[card.front] = track
    return tracks


def load() -> dict[str, list[TrackCard]]:
    """Todas as trilhas, validadas (lidas uma vez por processo)."""
    return _load(tracks_dir())


def tracks_for(goals: list[str]) -> list[str]:
    return [BASE_TRACK, *(g for g in GOALS if g in goals)]


def cards_for(goals: list[str], level: str | None) -> list[TrackCard]:
    """As frases que essa pessoa deve ter, nas trilhas dela e a partir do nível dela."""
    if not goals or level not in LEVELS_FOR:
        return []
    tracks, levels = load(), LEVELS_FOR[level]
    return [c for t in tracks_for(goals) for c in tracks.get(t, []) if c.level in levels]


def sync_user(conn: psycopg.Connection, user_id: int, goals: list[str], level: str | None) -> None:
    """Põe na conta as frases das trilhas dela que ainda faltam (não apaga nem mexe no progresso).

    Se a frase já existe como card do deck inicial, só atualiza de que trilha ela é. Um card
    que a pessoa criou com a mesma frase (minerado, do diário) continua sendo dela, intocado.
    """
    rows = [
        (user_id, c.front, c.back, c.note, c.category, db.SEED_SOURCE, c.track, c.level, c.situation, c.step,
         db.SEED_SOURCE)
        for c in cards_for(goals, level)
    ]
    if not rows:
        return
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO cards (user_id, front, back, note, category, source,"
            " track, track_level, track_situation, track_step)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (user_id, front) DO UPDATE SET track = EXCLUDED.track,"
            " track_level = EXCLUDED.track_level, track_situation = EXCLUDED.track_situation,"
            " track_step = EXCLUDED.track_step"
            " WHERE cards.source = %s",
            rows,
        )


def sync_everyone(conn: psycopg.Connection) -> int:
    """Ao subir o servidor: frases novas escritas nas trilhas chegam a quem já tem conta."""
    users = conn.execute("SELECT id, goals, level FROM users WHERE onboarded_at IS NOT NULL").fetchall()
    for user in users:
        sync_user(conn, user["id"], user["goals"], user["level"])
    return len(users)
