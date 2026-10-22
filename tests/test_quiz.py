"""Opções de resposta do estudo ativo (as traduções erradas)."""

import random

from app import quiz


def _card(id, back, category="viagem"):
    return {"id": id, "back": back, "category": category}


def test_wrong_options_never_include_the_right_answer():
    card = _card(1, "Estou perdido.")
    pool = [card, _card(2, "estou  perdido"), _card(3, "Estou perdido!"), _card(4, "Siga em frente."),
            _card(5, "É longe daqui?"), _card(6, "Dá pra ir a pé?")]
    options = quiz.distractors(card, pool, random.Random(1))
    assert sorted(options) == ["Dá pra ir a pé?", "Siga em frente.", "É longe daqui?"]


def test_options_are_different_from_each_other():
    card = _card(1, "Oi")
    pool = [card, _card(2, "Tchau"), _card(3, "tchau!"), _card(4, "Valeu"), _card(5, "Até mais")]
    options = quiz.distractors(card, pool, random.Random(1))
    assert len({quiz.answer_key(o) for o in options}) == 3


def test_same_theme_comes_first():
    card = _card(1, "Onde fica o portão 12?")
    pool = [card, _card(2, "Janela ou corredor?"), _card(3, "Aqui está meu passaporte."),
            _card(4, "Esse voo está atrasado?"), _card(5, "Para de mentir, mano.", "streamer"),
            _card(6, "Sem mentira, aquilo foi insano.", "streamer")]
    for seed in range(20):
        assert set(quiz.distractors(card, pool, random.Random(seed))) == {
            "Janela ou corredor?", "Aqui está meu passaporte.", "Esse voo está atrasado?"}


def test_other_themes_fill_the_gap():
    card = _card(1, "Onde fica o portão 12?")
    pool = [card, _card(2, "Janela ou corredor?"), _card(5, "Para de mentir, mano.", "streamer"),
            _card(6, "Sem mentira, aquilo foi insano.", "streamer")]
    options = quiz.distractors(card, pool, random.Random(1))
    assert options[0] == "Janela ou corredor?" and len(options) == 3


def test_similar_length_is_preferred():
    card = _card(1, "Oi.")
    long = [_card(i, "Uma frase bem comprida que entregaria a resposta " + str(i)) for i in range(10, 20)]
    short = [_card(2, "Tchau."), _card(3, "Valeu."), _card(4, "Boa."), _card(5, "Sério?"),
             _card(6, "Fechou."), _card(7, "Bora."), _card(8, "Massa."), _card(9, "Opa.")]
    for seed in range(20):
        options = quiz.distractors(card, [card, *long, *short], random.Random(seed))
        assert all(len(o) < 10 for o in options)


def test_more_shared_words_come_first():
    card = _card(1, "E aí? Nada de mais, e você?", "conversa")
    pool = [card, _card(2, "Tô bem, valeu. E você?", "conversa"), _card(3, "E você?", "conversa"),
            _card(4, "Nada mal.", "conversa")] + [_card(i, f"Frase sem relação {i}", "conversa") for i in range(10, 20)]
    for seed in range(10):
        assert set(quiz.distractors(card, pool, random.Random(seed))) == {"Tô bem, valeu. E você?", "E você?", "Nada mal."}


def test_empty_words_do_not_count_as_shared():
    assert quiz._words("E aí? Nada de mais, e você?") == {"ai", "nada", "mais", "voce"}


def _with_traps(reps):
    return {"id": 1, "back": "E aí? Nada de mais, e você?", "category": "conversa", "reps": reps,
            "traps": ["E aí? Muita coisa, e você?", "E aí? Nada de mais, e ele?"]}


def _pool():
    return [_card(i, f"Outra frase {i}", "conversa") for i in range(2, 12)]


def test_first_round_uses_one_trap():
    for seed in range(10):
        options = quiz.distractors(_with_traps(1), _pool(), random.Random(seed))
        assert len(options) == 3 and sum(o.startswith("E aí?") for o in options) == 1


def test_second_round_uses_both_traps():
    options = quiz.distractors(_with_traps(2), _pool(), random.Random(1))
    assert len(options) == 3
    assert {"E aí? Muita coisa, e você?", "E aí? Nada de mais, e ele?"} <= set(options)


def test_a_trap_equal_to_the_answer_is_skipped():
    card = {**_with_traps(2), "traps": ["e ai nada de mais e voce", "E aí? Nada de mais, e ele?"]}
    options = quiz.distractors(card, _pool(), random.Random(1))
    assert "e ai nada de mais e voce" not in options and len(options) == 3


def test_not_enough_cards_means_no_options():
    cards = [_card(1, "Oi"), _card(2, "Tchau")]
    quiz.add_choices(cards, cards)
    assert cards[0]["choices"] == [] and cards[1]["choices"] == []


# ---------- Na sessão ----------

def test_session_cards_come_with_options(client):
    data = client.get("/api/session?new_limit=6").json()
    for card in data["new"]:
        assert len(card["choices"]) == 3, card
        assert card["back"] not in card["choices"]


def test_session_uses_the_traps_but_does_not_send_them(client, database):
    import psycopg

    with psycopg.connect(database) as conn:
        conn.execute("UPDATE cards SET traps = ARRAY['Pegadinha A', 'Pegadinha B'], introduced_on = '2000-01-01',"
                     " due = '2000-01-02', reps = 2 WHERE front = 'Base I1'")
    card = next(c for c in client.get("/api/session").json()["due"] if c["front"] == "Base I1")
    assert {"Pegadinha A", "Pegadinha B"} <= set(card["choices"])
    assert "traps" not in card


def test_options_come_only_from_your_own_cards(new_user):
    ana, bia = new_user("ana@example.com"), new_user("bia@example.com", name="Bia")
    for i in range(30):  # muitas frases da Ana com o mesmo tema das da Bia
        ana.post("/api/cards", json={"front": f"Ana {i}", "back": f"Segredo {i}", "category": "conversa"})
    choices = [c for card in bia.get("/api/session?new_limit=100").json()["new"] for c in card["choices"]]
    assert choices and not any(c.startswith("Segredo") for c in choices)
