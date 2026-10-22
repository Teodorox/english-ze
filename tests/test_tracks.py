"""Trilhas por objetivo e nível, e o tamanho do dia pelo tempo escolhido."""

import json

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import main, tracks


def _answers(goals, level="iniciante", minutes=10):
    return {"goals": goals, "level": level, "daily_minutes": minutes}


def _fronts(client):
    return {c["front"] for c in client.get("/api/cards").json()}


def _new(client, **params):
    return [c["front"] for c in client.get("/api/session", params=params).json()["new"]]


def _make_due(database, fronts):
    """Finge que essas frases já foram estudadas e venceram hoje."""
    with psycopg.connect(database) as conn:
        conn.execute(
            "UPDATE cards SET introduced_on = '2000-01-01', due = '2000-01-02' WHERE front = ANY(%s)", (list(fronts),)
        )


@pytest.fixture
def fresh(new_user):
    """Conta que ainda vai responder o primeiro acesso."""
    return new_user(onboard=False)


# ---------- Que frases a pessoa ganha ----------

def test_cards_follow_goals_and_level(fresh):
    fresh.post("/api/me/onboarding", json=_answers(["viagem"]))
    # base + viagem, iniciante e básico; nada de streamers nem conversar
    assert _fronts(fresh) == {"Base I1", "Base I2", "Base I3", "Base B1", "Base B2", "Trip I1", "Trip I2",
                              "Trip B1", "Trip B2"}


def test_basic_level_skips_beginner_cards(fresh):
    fresh.post("/api/me/onboarding", json=_answers(["viagem"], level="basico"))
    assert _fronts(fresh) == {"Base B1", "Base B2", "Trip B1", "Trip B2"}


def test_intermediate_starts_at_basic_for_now(fresh):
    fresh.post("/api/me/onboarding", json=_answers(["viagem"], level="intermediario"))
    assert _fronts(fresh) == {"Base B1", "Base B2", "Trip B1", "Trip B2"}


def test_two_people_with_different_goals_get_different_cards(new_user):
    ana, bia = new_user("ana@example.com", onboard=False), new_user("bia@example.com", name="Bia", onboard=False)
    ana.post("/api/me/onboarding", json=_answers(["streamers"]))
    bia.post("/api/me/onboarding", json=_answers(["viagem"]))
    assert "No cap, that was crazy." in _fronts(ana) and "No cap, that was crazy." not in _fronts(bia)
    assert "Trip I1" in _fronts(bia) and "Trip I1" not in _fronts(ana)


def test_card_details_come_from_the_track(fresh, database):
    fresh.post("/api/me/onboarding", json=_answers(["viagem"]))
    with psycopg.connect(database) as conn:
        rows = conn.execute(
            "SELECT front, note, category, source, track, track_level, track_situation, track_step FROM cards"
            " WHERE front IN ('Base I1', 'Trip B1') ORDER BY front"
        ).fetchall()
    assert rows == [
        ("Base I1", "nota", "conversa", "deck inicial", "base", "iniciante", "Base iniciante", 0),
        ("Trip B1", "", "hotel", "deck inicial", "viagem", "basico", "No hotel", 2),  # categoria da situação
    ]


def test_repeating_the_first_access_does_not_duplicate(fresh):
    fresh.post("/api/me/onboarding", json=_answers(["viagem"]))
    count = len(fresh.get("/api/cards").json())
    fresh.post("/api/me/onboarding", json=_answers(["viagem"]))
    assert len(fresh.get("/api/cards").json()) == count


# ---------- Mudar objetivos e nível ----------

def test_new_goal_adds_cards_and_keeps_progress(client):
    card = client.get("/api/session?new_limit=1").json()["new"][0]
    client.post(f"/api/cards/{card['id']}/review", json={"grade": 2})
    res = client.patch("/api/me", json={"goals": ["viagem"]})
    assert res.status_code == 200, res.text
    fronts = _fronts(client)
    assert "Trip I1" in fronts
    assert "Stream I2" in fronts  # objetivo que saiu: as frases ficam
    same = next(c for c in client.get("/api/cards").json() if c["id"] == card["id"])
    assert same["reps"] == 1  # o progresso continua


def test_removed_goal_goes_to_the_end_of_the_queue(client):
    client.patch("/api/me", json={"goals": ["viagem"]})
    fronts = _new(client, new_limit=100)
    first_old = min(i for i, f in enumerate(fronts) if f.startswith(("Stream", "Talk", "No cap")))
    assert all(f.startswith(("Base", "Trip")) for f in fronts[:first_old])
    assert first_old == 9  # todas as frases de base + viagem antes


def test_changing_level_puts_easier_cards_last(client):
    client.patch("/api/me", json={"level": "basico"})
    fronts = _new(client, new_limit=100)
    assert fronts[:4] == ["Base B1", "Stream B1", "Base B2", "Stream B2"]


def test_tracks_are_interleaved(client):
    # base, streamers e conversar se revezam: a sessão não fica toda num tema só
    assert _new(client, new_limit=6) == ["Base I1", "No cap, that was crazy.", "Talk I1",
                                         "Base I2", "Stream I2", "Talk I2"]


