"""Ocena posunięć w kierkach: poprawność + agresywność (0-100).

Model agresywności (wszystkie składowe w zakresie 0..1):

* exposure  - ryzyko wzięcia lewy z karą: P(wezmę lewę) * oczekiwana kara w lewie
              / maksymalna kara możliwa w jednej lewie w tej rundzie
* excess    - o ile ten ruch jest bardziej ryzykowny niż najbezpieczniejszy
              legalny ruch w tej samej sytuacji (exposure - min exposure)
* attack    - zrzucenie karnej karty na gracza, który aktualnie bierze lewę

aggressiveness = 100 * (w_exposure*exposure + w_excess*excess + w_attack*attack)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .cards import Card, full_deck, parse_card
from .rounds import TOTAL_TRICKS, RoundType, get_rules

N_PLAYERS = 4


class InvalidState(ValueError):
    """Niespójne dane wejściowe (to nie jest błąd ruchu gracza)."""


@dataclass
class Weights:
    exposure: float = 0.4
    excess: float = 0.4
    attack: float = 0.2


@dataclass
class Settings:
    # Szansa, że przeciwnik, który MOŻE przebić moją kartę, faktycznie to zrobi.
    overtake_rate: float = 0.7
    weights: Weights = field(default_factory=Weights)


@dataclass
class GameState:
    hand: list[str]                      # ręka gracza PRZED zagraniem (z kartą do oceny)
    round_type: RoundType
    history: list[list[str]] = field(default_factory=list)       # zakończone lewy, w kolejności kładzenia
    current_trick: list[str] = field(default_factory=list)       # karty już leżące w bieżącej lewie


@dataclass
class MoveEvaluation:
    card: str
    legal: bool
    errors: list[str]
    aggressiveness: float | None = None
    label: str | None = None
    components: dict[str, float] = field(default_factory=dict)


@dataclass
class _Ctx:
    hand: list[Card]
    current: list[Card]
    unseen: list[Card]
    rules: object
    trick_number: int
    n_remaining: int          # ilu graczy zagra PO mnie w tej lewie
    mean_unseen_pen: float
    ref_penalty: float        # maks. kara możliwa w jednej lewie (normalizacja)
    max_card_pen: float


def _prepare(state: GameState) -> _Ctx:
    try:
        hand = [parse_card(c) for c in state.hand]
        history = [[parse_card(c) for c in t] for t in state.history]
        current = [parse_card(c) for c in state.current_trick]
    except ValueError as e:
        raise InvalidState(str(e)) from e

    if any(len(t) != N_PLAYERS for t in history):
        raise InvalidState("Każda zakończona lewa musi mieć 4 karty.")
    if len(current) >= N_PLAYERS:
        raise InvalidState("Bieżąca lewa ma już komplet kart.")
    if len(history) >= TOTAL_TRICKS:
        raise InvalidState("Runda ma tylko 13 lew.")
    known = hand + [c for t in history for c in t] + current
    if len(set(known)) != len(known):
        raise InvalidState("Ta sama karta występuje więcej niż raz.")
    if len(hand) != TOTAL_TRICKS - len(history):
        raise InvalidState(
            f"Po {len(history)} lewach na ręce powinno być {TOTAL_TRICKS - len(history)} kart, "
            f"jest {len(hand)}."
        )

    rules = get_rules(state.round_type)
    unseen = [c for c in full_deck() if c not in set(known)]
    played = {c for t in history for c in t}
    remaining = [c for c in full_deck() if c not in played]  # karty jeszcze nie rozegrane w lewach
    pens = sorted((rules.card_penalty(c) for c in remaining), reverse=True)
    trick_number = len(history) + 1
    ref = rules.trick_penalty(trick_number) + sum(pens[:N_PLAYERS])
    mean_unseen = (sum(rules.card_penalty(c) for c in unseen) / len(unseen)) if unseen else 0.0
    return _Ctx(
        hand=hand, current=current, unseen=unseen, rules=rules,
        trick_number=trick_number,
        n_remaining=N_PLAYERS - len(current) - 1,
        mean_unseen_pen=mean_unseen,
        ref_penalty=float(ref),
        max_card_pen=float(pens[0]) if pens else 0.0,
    )


def _legal_cards(ctx: _Ctx) -> list[Card]:
    if not ctx.current:
        return list(ctx.hand)
    lead = ctx.current[0].suit
    same = [c for c in ctx.hand if c.suit == lead]
    return same or list(ctx.hand)


def _beats_current(ctx: _Ctx, card: Card) -> bool:
    """Czy karta bije (lub otwiera) aktualnie prowadzącą kartę w lewie."""
    if not ctx.current:
        return True
    lead = ctx.current[0].suit
    if card.suit != lead:
        return False
    best = max(c.value for c in ctx.current if c.suit == lead)
    return card.value > best


def _p_win(ctx: _Ctx, card: Card, s: Settings) -> float:
    if not _beats_current(ctx, card):
        return 0.0
    if ctx.n_remaining == 0:
        return 1.0
    k = sum(1 for c in ctx.unseen if c.suit == card.suit and c.value > card.value)
    if k == 0:
        return 1.0
    u = len(ctx.unseen)
    m = min(ctx.n_remaining * len(ctx.hand), u)
    # P(żaden z graczy po mnie nie ma wyższej karty do koloru) - losowe rozdanie bez wiedzy o renonsach
    p_none = math.comb(u - k, m) / math.comb(u, m) if u - k >= m else 0.0
    return p_none + (1.0 - p_none) * (1.0 - s.overtake_rate)


def _exposure(ctx: _Ctx, card: Card, s: Settings) -> tuple[float, float, float]:
    """Zwraca (exposure, p_win, oczekiwana kara w lewie)."""
    p = _p_win(ctx, card, s)
    pen_now = ctx.rules.trick_penalty(ctx.trick_number) + sum(
        ctx.rules.card_penalty(c) for c in ctx.current + [card]
    )
    expected = pen_now + ctx.n_remaining * ctx.mean_unseen_pen
    if ctx.ref_penalty <= 0:
        return 0.0, p, expected
    return min(1.0, p * expected / ctx.ref_penalty), p, expected


def _attack(ctx: _Ctx, card: Card) -> float:
    if not ctx.current or ctx.max_card_pen <= 0 or _beats_current(ctx, card):
        return 0.0
    return ctx.rules.card_penalty(card) / ctx.max_card_pen


def label_for(score: float) -> str:
    if score < 15:
        return "bardzo defensywny"
    if score < 35:
        return "defensywny"
    if score < 60:
        return "wyważony"
    if score < 80:
        return "agresywny"
    return "bardzo agresywny"


def evaluate_move(state: GameState, card: str, settings: Settings | None = None) -> MoveEvaluation:
    s = settings or Settings()
    ctx = _prepare(state)
    try:
        c = parse_card(card)
    except ValueError as e:
        return MoveEvaluation(card, False, [str(e)])

    errors: list[str] = []
    if c not in ctx.hand:
        errors.append(f"Karty {c} nie ma na ręce gracza.")
    elif c not in _legal_cards(ctx):
        errors.append(f"Trzeba dołożyć do koloru '{ctx.current[0].suit}' - gracz ma taką kartę.")
    if errors:
        return MoveEvaluation(str(c), False, errors)

    exposures = {x: _exposure(ctx, x, s)[0] for x in _legal_cards(ctx)}
    exposure, p, expected = _exposure(ctx, c, s)
    excess = exposure - min(exposures.values())
    attack = _attack(ctx, c)
    w = s.weights
    score = 100.0 * min(1.0, max(0.0, w.exposure * exposure + w.excess * excess + w.attack * attack))
    return MoveEvaluation(
        card=str(c), legal=True, errors=[],
        aggressiveness=round(score, 1), label=label_for(score),
        components={
            "p_win": round(p, 3),
            "expected_trick_penalty": round(expected, 1),
            "exposure": round(exposure, 3),
            "excess": round(excess, 3),
            "attack": round(attack, 3),
        },
    )


def evaluate_all(state: GameState, settings: Settings | None = None) -> list[MoveEvaluation]:
    """Ocena wszystkich legalnych ruchów, od najbardziej defensywnego."""
    ctx = _prepare(state)
    res = [evaluate_move(state, str(c), settings) for c in _legal_cards(ctx)]
    return sorted(res, key=lambda e: e.aggressiveness)
