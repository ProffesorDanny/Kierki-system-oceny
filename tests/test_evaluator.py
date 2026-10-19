import pytest

from kierki import GameState, InvalidState, RoundType, evaluate_all, evaluate_move

HAND = ["9h", "4h", "As", "Ks", "Qs", "2c", "3c", "4c", "5c", "6c", "7c", "8c", "9c"]


def hearts_state(**kw):
    base = dict(hand=HAND, round_type=RoundType.NO_HEARTS, current_trick=["3h", "5h", "2h"])
    base.update(kw)
    return GameState(**base)


def test_must_follow_suit():
    ev = evaluate_move(hearts_state(), "As")
    assert not ev.legal and "dołożyć do koloru" in ev.errors[0]


def test_card_not_in_hand():
    ev = evaluate_move(hearts_state(), "2d")
    assert not ev.legal


def test_ducking_is_less_aggressive_than_taking_hearts():
    st = hearts_state()
    duck, take = evaluate_move(st, "4h"), evaluate_move(st, "9h")
    assert duck.legal and take.legal
    assert take.components["p_win"] == 1.0
    assert take.aggressiveness > duck.aggressiveness


def test_void_player_may_discard_anything():
    st = GameState(
        hand=["As", "Ks", "Qs", "2c", "3c", "4c", "5c", "6c", "7c", "8c", "9c", "10c", "Jc"],
        round_type=RoundType.NO_HEARTS, current_trick=["3h", "5h", "2h"],
    )
    assert evaluate_move(st, "As").legal


def test_low_lead_safer_than_ace_lead():
    st = GameState(
        hand=["2h", "Ah"] + ["3c", "4c", "5c", "6c", "7c", "8c", "9c", "10c", "Jc", "Qc", "Kc"],
        round_type=RoundType.NO_HEARTS,
    )
    assert evaluate_move(st, "Ah").aggressiveness > evaluate_move(st, "2h").aggressiveness


def test_dumping_king_of_hearts_is_pure_attack():
    st = GameState(
        hand=["Kh", "2s", "3s", "4s", "5s", "6s", "7s", "8s", "9s", "10s", "Js", "Qs", "Ks"],
        round_type=RoundType.NO_KING_OF_HEARTS, current_trick=["Ac", "2c"],
    )
    ev = evaluate_move(st, "Kh")
    assert ev.legal and ev.components["exposure"] == 0 and ev.components["attack"] == 1.0


def test_evaluate_all_sorted():
    res = evaluate_all(hearts_state())
    assert [e.card for e in res] == ["4h", "9h"]


def test_inconsistent_hand_size():
    with pytest.raises(InvalidState):
        evaluate_move(GameState(hand=["As"], round_type=RoundType.NO_TRICKS), "As")


def test_duplicate_card():
    with pytest.raises(InvalidState):
        evaluate_move(hearts_state(current_trick=["9h"]), "9h")
