#!/usr/bin/env python3
"""Rysunek 3.n.5 — profil godzinowy ruchu zmotoryzowanego i niezmotoryzowanego
(dwie osie, jak generuj_wykres_pogoda.py) na podstawie `obliczenia.godzinowa`,
czyli dokładnie tych samych danych co Tabela 3.n.6 — bez nowego eksportu.

Użycie: python3 generuj_wykres_profil_kategorie.py <obliczenia.json> <output.png>
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
    godzinowa = dane["obliczenia"]["godzinowa"]

    godziny = [w["godzina"] for w in godzinowa]
    zmot = [w["zmotoryzowany"] for w in godzinowa]
    niezmot = [w["niezmotoryzowany"] for w in godzinowa]

    # constrained_layout SAM w sobie (bez bbox_inches) nadal lekko ucinał
    # ostatnie znaki obu skrajnych etykiet osi przy tej czcionce i obróconych
    # etykietach godzin — dopiero constrained_layout + bbox_inches="tight" z
    # dodatkowym marginesem (pad_inches) daje pełne, nieprzycięte etykiety.
    fig, ax1 = plt.subplots(figsize=(9, 4), constrained_layout=True)
    ax1.plot(godziny, zmot, color=ORANGE, marker="o", markersize=3, linewidth=2)
    ax1.set_ylabel("Ruch zmotoryzowany [poj./h]", fontsize=19, color=ORANGE)
    ax1.tick_params(axis="y", labelcolor=ORANGE, labelsize=14)
    ax1.set_xlabel("Godzina", fontsize=19)
    ax1.spines[["top"]].set_visible(False)
    for i, label in enumerate(ax1.get_xticklabels()):
        label.set_fontsize(14)
        label.set_rotation(90)
        if i % 2 == 1:
            label.set_visible(False)

    ax2 = ax1.twinx()
    ax2.plot(godziny, niezmot, color=GRAPHITE, marker="s", markersize=3, linewidth=1.6, linestyle="--")
    ax2.set_ylabel("Ruch nie zmotoryzowany [poj./h]", fontsize=19, color=GRAPHITE)
    ax2.tick_params(axis="y", labelcolor=GRAPHITE, labelsize=14)
    ax2.spines[["top"]].set_visible(False)

    # ax.legend() (nie fig.legend()) — constrained_layout rezerwuje dla niej
    # miejsce tylko gdy jest częścią danego Axes, inaczej znów przycina
    # etykiety skrajnych osi tak jak przy manualnym bbox_to_anchor na figurze.
    ax2.legend(
        handles=[
            plt.Line2D([], [], color=ORANGE, marker="o", markersize=4, linewidth=2, label="Zmotoryzowany"),
            plt.Line2D([], [], color=GRAPHITE, marker="s", markersize=4, linewidth=1.6, linestyle="--", label="Nie zmotoryzowany"),
        ],
        loc="upper right", fontsize=15,
    )
    plt.savefig(sciezka_png, dpi=200, bbox_inches="tight", pad_inches=0.55)
    print(f"Zapisano: {sciezka_png}")


if __name__ == "__main__":
    main()
