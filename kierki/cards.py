"""Karty: parsowanie zapisu typu "Qs", "10h", "Ad", "2c"."""
from __future__ import annotations

import re
from dataclasses import dataclass

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["s", "h", "d", "c"]  # spades, hearts, diamonds, clubs
_RANK_VALUE = {r: i + 2 for i, r in enumerate(RANKS)}
_CARD_RE = re.compile(r"^(10|[2-9]|[JQKATjqkat])([shdcSHDC])$")


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        return _RANK_VALUE[self.rank]

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


def parse_card(text: str) -> Card:
    m = _CARD_RE.match(text.strip())
    if not m:
        raise ValueError(f"Nieprawidłowa karta: {text!r} (oczekiwano np. 'Qs', '10h', 'Ad')")
    rank, suit = m.groups()
    rank = rank.upper()
    if rank == "T":
        rank = "10"
    return Card(rank, suit.lower())


def full_deck() -> list[Card]:
    return [Card(r, s) for s in SUITS for r in RANKS]
