"""Aba Hoje: o plano do dia pelo tempo e pelos objetivos, com os "feitos" automáticos."""

from datetime import date

import psycopg
import pytest

from app import dayplan, main

DAY = date(2026, 10, 22)
NOTHING = {"reviewed": 0, "due_left": 3, "new_left": 5, "speech": 0, "journal": 0, "mined": 0}


def _ids(result):
    return [i["id"] for i in result["items"]]


def _item(result, id):
    return next(i for i in result["items"] if i["id"] == id)


# ---------- O plano ----------

@pytest.mark.parametrize(
    ("minutes", "ids", "speech"),
    [
        (5, ["study", "speak"], 1),
        (10, ["study", "speak"], 2),
        (15, ["study", "speak", "journal"], 3),
        (20, ["study", "speak", "journal", "mine"], 3),
        (30, ["study", "speak", "journal", "mine"], 5),
    ],
)
def test_plan_grows_with_the_time(minutes, ids, speech):
    result = dayplan.plan(minutes, ["viagem"], DAY, NOTHING)
    assert _ids(result) == ids
    assert _item(result, "speak")["target"] == speech


def test_every_time_option_has_a_plan():
    for table in (dayplan.SPEECH_PER_DAY, dayplan.JOURNAL_PER_DAY, dayplan.MINE_PER_DAY):
        assert set(table) == set(main.NEW_PER_DAY)


def test_study_step_says_what_is_left():
    study = _item(dayplan.plan(10, ["viagem"], DAY, NOTHING), "study")
    assert study["detail"] == "3 revisões e 5 frases novas"
    assert (study["count"], study["target"], study["done"]) == (0, 8, False)
    one = _item(dayplan.plan(10, ["viagem"], DAY, {**NOTHING, "due_left": 1, "new_left": 0}), "study")
    assert one["detail"] == "1 revisão"


def test_goals_take_turns_day_by_day():
    goals = ["viagem", "series"]
    seen = {dayplan.goal_of_the_day(goals, date.fromordinal(DAY.toordinal() + i)) for i in range(4)}
    assert seen == {"viagem", "series"}
    assert dayplan.goal_of_the_day([], DAY) == "conversar"


def test_journal_and_mine_follow_the_goal():
    result = dayplan.plan(30, ["series"], DAY, NOTHING)
    assert _item(result, "journal")["detail"] == dayplan.JOURNAL_PROMPTS["series"]
    assert "de uma série" in _item(result, "mine")["detail"]
    assert _item(result, "mine")["detail"].startswith("Anote 2 frases")


def test_every_goal_has_texts():
    from app import tracks

    assert set(dayplan.JOURNAL_PROMPTS) == set(tracks.GOALS) == set(dayplan.MINE_SOURCES)


def test_done_when_every_step_is_done():
    progress = {"reviewed": 8, "due_left": 0, "new_left": 0, "speech": 2, "journal": 0, "mined": 0}
    assert dayplan.plan(10, ["viagem"], DAY, progress)["done"] is True
    assert dayplan.plan(15, ["viagem"], DAY, progress)["done"] is False  # falta o diário


# ---------- Na API: os "feitos" automáticos ----------

def _today(client):
    return client.get("/api/today").json()


def test_new_account_plan(client):
    result = _today(client)
    assert _ids(result) == ["study", "speak"]  # 10 min por dia
    assert _item(result, "study")["detail"] == "5 frases novas"
    assert result["done"] is False


def test_studying_checks_the_study_step(client):
    for card in client.get("/api/session").json()["new"]:
        client.post(f"/api/cards/{card['id']}/review", json={"grade": 2})
    study = _item(_today(client), "study")
    assert (study["count"], study["target"], study["done"]) == (5, 5, True)


def test_speaking_checks_the_speak_step(client):
    client.post("/api/speech-checks", json={"words_total": 3, "words_ok": 2})
    assert _item(_today(client), "speak")["count"] == 1
    client.post("/api/speech-checks", json={"words_total": 3, "words_ok": 3})
    client.post("/api/speech-checks", json={"words_total": 3, "words_ok": 3})
    speak = _item(_today(client), "speak")
    assert (speak["count"], speak["done"]) == (2, True)  # não passa da meta


def test_journal_today_checks_the_journal_step(client, database):
    client.patch("/api/me", json={"daily_minutes": 15})
    with psycopg.connect(database) as conn:  # uma entrada de ontem não vale
        conn.execute("INSERT INTO journal (user_id, text, created_at) SELECT id, 'old', now() - interval '2 days' FROM users")
    assert _item(_today(client), "journal")["done"] is False
    client.post("/api/journal", json={"text": "Today I studied."})
    assert _item(_today(client), "journal")["done"] is True


def test_only_your_own_mined_phrases_count(client):
    client.patch("/api/me", json={"daily_minutes": 20})
    assert _item(_today(client), "mine")["count"] == 0
    client.post("/api/cards", json={"front": "Bro is cooking", "back": "O cara tá mandando bem", "source": "live"})
    mine = _item(_today(client), "mine")
    assert (mine["count"], mine["done"]) == (1, True)


def test_plan_is_per_account(new_user):
    ana, bia = new_user("ana@example.com"), new_user("bia@example.com", name="Bia")
    ana.post("/api/speech-checks", json={"words_total": 3, "words_ok": 3})
    ana.post("/api/cards", json={"front": "Segredo da Ana", "back": "x", "source": "live"})
    assert _item(_today(bia), "speak")["count"] == 0
    bia.patch("/api/me", json={"daily_minutes": 20})
    assert _item(_today(bia), "mine")["count"] == 0


def test_plan_needs_login(anon):
    assert anon.get("/api/today").status_code == 401


# ---------- Mais uma rodada ----------

def test_one_more_round_brings_more_new_phrases(client):
    first = client.get("/api/session").json()
    for card in first["new"]:
        client.post(f"/api/cards/{card['id']}/review", json={"grade": 2})
    assert client.get("/api/session").json()["new"] == []
    more = client.get("/api/session?rounds=2").json()
    assert len(more["new"]) == 5 and more["held_back"] is False


@pytest.mark.parametrize("rounds", [0, 11, "x"])
def test_rounds_must_be_reasonable(client, rounds):
    assert client.get(f"/api/session?rounds={rounds}").status_code == 422
