#!/usr/bin/env python3
"""4.2 — natężenie w stałych oknach szczytu (7-8 i 15-16) per punkt projektu.

Użycie: python3 generuj_wykres_szczyty_projektu.py <projekt.json> <output.png>
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ORANGE = "#FF7900"
GRAPHITE = "#4A4A4A"


def main():
    sciezka_json, sciezka_png = sys.argv[1], sys.argv[2]
    with open(sciezka_json, encoding="utf-8") as f:
        projekt = json.load(f)

    etykiety = [p["id"] for p in projekt["punkty"]]
    poranne = [p["obliczenia"]["szczytOknoPoranne"]["wartosc"] for p in projekt["punkty"]]
    popoludniowe = [p["obliczenia"]["szczytOknoPopoludniowe"]["wartosc"] for p in projekt["punkty"]]

    x = np.arange(len(etykiety))
    szer = 0.35

    fig, ax = plt.subplots(figsize=(max(6, len(etykiety) * 1.6), 4.5))
    ax.bar(x - szer / 2, poranne, szer, label="Szczyt poranny (7:00-8:00)", color=ORANGE)
    ax.bar(x + szer / 2, popoludniowe, szer, label="Szczyt popołudniowy (15:00-16:00)", color=GRAPHITE)

    ax.set_ylabel("Natężenie [poj./h]", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(etykiety)
    ax.legend(fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(sciezka_png, dpi=200)
    print(f"Zapisano: {sciezka_png}")


if __name__ == "__main__":
    main()
