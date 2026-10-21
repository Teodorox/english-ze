"""O mais importante das contas: ninguém vê nem mexe nos dados de outra pessoa, nem adivinhando ids."""

import pytest


@pytest.fixture
def ana_and_bia(new_user):
    ana = new_user("ana@example.com", "Ana")
    bia = new_user("bia@example.com", "Bia")
    return ana, bia


def test_each_account_sees_only_its_own_data(ana_and_bia):
    ana, bia = ana_and_bia
    card = ana.get("/api/session?new_limit=1").json()["new"][0]
    ana.post(f"/api/cards/{card['id']}/review", json={"grade": 2})
    ana.post("/api/cards", json={"front": "Bro is cooking", "back": "O cara tá mandando bem", "category": "live"})
    ana.post("/api/journal", json={"text": "Segredo da Ana"})

    assert "Bro is cooking" not in [c["front"] for c in bia.get("/api/cards?q=cooking").json()]
    assert "live" not in bia.get("/api/categories").json()
    assert bia.get("/api/journal").json() == []
    assert bia.get("/api/stats").json()["reviews_today"] == 0
    assert ana.get("/api/stats").json()["reviews_today"] == 1
    # O mesmo card do deck inicial existe nas duas contas, cada um com o seu progresso
    assert card["front"] in [c["front"] for c in bia.get("/api/session?new_limit=100").json()["new"]]


def test_cannot_touch_other_accounts_cards_by_id(ana_and_bia, monkeypatch):
    from app import tutor

    ana, bia = ana_and_bia
    card = ana.post("/api/cards", json={"front": "Mine", "back": "Meu"}).json()
    entry = ana.post("/api/journal", json={"text": "I go yesterday"}).json()
    monkeypatch.setattr(tutor, "correct_journal", lambda text, learner: pytest.fail("não podia chamar a IA"))

    assert bia.post(f"/api/cards/{card['id']}/review", json={"grade": 3}).status_code == 404
    assert bia.delete(f"/api/cards/{card['id']}").status_code == 404
    assert bia.post(f"/api/journal/{entry['id']}/correct").status_code == 404

    # Nada mudou pra Ana
    mine = [c for c in ana.get("/api/cards").json() if c["id"] == card["id"]][0]
    assert (mine["reps"], mine["introduced_on"]) == (0, None)


def test_same_card_text_in_two_accounts(ana_and_bia):
    ana, bia = ana_and_bia
    body = {"front": "That's tuff", "back": "Isso é muito bom"}
    assert ana.post("/api/cards", json=body).status_code == 201
    assert bia.post("/api/cards", json=body).status_code == 201  # o "já existe" é por conta
    assert ana.post("/api/cards", json=body).status_code == 409


def test_ai_uses_each_persons_description(ana_and_bia, monkeypatch):
    from app import tutor

    ana, bia = ana_and_bia
    ana.patch("/api/me", json={"learner": "Professora, inglês fluente"})
    seen = []
    fake = tutor.Correction(corrected="x", natural="x", mistakes=[], encouragement="x")
    monkeypatch.setattr(tutor, "correct_journal", lambda text, learner: seen.append(learner) or fake)

    for person in (ana, bia):
        entry = person.post("/api/journal", json={"text": "Hi"}).json()
        person.post(f"/api/journal/{entry['id']}/correct")
    assert seen == ["Professora, inglês fluente", ""]


def test_today_follows_each_persons_timezone(ana_and_bia):
    ana, bia = ana_and_bia
    # Kiritimati (UTC+14) e Honolulu (UTC-10) estão sempre em dias diferentes
    ana.patch("/api/me", json={"timezone": "Pacific/Kiritimati"})
    bia.patch("/api/me", json={"timezone": "Pacific/Honolulu"})
    for person in (ana, bia):
        card = person.get("/api/session?new_limit=1").json()["new"][0]
        person.post(f"/api/cards/{card['id']}/review", json={"grade": 2})
    ana_day = ana.get("/api/stats").json()["history"][-1]["day"]
    bia_day = bia.get("/api/stats").json()["history"][-1]["day"]
    assert ana_day > bia_day
