#!/usr/bin/env python3
"""CLI: wykrywa realne wloty skrzyżowania (kierunek + nazwa ulicy) z
koordynatów przez `generate_intersection_map.find_arms()`, dopasowuje nasze
kanoniczne kody PN/WSCH/PD/ZACH (Etap 1 silnik, kategorie.py) do najbliższych
azymutem rzeczywistych ramion OSM. Wynik nadaje się wprost jako
"wlot_to_arm_direction" dla generate_flow_diagram.py.

Użycie: python3 wykryj_wloty.py --lat X --lon Y [--region-cache DIR] [--local-radius M]
Wypisuje JSON na stdout: {"PN": {"direction": "Północny", "name": "..."}, ...}
"""
from __future__ import annotations

import argparse
import json

from generate_intersection_map import find_arms, load_or_fetch_region

NASZE_BEARING = {"PN": 0, "WSCH": 90, "PD": 180, "ZACH": 270}


def _katowa_odleglosc(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--region-cache", type=str, default="region_cache")
    p.add_argument("--region-radius", type=int, default=4000)
    p.add_argument("--local-radius", type=int, default=150)
    args = p.parse_args()

    G_drive, _, _, _ = load_or_fetch_region(args.region_cache, args.lat, args.lon, args.region_radius)
    _, arms = find_arms(G_drive, args.lat, args.lon, max_arm_dist_m=args.local_radius)
    if not arms:
        raise SystemExit("Nie znaleziono ramion skrzyżowania w zcache'owanym regionie.")

    wynik = {}
    for nasz_kod, nasz_bearing in NASZE_BEARING.items():
        najblizsze = min(arms, key=lambda a: _katowa_odleglosc(a["bearing"], nasz_bearing))
        wynik[nasz_kod] = {"direction": najblizsze["direction"], "name": najblizsze["name"]}

    print(json.dumps(wynik, ensure_ascii=False))


if __name__ == "__main__":
    main()