def test_a_phrase_the_person_already_mined_stays_theirs(fresh, database):
    fresh.post("/api/cards", json={"front": "Trip I1", "back": "Minha tradução", "source": "live"})
    fresh.post("/api/me/onboarding", json=_answers(["viagem"]))
    with psycopg.connect(database) as conn:
        row = conn.execute("SELECT back, source, track FROM cards WHERE front = 'Trip I1'").fetchone()
    assert row == ("Minha tradução", "live", None)


# ---------- Tamanho do dia ----------

@pytest.mark.parametrize(("minutes", "expected"), [(5, 3), (10, 5), (15, 8)])
def test_new_cards_per_day_follow_the_time(client, minutes, expected):
    client.patch("/api/me", json={"daily_minutes": minutes})
    data = client.get("/api/session").json()
    assert len(data["new"]) == expected and data["new_per_day"] == expected and data["held_back"] is False


def test_daily_plan_table_covers_every_time_option():
    assert set(main.NEW_PER_DAY) == {5, 10, 15, 20, 30}
    assert main.NEW_PER_DAY[30] == 15


def test_new_cards_already_seen_today_count(client):
    client.patch("/api/me", json={"daily_minutes": 5})
    for card in client.get("/api/session").json()["new"][:2]:
        client.post(f"/api/cards/{card['id']}/review", json={"grade": 2})
    assert len(client.get("/api/session").json()["new"]) == 1


def test_piled_up_reviews_hold_back_new_cards(client, database, monkeypatch):
    monkeypatch.setattr(main, "REVIEWS_PER_MINUTE", 1)
    client.patch("/api/me", json={"daily_minutes": 5})  # teto de 5 revisões, 3 novas
    _make_due(database, ["Base B1", "Base B2", "Stream B1"])  # metade do teto: metade das novas
    data = client.get("/api/session").json()
    assert (len(data["due"]), len(data["new"]), data["held_back"]) == (3, 2, True)

    _make_due(database, ["Stream B2", "Talk I3", "Base I3"])  # passou do teto: nenhuma nova
    data = client.get("/api/session").json()
    assert (len(data["due"]), data["due_total"], len(data["new"]), data["held_back"]) == (5, 6, 0, True)


def test_session_without_first_access_is_empty(fresh):
    data = fresh.get("/api/session").json()
    assert data["due"] == [] and data["new"] == []


# ---------- Frases novas chegam a quem já tem conta ----------

def test_new_phrases_reach_existing_accounts_on_restart(client, test_tracks):
    track = json.loads((test_tracks / "viagem.json").read_text(encoding="utf-8"))
    client.patch("/api/me", json={"goals": ["viagem"]})
    track["situations"][0]["cards"].append({"front": "Trip I3", "back": "Trip i3"})
    (test_tracks / "viagem.json").write_text(json.dumps(track), encoding="utf-8")
    tracks._load.cache_clear()
    with TestClient(main.app):  # subir o servidor de novo
        pass
    assert "Trip I3" in _fronts(client)


# ---------- Arquivos de trilha ----------

def _write(folder, name, track):
    (folder / f"{name}.json").write_text(json.dumps(track), encoding="utf-8")


def _situation(**changes):
    return {"level": "iniciante", "title": "T", "cards": [{"front": "Hi", "back": "Oi"}], **changes}


@pytest.mark.parametrize(
    ("name", "track", "message"),
    [
        ("hackear", {"category": "x", "situations": [_situation()]}, "trilha desconhecida"),
        ("viagem", {"category": "x", "situations": [_situation(level="fluente")]}, "nível desconhecido"),
        ("viagem", {"category": "x", "situations": []}, "sem situações"),
        ("viagem", {"category": "x", "situations": [_situation(cards=[])]}, "sem frases"),
        ("viagem", {"category": "x", "situations": [_situation(cards=[{"front": "Hi"}])]}, "back"),
        ("viagem", {"category": "x", "situations": [_situation(cards=[{"front": "x" * 501, "back": "y"}])]}, "front"),
        ("viagem", {"category": "", "situations": [_situation()]}, "category"),
        ("viagem", {"category": "x", "situations": [_situation(), _situation()]}, "duas vezes"),
    ],
)
def test_broken_track_files_are_rejected(tmp_path, name, track, message):
    folder = tmp_path / "broken"
    folder.mkdir()
    _write(folder, name, track)
    with pytest.raises(tracks.TrackError, match=message):
        tracks._load(folder)


def test_same_phrase_in_two_tracks_is_rejected(tmp_path):
    folder = tmp_path / "twice"
    folder.mkdir()
    _write(folder, "viagem", {"category": "x", "situations": [_situation()]})
    _write(folder, "series", {"category": "x", "situations": [_situation()]})
    with pytest.raises(tracks.TrackError, match="duas vezes"):
        tracks._load(folder)


def test_real_tracks_are_valid():
    """As frases de verdade (data/tracks): todo objetivo tem trilha, com iniciante e básico."""
    real = tracks._load(tracks.DEFAULT_DIR)
    assert set(real) == {tracks.BASE_TRACK, *tracks.GOALS}
    for name, cards in real.items():
        levels = {c.level for c in cards}
        assert {"iniciante", "basico"} <= levels, name
        assert all(c.back != c.front for c in cards), name
