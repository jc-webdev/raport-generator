"""9 funkcji obliczeniowych z §5.3 specyfikacji panelu.

Wszystkie funkcje działają na zmapowanym df (kolumny: wlot, manewr,
Godzina, + 12 kolumn kategorii) produkowanym przez
`mapowanie.zmapuj_kierunki`.
"""
from __future__ import annotations

import pandas as pd

from .kategorie import KATEGORIE_CIEZKIE, KATEGORIE_NIEZMOT, KATEGORIE_PELNE, KATEGORIE_WSZYSTKIE, \
    KATEGORIE_ZMOTORYZOWANE
from .opisy import opisz_relacje, sortuj_relacje


def _godz(h: int) -> str:
    return f"{h:02d}:00"


def oblicz_sdr_i_szczyt_dobowy(df: pd.DataFrame) -> tuple[int, dict]:
    sdr = int(df[KATEGORIE_ZMOTORYZOWANE].sum().sum())

    suma_godzinowa = df.groupby("Godzina")[KATEGORIE_ZMOTORYZOWANE].sum().sum(axis=1)
    if suma_godzinowa.empty:
        szczyt_dobowy = {"wartosc": 0, "godzina": _godz(0)}
    else:
        godzina_szczytu = int(suma_godzinowa.idxmax())
        szczyt_dobowy = {"wartosc": int(suma_godzinowa.max()), "godzina": _godz(godzina_szczytu)}

    return sdr, szczyt_dobowy


def oblicz_relacje_sdr(df: pd.DataFrame, sdr_punkt: int, geometria_regularna: bool) -> list[dict]:
    relacje = []
    for (wlot, manewr), grupa in df.groupby(["wlot", "manewr"]):
        sdr_relacji = int(grupa[KATEGORIE_ZMOTORYZOWANE].sum().sum())
        suma_godzinowa = grupa.groupby("Godzina")[KATEGORIE_ZMOTORYZOWANE].sum().sum(axis=1)
        godzina_szczytu = int(suma_godzinowa.idxmax())
        szczyt = int(suma_godzinowa.max())
        udzial = round(sdr_relacji / sdr_punkt * 100, 1) if sdr_punkt else 0.0

        relacje.append({
            "wlot": wlot,
            "manewr": manewr,
            "opis": opisz_relacje(wlot, manewr, geometria_regularna),
            "sdr": sdr_relacji,
            "udzial": udzial,
            "szczyt": szczyt,
            "godzinaSzczytu": _godz(godzina_szczytu),
        })

    return sortuj_relacje(relacje)


def oblicz_relacje_z_niezmot(
    df: pd.DataFrame, relacje_sdr: list[dict], suma_dobowa_niezmot: int | None = None,
) -> tuple[list[dict], bool]:
    niezmot_w_df = int(df[KATEGORIE_NIEZMOT].sum().sum())
    if suma_dobowa_niezmot is None:
        suma_dobowa_niezmot = niezmot_w_df

    if niezmot_w_df == 0 and suma_dobowa_niezmot > 0:
        return [], False

    wyniki = []
    for r in relacje_sdr:
        subset = df[(df["wlot"] == r["wlot"]) & (df["manewr"] == r["manewr"])]
        niezmot = int(subset[KATEGORIE_NIEZMOT].sum().sum())
        wyniki.append({
            "wlot": r["wlot"], "manewr": r["manewr"], "opis": r["opis"],
            "suma": r["sdr"] + niezmot,
        })

    wyniki = sortuj_relacje(wyniki)
    total = sum(w["suma"] for w in wyniki)
    for w in wyniki:
        w["udzial"] = round(w["suma"] / total * 100, 1) if total else 0.0

    return [{"opis": w["opis"], "suma": w["suma"], "udzial": w["udzial"]} for w in wyniki], True


def oblicz_relacje_ciezkie(
    df: pd.DataFrame, relacje_sdr: list[dict], suma_dobowa_ciezkie: int | None = None,
) -> tuple[list[dict], bool]:
    ciezkie_w_df = int(df[KATEGORIE_CIEZKIE].sum().sum())
    if suma_dobowa_ciezkie is None:
        suma_dobowa_ciezkie = ciezkie_w_df

    estymowane = ciezkie_w_df == 0 and suma_dobowa_ciezkie > 0
    sdr_punkt = sum(r["sdr"] for r in relacje_sdr)

    wyniki = []
    for r in relacje_sdr:
        if estymowane:
            suma = round(suma_dobowa_ciezkie * r["sdr"] / sdr_punkt) if sdr_punkt else 0
        else:
            subset = df[(df["wlot"] == r["wlot"]) & (df["manewr"] == r["manewr"])]
            suma = int(subset[KATEGORIE_CIEZKIE].sum().sum())
        wyniki.append({"wlot": r["wlot"], "manewr": r["manewr"], "opis": r["opis"], "suma": suma})

    total = sum(w["suma"] for w in wyniki)
    for w in wyniki:
        w["udzial"] = round(w["suma"] / total * 100, 1) if total else 0.0

    return [{"opis": w["opis"], "suma": w["suma"], "udzial": w["udzial"]} for w in wyniki], estymowane


