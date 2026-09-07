#!/usr/bin/env python3
"""4.1 — porównawczy wykres słupkowy SDR punktów projektu (tryb pełny, N<=próg).

Użycie: python3 generuj_wykres_zestawienie_sdr.py <projekt.json> <output.png>
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORANGE = "#FF7900"


def main():
    sciezka_json, sciezka_png = sys.argv[1], sys.argv[2]
    with open(sciezka_json, encoding="utf-8") as f:
        projekt = json.load(f)

    etykiety = [p["id"] for p in projekt["punkty"]]
    wartosci = [p["obliczenia"]["sdr"] for p in projekt["punkty"]]

    fig, ax = plt.subplots(figsize=(max(6, len(etykiety) * 1.2), 4.5))
    slupki = ax.bar(etykiety, wartosci, color=ORANGE, width=0.5)
    for slupek, wartosc in zip(slupki, wartosci):
        ax.text(slupek.get_x() + slupek.get_width() / 2, slupek.get_height(),
                f"{wartosc:,.0f}".replace(",", " "), ha="center", va="bottom", fontsize=10)

    ax.set_ylabel("SDR [poj./dobę]", fontsize=11)
    ax.set_ylim(0, max(wartosci) * 1.2 if wartosci else 1)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(sciezka_png, dpi=200)
    print(f"Zapisano: {sciezka_png}")


if __name__ == "__main__":
    main()
