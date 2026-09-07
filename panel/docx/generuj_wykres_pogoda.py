#!/usr/bin/env python3
"""Wykres godzinowy temperatury i opadów w trakcie pomiaru (dane godzinowe
Open-Meteo Archive, patrz server.js::wykryjPogodeGodzinowo) — wstawiany w
karcie skrzyżowania (3.n.1), tuż przed schematem skrzyżowania.

Użycie: python3 generuj_wykres_pogoda.py <dane.json> <output.png>
dane.json: {"godziny": ["00:00", ...], "temperatura": [...], "opady": [...]}
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

    godziny = dane["godziny"]
    temperatura = dane["temperatura"]
    opady = dane["opady"]

    # Szerszy (renderowany na pełną szerokość treści strony — patrz
    # budujPunkt.js::SZEROKOSC_TRESCI_CM) i niższy (ok. 3/5 poprzedniej
    # wysokości) niż pierwotny (9, 4) — stąd bardziej wydłużony aspekt.
    # constrained_layout — patrz generuj_wykres_profil_kategorie.py, ten sam
    # problem z przycinaniem etykiet skrajnych osi przy twinx() i dużej czcionce.
    fig, ax1 = plt.subplots(figsize=(14, 2.9), constrained_layout=True)
    ax1.plot(godziny, temperatura, color=ORANGE, marker="o", markersize=3, linewidth=2, zorder=3)
    ax1.set_ylabel("Temperatura [°C]", fontsize=19, color=ORANGE)
    ax1.tick_params(axis="y", labelcolor=ORANGE, labelsize=14)
    ax1.set_xlabel("Godzina", fontsize=19)
    ax1.spines[["top"]].set_visible(False)
    for i, label in enumerate(ax1.get_xticklabels()):
        label.set_fontsize(14)
        label.set_rotation(90)
        if i % 2 == 1:
            label.set_visible(False)  # co druga godzina — inaczej etykiety się zlewają

    ax2 = ax1.twinx()
    maks_opady = max(opady) if max(opady) > 0 else 1
    ax2.bar(godziny, opady, color=GRAPHITE, alpha=0.35, width=0.6, zorder=1)
    ax2.set_ylabel("Opady [mm]", fontsize=19, color=GRAPHITE)
    ax2.tick_params(axis="y", labelcolor=GRAPHITE, labelsize=14)
    ax2.spines[["top"]].set_visible(False)
    ax2.set_ylim(0, maks_opady * 3)  # słupki opadów nisko w tle, nie zasłaniają linii temperatury

    # ax.legend() (nie fig.legend()) — z constrained_layout rezerwuje dla niej
    # miejsce, inaczej przycina etykiety skrajnych osi (patrz profil_kategorie).
    ax2.legend(
        handles=[
            plt.Line2D([], [], color=ORANGE, marker="o", markersize=4, linewidth=2, label="Temperatura [°C]"),
            plt.Rectangle((0, 0), 1, 1, color=GRAPHITE, alpha=0.35, label="Opady [mm]"),
        ],
        loc="upper right", fontsize=15,
    )
    plt.savefig(sciezka_png, dpi=200, bbox_inches="tight", pad_inches=0.55)
    print(f"Zapisano: {sciezka_png}")


if __name__ == "__main__":
    main()
