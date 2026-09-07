#!/usr/bin/env python3
"""Rysunek 4.1 w trybie zagregowanym Podsumowania (N > próg analizy pełnej,
patrz budujRaport.js::budujPodsumowanie) — histogram rozkładu SDR wszystkich
punktów projektu, zastępuje wykres słupkowy 1:1 na punkt (nieczytelny przy
dużym N).

Użycie: python3 generuj_wykres_histogram_sdr.py <projekt_wykresy.json> <output.png>
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

    wartosci = [p["obliczenia"]["sdr"] for p in projekt["punkty"]]
    liczba_binow = min(20, max(5, len(wartosci) // 3))

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(wartosci, bins=liczba_binow, color=ORANGE, edgecolor="white")
    ax.set_xlabel("SDR [poj./dobę]", fontsize=11)
    ax.set_ylabel("Liczba punktów pomiarowych", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontsize(10)

    plt.tight_layout()
    plt.savefig(sciezka_png, dpi=200)
    print(f"Zapisano: {sciezka_png}")


if __name__ == "__main__":
    main()
