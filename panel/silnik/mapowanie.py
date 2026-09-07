"""Wczytanie surowego CSV (format AISP) i mapowanie liter kierunków na
(wlot, manewr) — raport-panel-generowania-raportow-v2.md §5.1-5.2.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .kategorie import KATEGORIE_WSZYSTKIE
from .opisy import oblicz_manewr


def wczytaj_surowe_csv(sciezka: str | Path) -> pd.DataFrame:
    """Wczytuje CSV w formacie AISP (';' separator, UTF-8).

    Akceptuje dwa warianty nazw kolumn kierunku/czasu — "Kierunek"/"Czas"
    (starszy format, pojedyncza litera = cała relacja, patrz zmapuj_kierunki)
    ORAZ "Kod"/"Godz" (prawdziwy format History->Quantity, patrz
    konwersja_history.py — pojedyncza litera = jedna bramka, para "X-Y" to
    relacja, patrz zmapuj_relacje_z_bramek) — oba normalizowane tutaj do
    "Kierunek"/"Godzina", żeby dalszy kod nie musiał znać różnicy.

    Zwraca df z kolumnami: Kierunek (str), Godzina (int 0-23, wyekstrahowane
    z kolumny czasu) + 12 kolumn kategorii z KATEGORIE_WSZYSTKIE.
    """
    df = pd.read_csv(sciezka, sep=";", encoding="utf-8")
    if "Kod" in df.columns:
        df = df.rename(columns={"Kod": "Kierunek", "Godz": "Czas"})
    df["Godzina"] = pd.to_datetime(df["Czas"]).dt.hour
    kolumny = ["Kierunek", "Godzina"] + KATEGORIE_WSZYSTKIE
    return df[kolumny]


def waliduj_litery(df_raw: pd.DataFrame, kierunek_mapping: dict) -> list[str]:
    """Litery obecne w danych a nieobecne w kierunek_mapping.

    Pusta lista = OK. Nie rzuca wyjątku — decyzję co robić dalej (blokada
    kroku UI) podejmuje wołający.
    """
    litery_w_danych = set(df_raw["Kierunek"].unique())
    litery_zmapowane = set(kierunek_mapping.keys())
    return sorted(litery_w_danych - litery_zmapowane)


def wykryj_duplikaty(kierunek_mapping: dict) -> list[dict]:
    """Grupuje litery mappingu po (wlot, manewr).

    Zwraca listę {"wlot", "manewr", "litery": [...], "sugerowanaAkcja": ...}
    dla każdej grupy z więcej niż jedną literą — kształt qc.duplikatyRelacji.
    """
    grupy: dict[tuple[str, str], list[str]] = {}
    for litera, wm in kierunek_mapping.items():
        klucz = (wm["wlot"], wm["manewr"])
        grupy.setdefault(klucz, []).append(litera)

    duplikaty = []
    for (wlot, manewr), litery in grupy.items():
        if len(litery) > 1:
            duplikaty.append({
                "wlot": wlot,
                "manewr": manewr,
                "litery": sorted(litery),
                "sugerowanaAkcja": "scal w jedną relację (suma po kluczu wlot+manewr)",
            })
    return duplikaty


def zmapuj_kierunki(df_raw: pd.DataFrame, kierunek_mapping: dict) -> pd.DataFrame:
    """Mapuje litery na (wlot, manewr) i grupuje (sumuje) po (wlot, manewr, Godzina).

    Zakłada, że waliduj_litery() już przeszła (nie waliduje ponownie).
    Grupowanie automatycznie scala zdublowane litery (np. K+L -> PN/Wprost)
    i zdublowane bramki AISP o tej samej (wlot, manewr) — §8.3.
    """
    df = df_raw.copy()
    df["wlot"] = df["Kierunek"].map(lambda l: kierunek_mapping[l]["wlot"])
    df["manewr"] = df["Kierunek"].map(lambda l: kierunek_mapping[l]["manewr"])

    zgrupowane = (
        df.groupby(["wlot", "manewr", "Godzina"], as_index=False)[KATEGORIE_WSZYSTKIE]
        .sum()
    )
    return zgrupowane


# --- Model "bramka -> wlot" (Etap 4 krok 5, realny format AISP History/Quantity) --
#
# W prawdziwym eksporcie AISP pojedyncza litera to jedna fizyczna bramka/wlot
# skrzyżowania (np. kamera na jednym z ramion), a obserwowana "Kierunek" to
# PARA bramek "X-Y" = wjazd bramką X, wyjazd bramką Y (patrz
# konwersja_history.py). Użytkownik mapuje więc TYLKO pojedyncze bramki na
# strony świata (PN/WSCH/PD/ZACH) — manewr (Prawo/Wprost/Lewo/Zawracający)
# liczy się GEOMETRYCZNIE z pary wlot_wejścia/wlot_wyjścia (opisy.oblicz_manewr),
# zamiast być klikany ręcznie dla każdej relacji osobno.


def rozbij_relacje(kierunek: str) -> tuple[str, str] | None:
    """"A-E" -> ("A", "E"). None gdy wartość nie jest parą bramek (np. pusta,
    albo pojedyncza litera bez myślnika — niepełny ślad, patrz krok 3 UI)."""
    if not isinstance(kierunek, str) or "-" not in kierunek:
        return None
    wejscie, _, wyjscie = kierunek.partition("-")
    if not wejscie or not wyjscie:
        return None
    return wejscie, wyjscie


def waliduj_bramki(df_raw: pd.DataFrame, mapowanie_bramek: dict) -> list[str]:
    """Bramki obecne w danych (jako część pary "X-Y" w kolumnie Kierunek) a
    nieobecne w mapowanie_bramek. Pusta lista = OK."""
    bramki_w_danych: set[str] = set()
    for wartosc in df_raw["Kierunek"].unique():
        rozbita = rozbij_relacje(wartosc)
        if rozbita:
            bramki_w_danych.update(rozbita)
    bramki_zmapowane = set(mapowanie_bramek.keys())
    return sorted(bramki_w_danych - bramki_zmapowane)


def zmapuj_relacje_z_bramek(df_raw: pd.DataFrame, mapowanie_bramek: dict) -> pd.DataFrame:
    """Jak zmapuj_kierunki(), ale wejściem jest mapowanie POJEDYNCZYCH bramek
    na wloty (nie gotowych relacji na wlot+manewr) — manewr wyliczany z
    geometrii. Zakłada że waliduj_bramki() już przeszła (nie waliduje ponownie).
    Wiersze bez rozbijalnej pary bramek (patrz rozbij_relacje) są pomijane —
    tak samo jak w konwersji History->Quantity, niepełny ślad nie ma
    jednoznacznej relacji.
    """
    df = df_raw.copy()
    rozbite = df["Kierunek"].map(rozbij_relacje)
    df = df[rozbite.notna()].copy()
    rozbite = rozbite[rozbite.notna()]

    df["wlot"] = rozbite.map(lambda para: mapowanie_bramek[para[0]])
    wlot_wyjscia = rozbite.map(lambda para: mapowanie_bramek[para[1]])
    df["manewr"] = [oblicz_manewr(a, b) for a, b in zip(df["wlot"], wlot_wyjscia)]

    return (
        df.groupby(["wlot", "manewr", "Godzina"], as_index=False)[KATEGORIE_WSZYSTKIE]
        .sum()
    )
