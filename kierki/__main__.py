"""CLI: python -m kierki [plik.json]   (bez pliku czyta stdin)

Wejście JSON:
{
  "round": "no_hearts",
  "hand": ["9h", "4h", ...],           // 13 - len(history) kart
  "history": [["2c","5c","Kc","3c"]],  // zakończone lewy w kolejności kładzenia
  "current_trick": ["3h", "5h"],       // karty już leżące w lewie
  "card": "9h"                         // opcjonalnie; bez tego oceniane są wszystkie legalne ruchy
}
"""
import json
import sys
from dataclasses import asdict

from . import GameState, RoundType, evaluate_all, evaluate_move


def main() -> None:
    raw = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
    d = json.loads(raw)
    state = GameState(
        hand=d["hand"],
        round_type=RoundType(d["round"]),
        history=d.get("history", []),
        current_trick=d.get("current_trick", []),
    )
    if "card" in d:
        out = asdict(evaluate_move(state, d["card"]))
    else:
        out = [asdict(e) for e in evaluate_all(state)]
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
