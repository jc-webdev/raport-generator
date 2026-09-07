"""Algorytm opisu relacji (§5.4) i sortowania relacji (§5.5)."""
from __future__ import annotations

from .kategorie import MANEWR_ORDER, WLOT_ORDER

BEARING = {"PN": 0, "WSCH": 90, "PD": 180, "ZACH": 270}
REVERSE_BEARING = {v: k for k, v in BEARING.items()}

DOPELNIACZ = {"PN": "północy", "WSCH": "wschodu", "PD": "południa", "ZACH": "zachodu"}
BIERNIK = {"PN": "północ", "WSCH": "wschód", "PD": "południe", "ZACH": "zachód"}
PREFIKS_EUFONICZNY = {"WSCH": "Ze"}  # domyślnie "Z"

MANEWR_TEKST = {
    "Prawo": "w prawo",
    "Wprost": "na wprost",
    "Lewo": "w lewo",
    "Zawracający": "zawracając",
}


def _heading(wlot: str) -> int:
    return (BEARING[wlot] + 180) % 360


def _exit_bearing(wlot: str, manewr: str) -> int:
    if manewr == "Wprost":
        return _heading(wlot)
    if manewr == "Prawo":
        return (_heading(wlot) + 90) % 360
    if manewr == "Lewo":
        return (_heading(wlot) - 90) % 360
    if manewr == "Zawracający":
        return BEARING[wlot]
    raise ValueError(f"Nieznany manewr: {manewr}")


def opisz_relacje(wlot: str, manewr: str, geometria_regularna: bool) -> str:
    """§5.4: opis słowny relacji.

    Zawracający zawsze pomija klauzulę "na X" (wjazd i "wylot" wypadałyby na
    tę samą stronę świata, co dawałoby bezsensowne "na północ" przy wlocie
    z północy) — niezależnie od geometria_regularna. Dla pozostałych
    manewrów: geometria_regularna=False -> forma skrócona bez "na X"
    (generator nie zgaduje kierunku wylotu przy nieregularnej geometrii).
    """
    prefiks = PREFIKS_EUFONICZNY.get(wlot, "Z")
    manewr_tekst = MANEWR_TEKST[manewr]

    if manewr == "Zawracający" or not geometria_regularna:
        return f"{prefiks} {DOPELNIACZ[wlot]}, {manewr_tekst}"

    exit_wlot = REVERSE_BEARING[_exit_bearing(wlot, manewr)]
    return f"{prefiks} {DOPELNIACZ[wlot]} na {BIERNIK[exit_wlot]}, {manewr_tekst}"


_DIFF_NA_MANEWR = {0: "Zawracający", 90: "Lewo", 180: "Wprost", 270: "Prawo"}


def oblicz_manewr(wlot_wejscia: str, wlot_wyjscia: str) -> str:
    """Wyznacza manewr geometrycznie z pary wlot wjazdu + wlot wyjazdu (Etap 4
    krok 5 — model "bramka->wlot": pojedyncza litera z History/Quantity.csv to
    jedna fizyczna bramka/wlot, para np. "A-E" to obserwowana relacja; zamiast
    ręcznie klikać manewr dla każdej relacji, liczymy go z namiarów wlotów.

    Odwrotność `_exit_bearing()` wyżej — zweryfikowane, że dla każdej z 16
    kombinacji (wlot, manewr) z tamtej funkcji ta daje dokładnie ten sam wynik.
    """
    diff = (BEARING[wlot_wyjscia] - BEARING[wlot_wejscia]) % 360
    return _DIFF_NA_MANEWR[diff]


def klucz_sortowania(wlot: str, manewr: str) -> tuple[int, int]:
    return (WLOT_ORDER[wlot], MANEWR_ORDER[manewr])


def sortuj_relacje(relacje: list[dict]) -> list[dict]:
    return sorted(relacje, key=lambda r: klucz_sortowania(r["wlot"], r["manewr"]))
