"""Składa wynik wszystkich funkcji obliczeniowych w jedną strukturę
zgodną z polem `obliczenia` w projekt.json.
"""
from __future__ import annotations

import pandas as pd

from . import obliczenia as o


def oblicz_wszystko(
    df_mapped: pd.DataFrame,
    geometria_regularna: bool,
    suma_dobowa_niezmot: int | None = None,
    suma_dobowa_ciezkie: int | None = None,
) -> dict:
    sdr, szczyt_dobowy = o.oblicz_sdr_i_szczyt_dobowy(df_mapped)
    relacje_sdr = o.oblicz_relacje_sdr(df_mapped, sdr, geometria_regularna)

    relacje_z_niezmot, relacje_z_niezmot_dostepne = o.oblicz_relacje_z_niezmot(
        df_mapped, relacje_sdr, suma_dobowa_niezmot)
    relacje_ciezkie, relacje_ciezkie_estymowane = o.oblicz_relacje_ciezkie(
        df_mapped, relacje_sdr, suma_dobowa_ciezkie)

    upc = o.oblicz_upc(relacje_sdr, relacje_ciezkie)

    godzinowa, niezmot_godzinowo_estymowane = o.oblicz_godzinowa(
        df_mapped, sdr, suma_dobowa_niezmot)
    pory_doby = o.oblicz_pory_doby(df_mapped)
    szczyt_poranne, szczyt_popoludniowe = o.oblicz_szczyty_okna_stale(df_mapped)
    struktura_rodzajowa, struktura_suma_cala = o.oblicz_strukture_rodzajowa(df_mapped, sdr)

    ruch_ciezki_suma = sum(r["suma"] for r in relacje_ciezkie)

    return {
        "sdr": sdr,
        "szczytDobowy": szczyt_dobowy,
        "szczytOknoPoranne": szczyt_poranne,
        "szczytOknoPopoludniowe": szczyt_popoludniowe,
        "relacjeSDR": relacje_sdr,
        "relacjeZNiezmot": relacje_z_niezmot,
        "relacjeZNiezmotDostepne": relacje_z_niezmot_dostepne,
        "relacjeCiezkie": relacje_ciezkie,
        "relacjeCiezkieEstymowane": relacje_ciezkie_estymowane,
        "ruchCiezkiSuma": ruch_ciezki_suma,
        "upc": upc,
        "godzinowa": godzinowa,
        "niezmotGodzinowoEstymowane": niezmot_godzinowo_estymowane,
        "poryDoby": pory_doby,
        "strukturaRodzajowa": struktura_rodzajowa,
        "strukturaRodzajowaSumaCala": struktura_suma_cala,
    }
