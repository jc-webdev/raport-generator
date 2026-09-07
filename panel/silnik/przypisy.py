"""Deterministyczne przypisy jakości danych (§5.6) — generowane z flag QC,
nie przez AI.
"""
from __future__ import annotations


_TEKST_NIEZMOT_NIEDOSTEPNE = (
    "Arkusz godzinowy dla tego punktu nie rejestruje ruchu nie zmotoryzowanego w "
    "rozbiciu na relacje (dostępna jest wyłącznie suma dobowa)."
)

_TEKST_CIEZKIE_ESTYMOWANE = (
    "Arkusz godzinowy dla tego punktu nie rejestruje kategorii ciężarowe/ciężarowe "
    "z naczepami w rozbiciu na relacje (dostępna jest wyłącznie suma dobowa). Powyższy "
    "rozkład kierunkowy jest oszacowany proporcjonalnie do ogólnego udziału każdej "
    "relacji w SDR punktu."
)

_TEKST_NIEZMOT_GODZINOWO_ESTYMOWANE = (
    "Arkusz godzinowy dla tego punktu nie rejestruje ruchu nie zmotoryzowanego w "
    "rozbiciu godzinowym (dostępna jest wyłącznie suma dobowa). Powyższy rozkład "
    "godzinowy jest oszacowany proporcjonalnie do godzinowego profilu ruchu "
    "zmotoryzowanego tego samego punktu."
)


def generuj_przypisy_jakosci(
    relacje_z_niezmot_dostepne: bool,
    relacje_ciezkie_estymowane: bool,
    niezmot_godzinowo_estymowane: bool,
) -> list[dict]:
    przypisy = []
    if not relacje_z_niezmot_dostepne:
        przypisy.append({"kotwica": "T4", "tresc": _TEKST_NIEZMOT_NIEDOSTEPNE})
    if relacje_ciezkie_estymowane:
        przypisy.append({"kotwica": "T5", "tresc": _TEKST_CIEZKIE_ESTYMOWANE})
    if niezmot_godzinowo_estymowane:
        przypisy.append({"kotwica": "T6", "tresc": _TEKST_NIEZMOT_GODZINOWO_ESTYMOWANE})
    return przypisy
