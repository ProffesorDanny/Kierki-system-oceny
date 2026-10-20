# Kierki-system-oceny

Algorytmiczna ocena posunięć w kierkach (4 graczy, 13 lew). Każdy ruch dostaje dwie niezależne oceny:

- **poprawność** 0–100 (+ werdykt: optymalne ≥90, poprawne ≥70, wątpliwe ≥40, niepoprawne),
- **agresywność** 0–100 (+ etykieta) albo `None` („neutralne”), gdy ruch jest wymuszony,

oraz listę `reasons` – które reguły zadziałały.

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
evaluate_all(state)          # wszystkie legalne ruchy, od najlepszego
```

CLI: `python -m kierki plik.json` (lub JSON ze stdin) – format w `kierki/__main__.py`.

Zapis kart: `<ranga><kolor>`, ranga `2–10, J, Q, K, A`, kolor `s` (pik), `h` (kier), `d` (karo), `c` (trefl).
`hand` to ręka **przed** zagraniem (razem z ocenianą kartą). Rundy (`RoundType`): `no_tricks`, `no_hearts`,
`no_queens`, `no_kings_jacks`, `no_king_of_hearts`, `no_seventh_last`, `robber` – kary w `kierki/rounds.py`.

## Reguły (jak Twoje zasady przekładają się na kod)

Scenariusz wybiera `strategy.score_move`; wszystkie liczby są w `kierki/params.py` (`Params`).

| Twoja reguła | Scenariusz | Poprawność | Agresywność |
|---|---|---|---|
| Na pewno zbiorę lewę → najwyżej niepunktowaną; punktowaną tylko gdy muszę | `forced_take` (każda legalna karta na pewno bierze) | najwyższa niepunktowana = 100, niższe tracą do `forced_rank_loss`, karta punktowa ≤ `forced_penalty_card_cap` | `None` – nie oceniamy |
| Celowe zbieranie lew bez kar: agresywne, najwyższą niepunktowaną, im później tym bardziej | `follow_take` | 100 · (1 − ryzyko), minus `take_not_highest_loss` za niższą niż najwyższa niepunktowana | `p_win · (take_aggr_base + take_aggr_progress · postęp)` + ryzyko |
| Zbieranie pewnych kar (karta karna na stole / karana lewa), choć mogłem dołożyć kartę, która nie bierze | `follow_take` | najwyżej 100 − p_win · (100 − `take_known_penalty_cap`) | j.w. |
| Wyjście w najkrótszym kolorze bez własnych kar | `lead` | bez straty | rośnie z ryzykiem, że komuś skończy się kolor (`void_aggr · P(renons)`) |
| Wyjście ostatnią kartą koloru (pozbywam się koloru) | `lead` | ryzyko zrzutu kar od gracza bez koloru liczy się o `lead_last_card_relief` słabiej | j.w. |
| Wysokie karty z niego: agresywne i poprawne, chyba że kary tego koloru jeszcze nie zagrane | `lead` | ryzyko = P(wezmę) · (kary na stole + oczekiwane zrzuty kar tego koloru) | j.w. + `risk_aggr · ryzyko` |
| Długi kolor z moimi karami punktowanymi: niepoprawne | `lead` | −`lead_own_penalty_loss` (o ile istnieje kolor bez moich kar) | j.w. |
| Długi kolor, kary mają inni: poprawne, agresywniej im więcej koloru zagrano | `lead` | −`lead_long_suit_loss` | rośnie z `P(renons)` |
| Długi kolor bez żadnych kar w grze | `lead` | −`lead_no_danger_loss` („nic nie daje”) – moje rozszerzenie | j.w. |
| Brak koloru: zrzut kar bardzo poprawny | `void_discard` / `follow_duck` | najwyższa kara = 100, mniejsze tracą `dump_order_loss` | `dump_pen_aggr` (niska) |
| Brak koloru: wysokie niepunktowane też można, ale agresywniej; dobre, gdy ktoś ma dużo koloru | `void_discard` / `follow_duck` | −`missed_dump_loss` (jeśli mogłem zrzucić karę) − `shed_rank_loss` za niższą kartę niż najwyższa, która nie bierze + `suspect_bonus · P(ktoś ma dużo koloru)` | `shed_base_aggr + shed_high_aggr · ranga + shed_kept_aggr · zatrzymane kary` |
| Dokładam pod spód, choć mogłem bezpiecznie zebrać czystą lewę (marnuję niską kartę) | `follow_duck` | −`duck_missed_take_loss` · (1 − ryzyko zebrania) · (1 − postęp) | bez zmian |

Wspólne pojęcia:
- **ryzyko** = min(1, P(wezmę lewę) · oczekiwana kara / „zła lewa”); kara = kara za lewę + karty na stole + moja karta
  + oczekiwane zrzuty następnych graczy (kary tego samego koloru oraz kary od gracza bez koloru),
- **P(renons)** – prawdopodobieństwo (hipergeometryczne, z kart niewidzianych), że komuś po mnie skończył się kolor,
- **P(ktoś ma dużo koloru)** – szansa, że któryś przeciwnik ma ≥ max(3, 40% ręki) kart danego koloru,
- **postęp** = (numer lewy − 1) / 12.

## Znane uproszczenia

- Historia nie zawiera informacji, kto zagrał którą kartę, więc nie śledzimy renonsów konkretnych graczy – tylko prawdopodobieństwa.
- Przy zrzutach i dokładaniu bez brania lewy nie rozróżniamy, którą z niskich kart najlepiej oddać (poza „wyższa lepsza”).
- Reguły o wyjściu w kolor nie mają osobnego wariantu dla rund karanych za lewy (`no_tricks`, `no_seventh_last`) –
  tam „kara w kolorze” = sama kara za lewę.
- Wszystkie liczby w `Params` to propozycje startowe do strojenia.

## Testy

`pytest` (testy w `tests/test_evaluator.py`).
