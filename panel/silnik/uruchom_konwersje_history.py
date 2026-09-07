"""CLI: konwertuje surowy History.csv na zagregowany Quantity.csv.

Użycie: python3 -m panel.silnik.uruchom_konwersje_history <History.csv> <Quantity_wyjsciowy.csv>
"""
from __future__ import annotations

import sys

import pandas as pd

from .konwersja_history import konwertuj_history_na_quantity


def main() -> None:
    sciezka_wejsciowa, sciezka_wyjsciowa = sys.argv[1], sys.argv[2]
    df_history = pd.read_csv(sciezka_wejsciowa, sep=";", encoding="utf-8")
    wynik = konwertuj_history_na_quantity(df_history)
    wynik.to_csv(sciezka_wyjsciowa, sep=";", index=False)
    print(f"Zapisano: {sciezka_wyjsciowa} ({len(wynik)} wierszy)")


if __name__ == "__main__":
    main()
