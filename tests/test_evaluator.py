import pytest

from kierki import GameState, InvalidState, RoundType, evaluate_all, evaluate_move
from kierki.cards import RANKS

LOW = RANKS[:9]  # 2..10 - wypełniacze bez figur, żeby nie wprowadzać przypadkowych kart punktowanych


def hand_of(*cards, suits="sd", size=13):
    """Ręka z podanych kart, dopełniona niskimi kartami z kolorów `suits` do `size` kart."""
    hand = list(cards)
    for s in suits:
        for r in LOW:
            if len(hand) >= size:
                return hand
            if f"{r}{s}" not in hand:
                hand.append(f"{r}{s}")
    assert len(hand) == size, "za mało wypełniaczy"
    return hand


def fill_history(n, exclude):
    pool = [f"{r}{s}" for s in "hcsd" for r in RANKS if f"{r}{s}" not in exclude]
    cards = pool[: 4 * n]
    return [cards[i * 4:(i + 1) * 4] for i in range(n)]


def state(hand, rnd, current=(), history=()):
    return GameState(hand=hand, round_type=rnd, current_trick=list(current), history=[list(t) for t in history])


# ---------------------------------------------------------------- poprawność formalna
def test_must_follow_suit():
    st = state(hand_of("9h", "4h", "As"), RoundType.NO_HEARTS, ["3h", "5h", "2h"])
    ev = evaluate_move(st, "As")
    assert not ev.legal and "dołożyć do koloru" in ev.errors[0]


def test_card_not_in_hand():
    st = state(hand_of("9h", "4h", "As"), RoundType.NO_HEARTS, ["3h", "5h", "2h"])
    assert not evaluate_move(st, "2c").legal


def test_inconsistent_hand_size():
    with pytest.raises(InvalidState):
        evaluate_move(GameState(hand=["As"], round_type=RoundType.NO_TRICKS), "As")


def test_duplicate_card():
    st = state(hand_of("9h", "4h", "As"), RoundType.NO_HEARTS, ["9h"])
    with pytest.raises(InvalidState):
        evaluate_move(st, "9h")


def test_single_legal_card_is_forced_move():
    st = state(hand_of("9h"), RoundType.NO_HEARTS, ["3h", "5h", "2h"])
    ev = evaluate_move(st, "9h")
    assert ev.scenario == "only_move" and ev.correctness == 100 and ev.aggressiveness is None


# ---------------------------------------------------------------- wymuszone zebranie lewy
def test_forced_take_prefers_highest_nonpenalty_card():
    st = state(hand_of("9c", "Kc", "Qc"), RoundType.NO_QUEENS, ["3c", "5c", "2c"])
    king, nine, queen = (evaluate_move(st, c) for c in ("Kc", "9c", "Qc"))
    assert king.scenario == "forced_take"
    assert king.correctness == 100 and king.aggressiveness is None
    assert nine.correctness < king.correctness
    assert queen.correctness <= 25 < nine.correctness  # karta punktowana tylko gdy musimy


# ---------------------------------------------------------------- celowe zbieranie lew
def test_deliberate_take_is_aggressive_and_grows_with_progress():
    cur = ["3c", "5c", "2c"]
    early = evaluate_move(state(hand_of("4c", "Kc"), RoundType.NO_HEARTS, cur), "Kc")
    hand_late = hand_of("4c", "Kc", size=5)
    hist = fill_history(8, set(hand_late) | set(cur))
    late = evaluate_move(state(hand_late, RoundType.NO_HEARTS, cur, hist), "Kc")
    duck = evaluate_move(state(hand_of("4c", "Kc"), RoundType.NO_HEARTS, cur), "4c")
    assert early.scenario == "follow_take" and early.correctness == 100
    assert abs(early.aggressiveness - 55.0) < 0.1
    assert late.aggressiveness > early.aggressiveness + 20
    assert duck.aggressiveness < 25


def test_taking_with_penalty_on_table_is_an_error():
    st = state(hand_of("9h", "4h"), RoundType.NO_HEARTS, ["3h", "5h"])
    take, duck = evaluate_move(st, "9h"), evaluate_move(st, "4h")
    assert take.correctness < 20 and duck.correctness > 60
    assert take.aggressiveness > duck.aggressiveness


def test_evaluate_all_sorted_best_first():
    st = state(hand_of("9h", "4h"), RoundType.NO_HEARTS, ["3h", "5h"])
    assert [e.card for e in evaluate_all(st)] == ["4h", "9h"]


# ---------------------------------------------------------------- wychodzenie w kolor
def test_lead_shortest_clean_suit_beats_long_suit():
    st = state(hand_of("2s", "3s", "4c", "5c", "6c", "7c", "8c", suits="d"), RoundType.NO_HEARTS)
    short, long_ = evaluate_move(st, "2s"), evaluate_move(st, "4c")
    assert short.scenario == "lead" and short.correctness > 95
    assert long_.correctness < short.correctness - 15  # długi kolor bez kar w grze "nic nie daje"


def test_lead_from_suit_with_own_penalty_is_incorrect():
    st = state(hand_of("2h", "3h", "4h", "5h", "6h", "2s", "3s", suits="dc"), RoundType.NO_HEARTS)
    assert evaluate_move(st, "2h").correctness < 60 < evaluate_move(st, "2s").correctness


def test_lead_long_suit_when_others_hold_penalty_is_fine():
    # NO_QUEENS: damy innych graczy są w grze, więc długi kolor "zmusza" ich do wzięcia lewy
    st = state(hand_of("2s", "3s", "4c", "5c", "6c", "7c", "8c", suits="d"), RoundType.NO_QUEENS)
    assert evaluate_move(st, "4c").correctness > 85


def test_lead_high_card_where_penalty_unseen_is_error():
    st = state(hand_of("As", "2s", suits="dc"), RoundType.NO_QUEENS)
    ace, two = evaluate_move(st, "As"), evaluate_move(st, "2s")
    assert ace.correctness < 50 and two.correctness > 90
    assert ace.aggressiveness > two.aggressiveness


def test_lead_high_card_when_no_penalty_in_suit_is_correct_and_aggressive():
    st = state(hand_of("As", "2s", suits="dc"), RoundType.NO_KING_OF_HEARTS)
    ace = evaluate_move(st, "As")
    assert ace.correctness > 90 and ace.aggressiveness >= 55


# ---------------------------------------------------------------- brak koloru / zrzuty
def test_void_dumping_penalty_beats_high_then_low_nonpenalty():
    st = state(hand_of("Ah", "2h", "As", "2s", suits="d"), RoundType.NO_HEARTS, ["3c", "5c", "2c"])
    heart, high, low = (evaluate_move(st, c) for c in ("Ah", "As", "2s"))
    assert heart.scenario == "void_discard"
    assert heart.correctness > high.correctness > low.correctness
    assert high.aggressiveness > heart.aggressiveness  # trzymanie kar na ręce = ryzyko


def test_duck_with_penalty_card_is_better_than_low_card():
    st = state(hand_of("Qs", "2s", suits="dc"), RoundType.NO_QUEENS, ["Ks", "3s"])
    queen, two = evaluate_move(st, "Qs"), evaluate_move(st, "2s")
    assert queen.scenario == "follow_duck" and queen.correctness > two.correctness
