"""Prática de fala guardada no servidor e modo (Ler/Ouvir) de cada revisão."""

import psycopg
import pytest

from app import main


def _first_card(client):
    return client.get("/api/cards").json()[0]


def _modes(database):
    with psycopg.connect(database) as conn:
        return [r[0] for r in conn.execute("SELECT mode FROM reviews ORDER BY id")]


def test_review_keeps_the_study_mode(client, database):
    card = client.get("/api/session?new_limit=3").json()["new"]
    assert client.post(f"/api/cards/{card[0]['id']}/review", json={"grade": 2, "mode": "read"}).status_code == 200
    assert client.post(f"/api/cards/{card[1]['id']}/review", json={"grade": 2, "mode": "listen"}).status_code == 200
    assert client.post(f"/api/cards/{card[2]['id']}/review", json={"grade": 2}).status_code == 200  # app antigo
    assert _modes(database) == ["read", "listen", None]


@pytest.mark.parametrize("mode", ["write", "LISTEN", "", "read'; DROP TABLE reviews; --", 1])
def test_review_rejects_unknown_mode(client, database, mode):
    card = _first_card(client)
    assert client.post(f"/api/cards/{card['id']}/review", json={"grade": 2, "mode": mode}).status_code == 422
    assert _modes(database) == []


def test_save_speech_check(client):
    res = client.post("/api/speech-checks", json={"words_total": 4, "words_ok": 3})
    assert res.status_code == 201, res.text
    assert res.json()["score"] == 75
    assert client.get("/api/stats").json()["speech_checks_today"] == 1


@pytest.mark.parametrize(("ok", "total", "score"), [(0, 3, 0), (1, 3, 33), (2, 3, 67), (5, 5, 100), (1, 8, 13)])
def test_score_comes_from_the_words(client, ok, total, score):
    """A nota é a mesma conta do app (Math.round), feita pelo banco."""
    assert client.post("/api/speech-checks", json={"words_total": total, "words_ok": ok}).json()["score"] == score


def test_speech_check_can_point_to_a_card(client, database):
    card = _first_card(client)
    assert client.post("/api/speech-checks", json={"words_total": 2, "words_ok": 2, "card_id": card["id"]}).status_code == 201
    # apagar o card não apaga a prática: ela só perde o vínculo
    client.delete(f"/api/cards/{card['id']}")
    with psycopg.connect(database) as conn:
        assert conn.execute("SELECT card_id, score FROM speech_checks").fetchall() == [(None, 100)]


@pytest.mark.parametrize(
    "body",
    [
        {"words_total": 3, "words_ok": 4},           # mais certas que o total
        {"words_total": 0, "words_ok": 0},
        {"words_total": 501, "words_ok": 1},
        {"words_total": 3, "words_ok": -1},
        {"words_total": "3", "words_ok": 1},
        {"words_total": 3},
        {"words_total": 3, "words_ok": 1, "card_id": 0},
        {"words_total": 3, "words_ok": 1, "card_id": 2**31},
        {"words_total": 3, "words_ok": 1, "score": 100},  # a nota não vem do app
    ],
)
def test_speech_check_rejects_invalid_numbers(client, database, body):
    res = client.post("/api/speech-checks", json=body)
    if "score" in body:  # campo extra é ignorado: quem manda na nota é o banco
        assert res.json()["score"] == 33
        return
    assert res.status_code == 422, (body, res.text)
    with psycopg.connect(database) as conn:
        assert conn.execute("SELECT COUNT(*) FROM speech_checks").fetchone()[0] == 0


def test_speech_check_needs_login(anon):
    assert anon.post("/api/speech-checks", json={"words_total": 1, "words_ok": 1}).status_code == 401


def test_speech_checks_are_per_account(new_user, database):
    ana, bia = new_user("ana@example.com"), new_user("bia@example.com", name="Bia")
    ana_card = _first_card(ana)
    # Bia não consegue ligar a prática dela a um card da Ana
    res = bia.post("/api/speech-checks", json={"words_total": 2, "words_ok": 1, "card_id": ana_card["id"]})
    assert res.status_code == 404
    ana.post("/api/speech-checks", json={"words_total": 2, "words_ok": 1})
    assert ana.get("/api/stats").json()["speech_checks_today"] == 1
    assert bia.get("/api/stats").json()["speech_checks_today"] == 0


def test_daily_limit(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_SPEECH_CHECKS_PER_DAY", 2)
    body = {"words_total": 2, "words_ok": 2}
    assert client.post("/api/speech-checks", json=body).status_code == 201
    assert client.post("/api/speech-checks", json=body).status_code == 201
    assert client.post("/api/speech-checks", json=body).status_code == 429
    assert client.get("/api/stats").json()["speech_checks_today"] == 2


def test_database_rejects_inconsistent_checks(client, database):
    """Mesmo se a validação da API falhar um dia, o banco recusa."""
    with psycopg.connect(database) as conn:
        user_id = conn.execute("SELECT id FROM users").fetchone()[0]
        for values in ((3, 4), (0, 0), (501, 1)):
            with pytest.raises(psycopg.errors.CheckViolation):
                conn.execute(
                    "INSERT INTO speech_checks (user_id, words_total, words_ok, checked_on) VALUES (%s, %s, %s, now())",
                    (user_id, *values),
                )
            conn.rollback()
        with pytest.raises(psycopg.errors.GeneratedAlways):
            conn.execute(
                "INSERT INTO speech_checks (user_id, words_total, words_ok, score, checked_on) VALUES (%s, 2, 1, 100, now())",
                (user_id,),
            )
        conn.rollback()
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("INSERT INTO reviews (card_id, grade, mode, reviewed_on) SELECT id, 2, 'write', now() FROM cards LIMIT 1")
