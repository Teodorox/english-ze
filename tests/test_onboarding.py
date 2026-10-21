"""Primeiro acesso: objetivos, nível e tempo por dia."""

import psycopg
import pytest

ANSWERS = {"goals": ["streamers", "musica"], "level": "basico", "daily_minutes": 10}


def test_new_account_starts_without_onboarding(client):
    me = client.get("/api/me").json()
    assert me["onboarded"] is False
    assert me["goals"] == [] and me["level"] is None and me["daily_minutes"] == 10


def test_complete_onboarding(client):
    res = client.post("/api/me/onboarding", json=ANSWERS)
    assert res.status_code == 200, res.text
    me = res.json()
    assert me["onboarded"] is True
    assert me["goals"] == ["streamers", "musica"] and me["level"] == "basico" and me["daily_minutes"] == 10
    assert client.get("/api/me").json() == me  # ficou salvo


@pytest.mark.parametrize("minutes", [5, 10, 15, 20, 30])
def test_every_daily_time_option_is_accepted(client, minutes):
    res = client.post("/api/me/onboarding", json={**ANSWERS, "daily_minutes": minutes})
    assert res.status_code == 200, res.text
    assert res.json()["daily_minutes"] == minutes


def test_repeated_goals_count_once(client):
    body = {**ANSWERS, "goals": ["viagem", "viagem", "provas"]}
    assert client.post("/api/me/onboarding", json=body).json()["goals"] == ["viagem", "provas"]


@pytest.mark.parametrize(
    "change",
    [
        {"goals": []},                                   # pelo menos um objetivo
        {"goals": ["hackear"]},                          # fora da lista
        {"goals": ["musica'); DROP TABLE users; --"]},   # nada vira SQL
        {"goals": "musica"},                             # tem que ser lista
        {"goals": ["musica"] * 8},                       # lista grande demais
        {"level": "fluente"},
        {"level": None},
        {"daily_minutes": 7},
        {"daily_minutes": 25},
        {"daily_minutes": 45},
        {"daily_minutes": "10"},
        {"daily_minutes": 10_000},
    ],
)
def test_onboarding_rejects_invalid_answers(client, change):
    res = client.post("/api/me/onboarding", json={**ANSWERS, **change})
    assert res.status_code == 422, (change, res.text)
    assert client.get("/api/me").json()["onboarded"] is False


def test_onboarding_needs_every_answer(client):
    for missing in ANSWERS:
        body = {k: v for k, v in ANSWERS.items() if k != missing}
        assert client.post("/api/me/onboarding", json=body).status_code == 422, missing


def test_settings_change_study_profile(client):
    client.post("/api/me/onboarding", json=ANSWERS)
    res = client.patch("/api/me", json={"goals": ["trabalho"], "level": "intermediario", "daily_minutes": 15})
    assert res.status_code == 200, res.text
    me = res.json()
    assert me["goals"] == ["trabalho"] and me["level"] == "intermediario" and me["daily_minutes"] == 15
    assert client.patch("/api/me", json={"daily_minutes": 3}).status_code == 422
    assert client.patch("/api/me", json={"goals": []}).status_code == 422
    assert client.get("/api/me").json()["daily_minutes"] == 15


def test_onboarding_date_is_kept(client, database):
    client.post("/api/me/onboarding", json=ANSWERS)
    with psycopg.connect(database) as conn:
        first = conn.execute("SELECT onboarded_at FROM users").fetchone()[0]
    client.post("/api/me/onboarding", json={**ANSWERS, "level": "iniciante"})
    with psycopg.connect(database) as conn:
        again = conn.execute("SELECT onboarded_at FROM users").fetchone()[0]
    assert first is not None and again == first


def test_onboarding_is_per_account(new_user):
    ana, bia = new_user("ana@example.com"), new_user("bia@example.com", name="Bia")
    ana.post("/api/me/onboarding", json=ANSWERS)
    assert bia.get("/api/me").json()["onboarded"] is False
    assert bia.get("/api/me").json()["goals"] == []


def test_database_rejects_values_outside_the_lists(database, client):
    """Mesmo se a validação da API falhar um dia, o banco recusa."""
    with psycopg.connect(database) as conn:
        for query in (
            "UPDATE users SET goals = ARRAY['hackear']",
            "UPDATE users SET level = 'fluente'",
            "UPDATE users SET daily_minutes = 7",
            "UPDATE users SET daily_minutes = 45",
        ):
            with pytest.raises(psycopg.errors.CheckViolation):
                conn.execute(query)
            conn.rollback()
