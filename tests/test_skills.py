"""Nível por habilidade: começa no nível escolhido e muda com os acertos e com o volume praticado."""

import psycopg
import pytest

from app import skills, tutor

VOCAB = skills.SKILLS[0]
WRITING = skills.SKILLS[3]


# ---------- A conta ----------

@pytest.mark.parametrize(("level", "band"), [("iniciante", "A1"), ("basico", "A2"), ("intermediario", "B1"), (None, "A1")])
def test_starts_at_the_chosen_level(level, band):
    result = skills.estimate(level, VOCAB, [], 0)
    assert (result["band"], result["start_band"], result["samples"], result["accuracy"]) == (band, band, 0, None)


def test_normal_accuracy_keeps_the_level():
    assert skills.estimate("basico", VOCAB, [0.75] * 100, 0)["value"] == 1.3


def test_accuracy_moves_more_with_more_data():
    few = skills.estimate("basico", VOCAB, [1.0] * 5, 0)["value"]
    many = skills.estimate("basico", VOCAB, [1.0] * 200, 0)["value"]
    assert 1.3 < few < many < 1.3 + skills.MAX_UP


def test_missing_a_lot_goes_down_but_not_below_zero():
    assert skills.estimate("basico", VOCAB, [0.0] * 200, 0)["value"] < 1.3
    assert skills.estimate("iniciante", VOCAB, [0.0] * 200, 0)["value"] == 0.0


def test_volume_grows_up_to_a_limit():
    assert skills.estimate("basico", VOCAB, [], 50)["value"] == 1.8
    assert skills.estimate("basico", VOCAB, [], 10_000)["value"] == 1.3 + skills.MAX_GROWTH


def test_never_goes_past_b2():
    result = skills.estimate("intermediario", VOCAB, [1.0] * 500, 10_000)
    assert (result["band"], result["next_band"]) == ("B2", None)
    assert result["value"] < 4


def test_progress_inside_the_band():
    result = skills.estimate("basico", VOCAB, [], 30)
    assert (result["band"], result["progress"], result["next_band"]) == ("A2", 0.6, "B1")


def test_review_and_writing_scores():
    assert [skills.review_score(g) for g in (0, 1, 2, 3)] == [0.0, 0.5, 1.0, 1.0]
    assert skills.writing_score("I went to the park with my friends yesterday.", 0) == 1.0
    assert skills.writing_score("I go to the park with my friends yesterday ok.", 1) == 0.5
    assert skills.writing_score("I go park", 3) == 0.0


# ---------- Na API ----------

def _skills(client):
    return {s["id"]: s for s in client.get("/api/stats").json()["skills"]}


def test_new_account_shows_the_starting_point(client):
    result = _skills(client)
    assert list(result) == ["vocabulary", "listening", "speaking", "writing"]
    assert all(s["band"] == "A1" and s["samples"] == 0 for s in result.values())  # conta de teste: iniciante


def test_first_review_only_introduces(client):
    card = client.get("/api/session").json()["new"][0]
    client.post(f"/api/cards/{card['id']}/review", json={"grade": 2, "mode": "read"})
    assert _skills(client)["vocabulary"]["samples"] == 0
    client.post(f"/api/cards/{card['id']}/review", json={"grade": 0, "mode": "read"})
    vocab = _skills(client)["vocabulary"]
    assert (vocab["samples"], vocab["accuracy"]) == (1, 0.0)


def test_listen_reviews_measure_listening(client):
    card = client.get("/api/session").json()["new"][0]
    for grade in (2, 2, 1):
        client.post(f"/api/cards/{card['id']}/review", json={"grade": grade, "mode": "listen"})
    result = _skills(client)
    assert (result["listening"]["samples"], result["listening"]["accuracy"]) == (2, 0.75)
    assert result["vocabulary"]["samples"] == 0


def test_speech_checks_measure_speaking(client):
    client.patch("/api/me", json={"level": "basico"})
    for ok in (4, 2):
        client.post("/api/speech-checks", json={"words_total": 4, "words_ok": ok})
    speaking = _skills(client)["speaking"]
    assert (speaking["samples"], speaking["accuracy"], speaking["start_band"]) == (2, 0.75, "A2")


def test_journal_measures_writing(client, monkeypatch):
    fake = tutor.Correction(
        corrected="Yesterday I went to work.",
        natural="I went to work yesterday.",
        mistakes=[tutor.Mistake(original="I go", correction="I went", explanation="passado")],
        encouragement="Boa!",
    )
    monkeypatch.setattr(tutor, "correct_journal", lambda text, learner: fake)
    client.patch("/api/me", json={"level": "basico"})
    client.post("/api/journal", json={"text": "Today I studied a lot."})  # sem correção: só volume
    entry = client.post("/api/journal", json={"text": "Yesterday I go to work by bus with my friend."}).json()
    client.post(f"/api/journal/{entry['id']}/correct")
    writing = _skills(client)["writing"]
    assert (writing["samples"], writing["accuracy"]) == (1, 0.5)
    # Me viro (1.3) + 2 entradas de volume (2/40) - meia nota com 1 correção de peso (1/6 de 0.5)
    assert writing["value"] == 1.27


def test_skills_are_per_account(new_user, database):
    ana, bia = new_user("ana@example.com"), new_user("bia@example.com", name="Bia")
    for _ in range(3):
        ana.post("/api/speech-checks", json={"words_total": 4, "words_ok": 4})
    with psycopg.connect(database) as conn:
        conn.execute("INSERT INTO journal (user_id, text) SELECT id, 'Ana writes' FROM users WHERE email = 'ana@example.com'")
    result = _skills(bia)
    assert result["speaking"]["samples"] == 0 and result["writing"]["value"] == 0
