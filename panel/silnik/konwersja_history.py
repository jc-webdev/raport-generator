"""Konwersja surowego eksportu History.csv (AISP, jeden wiersz = jedna
detekcja pojazdu) na zagregowany Quantity.csv (Kod relacji x Godzina x 12
kategorii) — to co wcześniej robiło ręczne makro VBA w Excelu.

Reguła potwierdzona z użytkownikiem: liczymy WYŁĄCZNIE wiersze gdzie
Validated == 1 — pozostałe wartości (np. 4, 5) to niepewne detekcje
wymagające ręcznej weryfikacji i nie wchodzą do zliczeń.

Kod relacji = pierwsza i ostatnia bramka (po zredukowaniu powtórzeń pod
rząd) z kolumny CrossSection — Python-list-string, np.
"['A', 'C', 'C', 'B']" -> redukcja powtórzeń -> ['A', 'C', 'B'] -> bierzemy
tylko pierwszy i ostatni element -> "A-B". Wiersze z <2 unikalnymi bramkami
po redukcji (CrossSection pusty, pojedyncza litera, albo sama powtórzona
litera) nie mają jednoznacznej relacji wlot->wylot i są pomijane.

Zweryfikowane na `dane-do-raportu/History.csv` + `dane-do-raportu/Quantity.csv`
(prawdziwa para wejście/wyjście) — patrz STAN-PRAC.md dla dokładnych liczb
i opisu rozbieżności (głównie ruch niezmotoryzowany, bo w przykładowych
danych większość detekcji rowerów/pieszych nie miała jeszcze Validated=1
w chwili eksportu, oraz ok. 6% wierszy z niepełnym śladem pojazdu — tylko
jedna bramka zarejestrowana zamiast dwóch).
"""
from __future__ import annotations

import ast

import pandas as pd

# a1.rowery/a3.hulajnogi/i1.piesi/i2.piesi.potrzeby -> nazwy kolumn Quantity.
# Pozostałe etykiety (b.moto, c.osobowe, c3.mikrobusy, d.dostawcze,
# e.ciezarowe, f.ciezarowe.z.naczepami, g.autobusy, h.rolne) już pasują 1:1.
MAPOWANIE_ETYKIET = {
    "a1.rowery": "rowery",
    "a3.hulajnogi": "hulajnogi",
    "i1.piesi": "pieszy",
    "i2.piesi.potrzeby": "pieszy potrzeby",
}

KATEGORIE_WSZYSTKIE = [
    "b.moto", "c.osobowe", "c3.mikrobusy", "d.dostawcze", "e.ciezarowe",
    "f.ciezarowe.z.naczepami", "g.autobusy", "h.rolne",
    "rowery", "hulajnogi", "pieszy", "pieszy potrzeby",
]


def _kod_z_cross_section(wartosc) -> str | None:
    """"['A', 'C', 'C', 'B']" -> zredukuj powtórzenia pod rząd -> ['A','C','B']
    -> weź pierwszą i ostatnią bramkę -> "A-B". None gdy <2 unikalne bramki."""
    if not isinstance(wartosc, str) or not wartosc.strip():
        return None
    try:
        bramki = ast.literal_eval(wartosc)
    except (ValueError, SyntaxError):
        return None

    zredukowane: list[str] = []
    for b in bramki:
        if not zredukowane or zredukowane[-1] != b:
            zredukowane.append(b)

    if len(zredukowane) < 2:
        return None
    return f"{zredukowane[0]}-{zredukowane[-1]}"


def konwertuj_history_na_quantity(df_history: pd.DataFrame) -> pd.DataFrame:
    """Zwraca DataFrame w kształcie Quantity.csv: kolumny Kod;Godz;<12
    kategorii>, jeden wiersz na (Kod, godzina) z policzonymi kategoriami.

    Godziny/Kody bez żadnego ruchu NIE są dogenerowywane jako wiersze
    zerowe — oryginalny plik Quantity.csv miał taki wiersz (Kod "F-C"
    wszędzie 0), ale lista "poprawnych" Kodów najwyraźniej pochodziła z
    konfiguracji spoza tego eksportu (np. arkusza z geometrią skrzyżowania),
    nie da się jej odtworzyć wyłącznie z History.csv — dalszy pipeline
    (mapowanie kierunków, krok 5) i tak działa na Kodach faktycznie
    obecnych w danych, więc brakujące zerowe wiersze nie zmieniają wyniku.
    """
    df = df_history[df_history["Validated"].astype(str) == "1"].copy()

    df["Kod"] = df["CrossSection"].map(_kod_z_cross_section)
    df = df.dropna(subset=["Kod"])

    df["Etykieta"] = df["Label"].map(lambda l: MAPOWANIE_ETYKIET.get(l, l))
    df["Godz"] = pd.to_datetime(df["Czas"]).dt.floor("h").dt.strftime("%Y-%m-%d %H:%M")

    pivot = (
        df.groupby(["Kod", "Godz", "Etykieta"])
        .size()
        .unstack("Etykieta", fill_value=0)
        .reindex(columns=KATEGORIE_WSZYSTKIE, fill_value=0)
        .reset_index()
        .sort_values(["Kod", "Godz"])
        .reset_index(drop=True)
    )
    return pivot[["Kod", "Godz"] + KATEGORIE_WSZYSTKIE]
