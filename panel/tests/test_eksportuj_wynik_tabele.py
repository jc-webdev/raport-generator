import json

import pandas as pd

from panel.silnik.eksportuj_wynik_tabele import main as eksportuj_main


def _zbuduj_projekt_testowy(tmp_path):
    """Minimalny punkt z 1 kamerą (2 relacje, 2 godziny) i już policzonymi
    `obliczenia` (jak po kroku 7) — eksporter czyta oba (df_mapped na nowo z
    CSV + obliczenia z projekt.json), więc oba muszą być spójne."""
    dir_zrodla = tmp_path / "zrodla" / "P1"
    dir_zrodla.mkdir(parents=True)
    (dir_zrodla / "quantity.csv").write_text(
        "Kod;Godz;b.moto;c.osobowe;c3.mikrobusy;d.dostawcze;e.ciezarowe;"
        "f.ciezarowe.z.naczepami;g.autobusy;h.rolne;rowery;hulajnogi;pieszy;pieszy potrzeby\n"
        "A-B;2026-05-28 07:00;0;10;0;0;0;0;0;0;0;0;0;0\n"
        "B-A;2026-05-28 08:00;0;5;0;0;0;0;0;0;0;0;0;0\n",
        encoding="utf-8",
    )
    projekt = {
        "punkty": [{
            "numer": 1, "id": "P1", "nazwa": "Testowe skrzyżowanie",
            "metadanePomiaru": {
                "dataPomiaru": "2026-05-28", "dzienTygodnia": "Czwartek",
                "warunkiAtmosferyczne": "bez opadów, +15°C",
            },
            "kamery": [{"plikZrodlowy": "quantity.csv", "przesuniecieLiter": 0}],
            "bramkiMapping": {"A": "PN", "B": "PD"},
            "geometriaRegularna": True,
            "obliczenia": {
                "sdr": 15,
                "szczytDobowy": {"wartosc": 10, "godzina": "07:00"},
                "relacjeSDR": [
                    {"wlot": "PN", "manewr": "Wprost", "opis": "Z północy na południe, na wprost", "sdr": 10, "udzial": 66.7, "szczyt": 10, "godzinaSzczytu": "07:00"},
                    {"wlot": "PD", "manewr": "Wprost", "opis": "Z południa na północ, na wprost", "sdr": 5, "udzial": 33.3, "szczyt": 5, "godzinaSzczytu": "08:00"},
                ],
                "poryDoby": {"dzien": [15, 100.0], "noc": [0, 0.0]},
                "strukturaRodzajowa": [
                    {"kategoria": "Osobowe", "suma": 15, "udzialZmotoryzowane": 100.0, "udzialCale": 100.0},
                ],
            },
        }],
    }
    sciezka_projekt = tmp_path / "projekt.json"
    sciezka_projekt.write_text(json.dumps(projekt), encoding="utf-8")
    return sciezka_projekt


def test_generuje_wszystkie_pieta_arkuszy(tmp_path, monkeypatch):
    sciezka_projekt = _zbuduj_projekt_testowy(tmp_path)
    sciezka_xlsx = tmp_path / "wynik_tabele_Punkt1_P1.xlsx"

    monkeypatch.setattr("sys.argv", ["prog", str(sciezka_projekt), "1", str(sciezka_xlsx)])
    eksportuj_main()

    assert sciezka_xlsx.exists()
    xl = pd.ExcelFile(sciezka_xlsx)
    assert xl.sheet_names == [
        "Parametry pomiaru", "Ruch wg kierunkow", "Pory doby",
        "Struktura rodzajowa", "Godzinowa szczegolowa",
    ]


def test_godzinowa_szczegolowa_ma_opis_relacji_i_poprawne_kolumny(tmp_path, monkeypatch):
    sciezka_projekt = _zbuduj_projekt_testowy(tmp_path)
    sciezka_xlsx = tmp_path / "wynik.xlsx"
    monkeypatch.setattr("sys.argv", ["prog", str(sciezka_projekt), "1", str(sciezka_xlsx)])
    eksportuj_main()

    godzinowa = pd.ExcelFile(sciezka_xlsx).parse("Godzinowa szczegolowa")
    assert list(godzinowa.columns[:4]) == ["Wlot", "Kierunek", "Opis relacji", "Godz"]
    assert len(godzinowa) == 2
    assert set(godzinowa["Opis relacji"]) == {"Z północy na południe, na wprost", "Z południa na północ, na wprost"}
    assert set(godzinowa["Godz"]) == {"07:00", "08:00"}
