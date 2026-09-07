#!/usr/bin/env python3
"""Szary placeholder z podpisem — dla rysunków bez jeszcze gotowego
generatora/uploadu (R1 na razie, R3 kamera, R8/R9/R10 kombo-wykresy).

Użycie: python3 generuj_placeholder.py "<tekst>" <output.png>
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

tekst, sciezka_png = sys.argv[1], sys.argv[2]

fig, ax = plt.subplots(figsize=(9, 5.5))
ax.set_facecolor("#E5E5E5")
fig.patch.set_facecolor("#E5E5E5")
ax.text(0.5, 0.5, tekst, ha="center", va="center", fontsize=16, color="#6b6b6b", wrap=True)
ax.set_xticks([])
ax.set_yticks([])
for spine in ax.spines.values():
    spine.set_visible(False)
plt.savefig(sciezka_png, dpi=150, facecolor="#E5E5E5")
print(f"Zapisano: {sciezka_png}")
