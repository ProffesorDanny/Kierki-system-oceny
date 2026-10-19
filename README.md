# Kierki-system-oceny

Algorytmiczna ocena posunięć w kierkach (4 graczy, 13 lew): **poprawność** (zasady) oraz **agresywność** (0–100).

## Użycie

```python
from kierki import GameState, RoundType, evaluate_move, evaluate_all

state = GameState(
    hand=["9h", "4h", "As", "Ks", "Qs", "2c", "3c", "4c", "5c", "6c", "7c", "8c", "9c"],
    round_type=RoundType.NO_HEARTS,
    history=[],                         # zakończone lewy, każda 4 karty w kolejności kładzenia
    current_trick=["3h", "5h", "2h"],   # karty już leżące w bieżącej lewie
)
evaluate_move(state, "9h")   # ocena jednego ruchu
evaluate_all(state)          # wszystkie legalne ruchy od najbardziej defensywnego
```

CLI: `python -m kierki plik.json` (lub JSON ze stdin) – format opisany w `kierki/__main__.py`.

Zapis kart: `<ranga><kolor>`, ranga: `2–10, J, Q, K, A`, kolor: `s` (pik), `h` (kier), `d` (karo), `c` (trefl).
`hand` to ręka **przed** zagraniem (razem z oceniana kartą).

Rundy (`RoundType`): `no_tricks`, `no_hearts`, `no_queens`, `no_kings_jacks`, `no_king_of_hearts`, `no_seventh_last`, `robber`.
Wartości kar są w `kierki/rounds.py` – to tylko założenia startowe, zmień na swoje.

## Model oceny

**Poprawność** – karta musi być na ręce i trzeba dokładać do koloru, jeśli się go ma. Niespójne dane (zła liczba kart, duplikaty) zgłaszają `InvalidState`.

**Agresywność** = `100 · (0.4·exposure + 0.4·excess + 0.2·attack)` (wagi w `Weights`):

| składowa | znaczenie |
|---|---|
| `exposure` | P(wezmę lewę) × oczekiwana kara w lewie / maks. kara w jednej lewie |
| `excess` | o ile ruch jest ryzykowniejszy od najbezpieczniejszego legalnego ruchu |
| `attack` | zrzut karnej karty na gracza, który aktualnie bierze lewę |

P(wezmę lewę) liczone jest dokładnie (hipergeometrycznie) z kart niewidzianych i liczby graczy po mnie, z parametrem `overtake_rate` (szansa, że przeciwnik, który może przebić, faktycznie to zrobi).

## Znane uproszczenia (do rozbudowy)

- brak śledzenia renonsów przeciwników (nie wiadomo, kto kogo prowadził w historii),
- brak oceny długofalowej (np. czy ruch zostawia na ręce niebezpieczne karty),
- punkty karne i wagi są wartościami domyślnymi.

## Testy

`pytest` (testy w `tests/test_evaluator.py`).
