#!/usr/bin/env python3
"""R11 — Udział pory dziennej i nocnej w ruchu. Jedyny wykres w §3.n.6
oznaczony w specyfikacji jako gotowy generator (nie placeholder).

Użycie: python3 generuj_wykres_pory_doby.py <obliczenia.json> <output.png>
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORANGE = "#FF7900"
GRAPHITE = "#4A4A4A"


def main():
    sciezka_json, sciezka_png = sys.argv[1], sys.argv[2]
    with open(sciezka_json, encoding="utf-8") as f:
        dane = json.load(f)
    pory = dane["obliczenia"]["poryDoby"]

    etykiety = ["Dzień\n(06:00–22:00)", "Noc\n(22:00–06:00)"]
    wartosci = [pory["dzien"][0], pory["noc"][0]]
    udzialy = [pory["dzien"][1], pory["noc"][1]]

    fig, ax = plt.subplots(figsize=(6, 4))
    slupki = ax.bar(etykiety, wartosci, color=[ORANGE, GRAPHITE], width=0.5)
    for slupek, wartosc, udzial in zip(slupki, wartosci, udzialy):
        ax.text(slupek.get_x() + slupek.get_width() / 2, slupek.get_height(),
                f"{wartosc:,.0f}".replace(",", " ") + f" poj.\n({udzial:.1f}%)".replace(".", ","),
                ha="center", va="bottom", fontsize=11)

    ax.set_ylabel("Natężenie ruchu [poj./dobę]", fontsize=11)
    ax.set_ylim(0, max(wartosci) * 1.25)
    ax.spines[["top", "right"]].set_visible(False)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontsize(10)
    # ponytail: font Carlito niedostępny lokalnie, matplotlib używa domyślnego —
    # podmienić gdy font będzie zainstalowany w środowisku docelowym.

    plt.tight_layout()
    plt.savefig(sciezka_png, dpi=200)
    print(f"Zapisano: {sciezka_png}")


if __name__ == "__main__":
    main()
