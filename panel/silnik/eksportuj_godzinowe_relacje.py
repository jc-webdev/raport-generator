"""CLI: eksportuje godzinowe (0-23) serie ruchu zmotoryzowanego i ciężkiego
w podziale na relacje — dane wejściowe dla wykresów Rysunek 3.n.3
("Rozkład godzinowy ruchu według relacji") i 3.n.4 ("...pojazdów ciężkich
według relacji"), których do tej pory nie było czym narysować (`obliczenia`
ma tylko sumy dobowe per relacja, bez rozbicia godzinowego).

Użycie: python3 -m panel.silnik.eksportuj_godzinowe_relacje <projekt.json> <numer_punktu> <output.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .kategorie import KATEGORIE_CIEZKIE, KATEGORIE_ZMOTORYZOWANE
from .opisy import opisz_relacje, sortuj_relacje
from .uruchom_dla_punktu import wczytaj_i_zmapuj_punkt


def _serie_godzinowe(df, kategorie, geometria_regularna):
    wyniki = []
    for (wlot, manewr), grupa in df.groupby(["wlot", "manewr"]):
        per_godzina = grupa.groupby("Godzina")[kategorie].sum().sum(axis=1)
        wartosci = [int(per_godzina.get(h, 0)) for h in range(24)]
        wyniki.append({
            "wlot": wlot, "manewr": manewr,
            "opis": opisz_relacje(wlot, manewr, geometria_regularna),
            "wartosci": wartosci,
        })
    return sortuj_relacje(wyniki)


def main() -> None:
    sciezka_projekt = Path(sys.argv[1])
    numer_punktu = int(sys.argv[2])
    sciezka_json = Path(sys.argv[3])

    punkt, df = wczytaj_i_zmapuj_punkt(sciezka_projekt, numer_punktu)

    wynik = {
        "godziny": [f"{h:02d}:00" for h in range(24)],
        "relacjeZmot": _serie_godzinowe(df, KATEGORIE_ZMOTORYZOWANE, punkt["geometriaRegularna"]),
        "relacjeCiezkie": _serie_godzinowe(df, KATEGORIE_CIEZKIE, punkt["geometriaRegularna"]),
    }
    sciezka_json.parent.mkdir(parents=True, exist_ok=True)
    sciezka_json.write_text(json.dumps(wynik, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"ok": True, "sciezka": str(sciezka_json), "relacje": len(wynik["relacjeZmot"])}))


if __name__ == "__main__":
    main()
