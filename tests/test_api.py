def test_new_limit_overrides_the_daily_plan(client):
    data = client.get("/api/session?new_limit=5").json()
    assert data["due"] == []
    assert len(data["new"]) == 5
    assert data["new_per_day"] == 5 and data["held_back"] is False


def test_review_moves_card_out_of_today(client):
    card = client.get("/api/session?new_limit=1").json()["new"][0]
    res = client.post(f"/api/cards/{card['id']}/review", json={"grade": 2})
    assert res.status_code == 200
    assert res.json()["interval_days"] == 1

    session = client.get("/api/session?new_limit=1").json()
    assert session["new"] == []  # limite diário de novos já usado
    assert card["id"] not in [c["id"] for c in session["due"]]
    assert client.get("/api/stats").json()["reviews_today"] == 1


def test_again_keeps_card_due_today(client):
    card = client.get("/api/session?new_limit=1").json()["new"][0]
    client.post(f"/api/cards/{card['id']}/review", json={"grade": 0})
    due_ids = [c["id"] for c in client.get("/api/session").json()["due"]]
    assert card["id"] in due_ids


def test_create_duplicate_and_delete(client):
    body = {"front": "That's tuff", "back": "Isso é muito bom", "category": "streamer"}
    created = client.post("/api/cards", json=body)
    assert created.status_code == 201
    assert client.post("/api/cards", json=body).status_code == 409
    assert client.delete(f"/api/cards/{created.json()['id']}").status_code == 204
    assert client.delete(f"/api/cards/{created.json()['id']}").status_code == 404


def test_invalid_grade_rejected(client):
    card = client.get("/api/session?new_limit=1").json()["new"][0]
    assert client.post(f"/api/cards/{card['id']}/review", json={"grade": 9}).status_code == 422


def test_journal(client):
    assert client.post("/api/journal", json={"text": "Today I studied English."}).status_code == 201
    assert client.get("/api/journal").json()[0]["text"] == "Today I studied English."


def test_correct_journal_creates_mistake_cards(client, monkeypatch):
    from app import tutor

    fake = tutor.Correction(
        corrected="Yesterday I went to work.",
        natural="Went to work yesterday.",
        mistakes=[tutor.Mistake(original="I go yesterday", correction="I went yesterday", explanation="Passado de go é went.")],
        encouragement="Boa!",
    )
    monkeypatch.setattr(tutor, "correct_journal", lambda text, learner: fake)

    entry = client.post("/api/journal", json={"text": "Yesterday I go to work."}).json()
    res = client.post(f"/api/journal/{entry['id']}/correct")
    assert res.status_code == 200
    assert res.json()["cards_created"] == 1

    cards = client.get("/api/cards?category=meus-erros").json()
    assert [c["front"] for c in cards] == ["I went yesterday"]
    assert client.get("/api/journal").json()[0]["correction"]["corrected"] == "Yesterday I went to work."

    # corrigir de novo é recusado: só gastaria a IA
    assert client.post(f"/api/journal/{entry['id']}/correct").status_code == 409


def test_correct_journal_without_key(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    entry = client.post("/api/journal", json={"text": "Hello"}).json()
    res = client.post(f"/api/journal/{entry['id']}/correct")
    assert res.status_code == 503
    assert res.json()["detail"] == "A correção por IA não está disponível agora. Tente mais tarde."  # sem detalhe técnico


def test_tutor_drops_non_mistakes(monkeypatch):
    from types import SimpleNamespace

    from app import tutor

    parsed = tutor.Correction(
        corrected="x", natural="x", encouragement="x",
        mistakes=[
            tutor.Mistake(original="I go", correction="I went", explanation="passado"),
            tutor.Mistake(original="to finish the feature", correction="To finish the feature.", explanation="ok"),
        ],
    )
    fake_client = SimpleNamespace(messages=SimpleNamespace(
        parse=lambda **kw: SimpleNamespace(stop_reason="end_turn", parsed_output=parsed)
    ))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(tutor, "_get_client", lambda: fake_client)

    result = tutor.correct_journal("I go to finish the feature")
    assert [m.original for m in result.mistakes] == ["I go"]


def test_personal_cards_come_before_seed_deck(client, monkeypatch):
    from app import tutor

    client.post("/api/cards", json={"front": "Bro is not him", "back": "O cara não é tudo isso", "source": "live"})
    fake = tutor.Correction(
        corrected="x", natural="x", encouragement="x",
        mistakes=[tutor.Mistake(original="I go", correction="I went", explanation="passado")],
    )
    monkeypatch.setattr(tutor, "correct_journal", lambda text, learner: fake)
    entry = client.post("/api/journal", json={"text": "Yesterday I go."}).json()
    client.post(f"/api/journal/{entry['id']}/correct")

    fronts = [c["front"] for c in client.get("/api/session?new_limit=3").json()["new"]]
    assert fronts[:2] == ["I went", "Bro is not him"]
    assert fronts[2] == "Base I1"  # depois vêm as trilhas
