"""CLI: generuje `wynik_tabele_Punkt{N}_{ID}.xlsx` — załącznik, który raport
Word (`panel/docx/budujPunkt.js`) obiecuje w tekście ("Pełna godzinowa
struktura rodzajowa ruchu dostępna jest wyłącznie w załączonym pliku xlsx"),
ale do tej pory nigdzie nie był faktycznie generowany.

Arkusze (nazwy i kolumny wg `raport-reguly-obliczen-i-danych.md` §1):
- "Parametry pomiaru" — metadane (jak Tabela 3.n.1 w raporcie)
- "Ruch wg kierunkow" — zestawienie relacji SDR (jak Tabela 3.n.3)
- "Pory doby" — dzień/noc (jak Tabela 3.n.6)
- "Struktura rodzajowa" — 12 kategorii (jak Tabela 3.n.7)
- "Godzinowa szczegolowa" — GŁÓWNY arkusz: (Wlot, Kierunek, Godz + 12 kategorii),
  jeden wiersz na (wlot, manewr, godzina) — to jest dokładnie to, czego tekst
  raportu każe szukać "wyłącznie w załączonym pliku xlsx" (setki wierszy,
  za dużo żeby wstawiać w treść Worda).

Użycie: python3 -m panel.silnik.eksportuj_wynik_tabele <projekt.json> <numer_punktu> <output.xlsx>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from .kategorie import KATEGORIE_WSZYSTKIE
from .opisy import opisz_relacje
from .uruchom_dla_punktu import wczytaj_i_zmapuj_punkt


def main() -> None:
    sciezka_projekt = Path(sys.argv[1])
    numer_punktu = int(sys.argv[2])
    sciezka_xlsx = Path(sys.argv[3])

    punkt, df_mapped = wczytaj_i_zmapuj_punkt(sciezka_projekt, numer_punktu)
    o = punkt["obliczenia"]
    if not o:
        raise SystemExit("Brak obliczeń dla tego punktu — najpierw krok 7.")

    parametry = pd.DataFrame([
        {"Parametr": "ID", "Wartość": punkt["id"]},
        {"Parametr": "Nazwa", "Wartość": punkt["nazwa"]},
        {"Parametr": "Data pomiaru", "Wartość": punkt["metadanePomiaru"]["dataPomiaru"]},
        {"Parametr": "Dzień tygodnia", "Wartość": punkt["metadanePomiaru"]["dzienTygodnia"]},
        {"Parametr": "Warunki atmosferyczne", "Wartość": punkt["metadanePomiaru"]["warunkiAtmosferyczne"]},
        {"Parametr": "SDR", "Wartość": f"{o['sdr']} poj./dobę"},
        {"Parametr": "Szczyt dobowy", "Wartość": f"{o['szczytDobowy']['wartosc']} poj./h o {o['szczytDobowy']['godzina']}"},
    ])

    relacje = pd.DataFrame(o["relacjeSDR"])[["opis", "sdr", "udzial", "szczyt", "godzinaSzczytu"]]
    relacje.columns = ["Opis relacji", "SDR [poj./dobę]", "Udział w SDR [%]", "Szczyt [poj./h]", "Godz. szczytu"]

    pory = pd.DataFrame([
        {"Pora": "Dzień (06:00-22:00)", "Suma [poj.]": o["poryDoby"]["dzien"][0], "Udział [%]": o["poryDoby"]["dzien"][1]},
        {"Pora": "Noc (22:00-06:00)", "Suma [poj.]": o["poryDoby"]["noc"][0], "Udział [%]": o["poryDoby"]["noc"][1]},
    ])

    struktura = pd.DataFrame(o["strukturaRodzajowa"])[["kategoria", "suma", "udzialZmotoryzowane", "udzialCale"]]
    struktura.columns = ["Kategoria", "Suma [poj./dobę]", "Udział zmotoryzowane [%]", "Udział całe [%]"]

    godzinowa = df_mapped.copy()
    godzinowa["Opis relacji"] = [
        opisz_relacje(w, m, punkt["geometriaRegularna"]) for w, m in zip(godzinowa["wlot"], godzinowa["manewr"])
    ]
    godzinowa["Godz"] = godzinowa["Godzina"].apply(lambda h: f"{h:02d}:00")
    godzinowa = godzinowa.rename(columns={"wlot": "Wlot", "manewr": "Kierunek"})
    godzinowa = godzinowa[["Wlot", "Kierunek", "Opis relacji", "Godz"] + KATEGORIE_WSZYSTKIE]
    godzinowa = godzinowa.sort_values(["Wlot", "Kierunek", "Godz"]).reset_index(drop=True)

    sciezka_xlsx.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(sciezka_xlsx, engine="openpyxl") as writer:
        parametry.to_excel(writer, sheet_name="Parametry pomiaru", index=False)
        relacje.to_excel(writer, sheet_name="Ruch wg kierunkow", index=False)
        pory.to_excel(writer, sheet_name="Pory doby", index=False)
        struktura.to_excel(writer, sheet_name="Struktura rodzajowa", index=False)
        godzinowa.to_excel(writer, sheet_name="Godzinowa szczegolowa", index=False)

    print(json.dumps({"ok": True, "sciezka": str(sciezka_xlsx), "wierszyGodzinowych": len(godzinowa)}))


if __name__ == "__main__":
    main()