def oblicz_upc(relacje_sdr: list[dict], relacje_ciezkie: list[dict]) -> list[dict]:
    wyniki = []
    for r_sdr, r_ciezkie in zip(relacje_sdr, relacje_ciezkie):
        upc = round(r_ciezkie["suma"] / r_sdr["sdr"] * 100, 1) if r_sdr["sdr"] else 0.0
        wyniki.append({"opis": r_sdr["opis"], "upc": upc})
    return wyniki


def oblicz_godzinowa(
    df: pd.DataFrame, sdr_punkt: int, suma_dobowa_niezmot: int | None = None,
) -> tuple[list[dict], bool]:
    niezmot_w_df = int(df[KATEGORIE_NIEZMOT].sum().sum())
    if suma_dobowa_niezmot is None:
        suma_dobowa_niezmot = niezmot_w_df
    estymowane = niezmot_w_df == 0 and suma_dobowa_niezmot > 0

    wiersze = []
    for h in range(24):
        subset = df[df["Godzina"] == h]
        zmot = int(subset[KATEGORIE_ZMOTORYZOWANE].sum().sum())
        if estymowane:
            niezmot = round(suma_dobowa_niezmot * zmot / sdr_punkt) if sdr_punkt else 0
        else:
            niezmot = int(subset[KATEGORIE_NIEZMOT].sum().sum())
        udzial_zmot = round(zmot / sdr_punkt * 100, 1) if sdr_punkt else 0.0
        wiersze.append({
            "godzina": _godz(h), "zmotoryzowany": zmot, "udzialZmot": udzial_zmot,
            "niezmotoryzowany": niezmot,
        })

    total_niezmot = sum(w["niezmotoryzowany"] for w in wiersze)
    for w in wiersze:
        w["udzialNiezmot"] = round(w["niezmotoryzowany"] / total_niezmot * 100, 1) if total_niezmot else 0.0

    return wiersze, estymowane


def oblicz_pory_doby(df: pd.DataFrame) -> dict:
    maska_dzien = (df["Godzina"] >= 6) & (df["Godzina"] < 22)
    maska_noc = ~maska_dzien

    dzien = int(df[maska_dzien][KATEGORIE_ZMOTORYZOWANE].sum().sum())
    noc = int(df[maska_noc][KATEGORIE_ZMOTORYZOWANE].sum().sum())
    total = dzien + noc

    return {
        "dzien": [dzien, round(dzien / total * 100, 1) if total else 0.0],
        "noc": [noc, round(noc / total * 100, 1) if total else 0.0],
    }


def oblicz_szczyty_okna_stale(df: pd.DataFrame) -> tuple[dict, dict]:
    poranne = int(df[df["Godzina"] == 7][KATEGORIE_ZMOTORYZOWANE].sum().sum())
    popoludniowe = int(df[df["Godzina"] == 15][KATEGORIE_ZMOTORYZOWANE].sum().sum())

    return (
        {"wartosc": poranne, "zakres": "07:00-08:00"},
        {"wartosc": popoludniowe, "zakres": "15:00-16:00"},
    )


def oblicz_strukture_rodzajowa(df: pd.DataFrame, sdr_punkt: int) -> tuple[list[dict], int]:
    suma_cala = int(df[KATEGORIE_WSZYSTKIE].sum().sum())

    wiersze = []
    for kolumna, nazwa in KATEGORIE_PELNE.items():
        suma = int(df[kolumna].sum())
        if kolumna in KATEGORIE_ZMOTORYZOWANE:
            udzial_zmot = round(suma / sdr_punkt * 100, 1) if sdr_punkt else 0.0
        else:
            udzial_zmot = None
        udzial_cale = round(suma / suma_cala * 100, 1) if suma_cala else 0.0
        wiersze.append({
            "kategoria": nazwa, "suma": suma,
            "udzialZmotoryzowane": udzial_zmot, "udzialCale": udzial_cale,
        })

    return wiersze, suma_cala
