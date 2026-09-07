"""CLI: generuje teksty analityczne bez AI (Etap 4, krok 9) dla jednego
punktu z `projekt.json` panelu UI. Wymaga ukończonego kroku 7 (obliczenia).

Użycie: python3 -m panel.silnik.uruchom_teksty_dla_punktu <sciezka_projekt.json> <numer_punktu>
Wypisuje JSON na stdout: {"lokalizacja": "...", "organizacjaRuchu": "...", ...}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .teksty import generuj_wszystkie_teksty


def main() -> None:
    sciezka_projekt = Path(sys.argv[1])
    numer_punktu = int(sys.argv[2])

    projekt = json.loads(sciezka_projekt.read_text(encoding="utf-8"))
    punkt = next(p for p in projekt["punkty"] if p["numer"] == numer_punktu)

    if not punkt.get("obliczenia"):
        raise SystemExit("Brak obliczeń dla tego punktu — najpierw krok 7.")

    print(json.dumps(generuj_wszystkie_teksty(punkt)))


if __name__ == "__main__":
    main()
