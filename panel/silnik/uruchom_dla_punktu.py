"""CLI: uruchamia silnik obliczeniowy (Etap 1) dla jednego punktu z
`projekt.json` panelu UI (Etap 4, krok 7).

Scala CSV wszystkich kamer punktu — z przesunięciem BRAMEK tak, jak w
`panel/ui/server.js::efektywneDanePunktu` (ta sama logika bazy-26,
przepisana 1:1 w Pythonie niżej, żeby wynik kroku 5 zgadzał się z tym co
faktycznie liczy silnik) — mapuje bramki na wloty (manewr liczony
geometrycznie, patrz opisy.oblicz_manewr) i woła oblicz_wszystko().

Użycie: python3 -m panel.silnik.uruchom_dla_punktu <sciezka_projekt.json> <numer_punktu>
Wypisuje JSON na stdout: {"obliczenia": {...}, "przypisyJakosciDanych": [...]}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from .mapowanie import wczytaj_surowe_csv, zmapuj_relacje_z_bramek
from .orkiestrator import oblicz_wszystko
from .przypisy import generuj_przypisy_jakosci


def indeks_na_litere(n: int) -> str:
    """Index (0-based) -> etykieta liter w stylu Excela (0=A,25=Z,26=AA,...).

    Musi być identyczna z `indeksNaLitere` w panel/ui/server.js.
    """
    etykieta = ""
    i = n + 1
    while i > 0:
        reszta = (i - 1) % 26
        etykieta = chr(65 + reszta) + etykieta
        i = (i - 1) // 26
    return etykieta


def przesun_bramke(bramka_surowa: str, przesuniecie: int) -> str:
    indeks_surowy = ord(bramka_surowa.strip().upper()[0]) - 65
    return indeks_na_litere(indeks_surowy + przesuniecie)


def przesun_relacje(relacja_surowa: str, przesuniecie: int) -> str:
    """"A-E" x przesunięcie -> "A'-E'" (obie bramki przesunięte niezależnie).
    Wartości bez myślnika (niepełny ślad) zwracane bez zmian — i tak
    zostaną odrzucone przez mapowanie.rozbij_relacje() w kroku dalej."""
    if "-" not in relacja_surowa:
        return relacja_surowa
    wejscie, _, wyjscie = relacja_surowa.partition("-")
    if not wejscie or not wyjscie:
        return relacja_surowa
    return f"{przesun_bramke(wejscie, przesuniecie)}-{przesun_bramke(wyjscie, przesuniecie)}"


def wczytaj_i_zmapuj_punkt(sciezka_projekt: Path, numer_punktu: int) -> tuple[dict, pd.DataFrame]:
    """Wspólne dla main() (obliczenia, krok 7) i eksportuj_relacje_synth.py
    (dane dla generate_flow_diagram.py, krok 11) — wczytuje CSV wszystkich
    kamer punktu, przesuwa bramki, mapuje na (wlot, manewr, Godzina, kategorie)."""
    projekt = json.loads(sciezka_projekt.read_text(encoding="utf-8"))
    punkt = next(p for p in projekt["punkty"] if p["numer"] == numer_punktu)
    dir_zrodla = sciezka_projekt.parent / "zrodla" / punkt["id"]

    ramki = []
    for kamera in punkt["kamery"]:
        df = wczytaj_surowe_csv(dir_zrodla / kamera["plikZrodlowy"])
        df["Kierunek"] = df["Kierunek"].apply(lambda l: przesun_relacje(l, kamera["przesuniecieLiter"]))
        ramki.append(df)
    df_raw = pd.concat(ramki, ignore_index=True)

    df_mapped = zmapuj_relacje_z_bramek(df_raw, punkt["bramkiMapping"])
    return punkt, df_mapped


def main() -> None:
    sciezka_projekt = Path(sys.argv[1])
    numer_punktu = int(sys.argv[2])

    punkt, df_mapped = wczytaj_i_zmapuj_punkt(sciezka_projekt, numer_punktu)
    wynik = oblicz_wszystko(df_mapped, punkt["geometriaRegularna"])

    przypisy = generuj_przypisy_jakosci(
        wynik["relacjeZNiezmotDostepne"],
        wynik["relacjeCiezkieEstymowane"],
        wynik["niezmotGodzinowoEstymowane"],
    )

    print(json.dumps({"obliczenia": wynik, "przypisyJakosciDanych": przypisy}))


if __name__ == "__main__":
    main()
