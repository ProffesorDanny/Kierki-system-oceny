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

### Z linii komend

Uruchamiane z katalogu projektu (tam, gdzie jest folder `kierki/`). Stan gry podaje się w pliku JSON:

| Pole | Znaczenie |
|---|---|
| `round` | rodzaj rundy, np. `no_queens` (lista niżej) |
| `hand` | moja ręka **przed** zagraniem: 13 − liczba zakończonych lew kart |
| `history` | zakończone lewy, każda jako 4 karty w kolejności kładzenia (opcjonalne) |
| `current_trick` | karty już leżące w bieżącej lewie; pusta lista = ja wychodzę (opcjonalne) |
| `card` | karta do oceny (opcjonalne); bez tego pola oceniane są wszystkie legalne ruchy, od najlepszego |

Przykład (`examples/bez_dam_krol_pik.json`): runda bez dam, zeszły już Ap, Dp, 10p, 7p, 8p, 6p, 4p, 2p i Jp,
w 4. lewie wychodzę Kp – moim ostatnim pikiem:

```json
{
  "round": "no_queens",
  "hand": ["Ks", "2h", "3h", "4h", "5h", "2d", "3d", "4d", "6c", "7c"],
  "history": [
    ["As", "Qs", "10s", "7s"],
    ["8s", "6s", "4s", "2s"],
    ["Js", "2c", "3c", "4c"]
  ],
  "current_trick": [],
  "card": "Ks"
}
```

```powershell
python -m kierki examples\bez_dam_krol_pik.json        # PowerShell / cmd
Get-Content examples\bez_dam_krol_pik.json | python -m kierki   # albo przez stdin
```

```bash
python -m kierki examples/bez_dam_krol_pik.json         # bash
python -m kierki < examples/bez_dam_krol_pik.json
```

Wynik (JSON):

```json
{
  "card": "Ks",
  "legal": true,
  "errors": [],
  "correctness": 78.0,
  "verdict": "poprawne",
  "aggressiveness": 98.9,
  "aggressiveness_label": "bardzo agresywny",
  "scenario": "lead",
  "reasons": [
    "Ostatnia karta w tym kolorze - pozbywam się koloru.",
    "Najkrótszy kolor bez moich kart punktowanych - pozbywam się koloru.",
    "Sporo tego koloru już zagrano - rośnie szansa, że komuś się skończy."
  ],
  "components": {"p_win": 1.0, "risk": 0.22, "void_prob": 0.628, "progress": 0.25}
}
```

Bez pola `card` dostaniesz listę takich obiektów dla każdej legalnej karty (tu: niskie karty ok. 93 pkt, Kp 78).
Nielegalny ruch zwraca `"legal": false` i opis w `errors`. Jeśli polskie znaki w wyniku są zniekształcone
(przekierowanie do pliku lub potok), ustaw kodowanie UTF-8: `$env:PYTHONUTF8=1` (PowerShell) lub `export PYTHONUTF8=1` (bash).

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

`python -m pytest` – testy w `tests/test_evaluator.py` (podstawy) i `tests/test_scenarios.py` (scenariusze z różnych
rund i etapów rozdania).

Każde uruchomienie zapisuje raport **`tests/wyniki_testow.md`** (generuje go `tests/conftest.py`): dla każdego testu
opis, co sprawdza, status, wejście (runda, ręka, historia, karty na stole) i wynik oceny każdej sprawdzanej karty.
Raport obejmuje tylko testy z danego uruchomienia – np. `python -m pytest -k rozbojnik` nadpisze go samymi testami
rozbójnika.
