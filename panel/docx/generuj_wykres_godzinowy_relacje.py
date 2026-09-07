#!/usr/bin/env python3
"""Wykres godzinowy (0-23) natężenia ruchu w podziale na relacje — jedna
linia na relację. Używany dla Rysunek 3.n.3 ("...według relacji", klucz
"relacjeZmot") i 3.n.4 ("...pojazdów ciężkich według relacji", klucz
"relacjeCiezkie") — te same dane wejściowe, inny wybór serii.

Dane wejściowe: panel/silnik/eksportuj_godzinowe_relacje.py.
Użycie: python3 generuj_wykres_godzinowy_relacje.py <dane.json> <klucz_serii> <output.png> <etykieta_osi_y>
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    sciezka_json, klucz_serii, sciezka_png, etykieta_y = sys.argv[1:5]
    with open(sciezka_json, encoding="utf-8") as f:
        dane = json.load(f)

    godziny = dane["godziny"]
    serie = dane[klucz_serii]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    for seria in serie:
        ax.plot(godziny, seria["wartosci"], marker="o", markersize=2, linewidth=1.6, label=seria["opis"])

    ax.set_xlabel("Godzina", fontsize=19)
    ax.set_ylabel(etykieta_y, fontsize=19)
    ax.tick_params(axis="y", labelsize=14)
    ax.spines[["top", "right"]].set_visible(False)
    for i, label in enumerate(ax.get_xticklabels()):
        label.set_fontsize(14)
        label.set_rotation(90)
        if i % 2 == 1:
            label.set_visible(False)
    ax.legend(fontsize=12, loc="upper left", bbox_to_anchor=(1.01, 1.0))

    plt.savefig(sciezka_png, dpi=200, bbox_inches="tight")
    print(f"Zapisano: {sciezka_png}")


if __name__ == "__main__":
    main()
