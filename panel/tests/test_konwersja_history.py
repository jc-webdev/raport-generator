import pandas as pd

from panel.silnik.konwersja_history import konwertuj_history_na_quantity


def _wiersz(czas, kierunek_lista, validated, label):
    return {
        "Czas": czas, "CrossSection": str(kierunek_lista), "Validated": str(validated), "Label": label,
    }


def test_filtruje_tylko_validated_1():
    df = pd.DataFrame([
        _wiersz("2026-05-28 07:15:00", ["A", "B"], 1, "c.osobowe"),
        _wiersz("2026-05-28 07:20:00", ["A", "B"], 4, "c.osobowe"),  # niepewny, pominięty
        _wiersz("2026-05-28 07:25:00", ["A", "B"], 5, "c.osobowe"),  # niepewny, pominięty
    ])
    wynik = konwertuj_history_na_quantity(df)
    assert len(wynik) == 1
    assert wynik.iloc[0]["c.osobowe"] == 1


def test_redukuje_powtorzenia_i_bierze_pierwsza_ostatnia_bramke():
    df = pd.DataFrame([
        _wiersz("2026-05-28 07:15:00", ["A", "C", "C", "B"], 1, "c.osobowe"),
    ])
    wynik = konwertuj_history_na_quantity(df)
    assert wynik.iloc[0]["Kod"] == "A-B"


def test_pomija_wiersze_z_niejednoznaczna_relacja():
    df = pd.DataFrame([
        _wiersz("2026-05-28 07:15:00", ["A"], 1, "c.osobowe"),       # jedna bramka
        _wiersz("2026-05-28 07:16:00", [], 1, "c.osobowe"),          # pusty ślad
        _wiersz("2026-05-28 07:17:00", ["A", "A"], 1, "c.osobowe"),  # sama powtórzona bramka
    ])
    wynik = konwertuj_history_na_quantity(df)
    assert len(wynik) == 0


def test_mapuje_etykiety_niezmotoryzowane_na_nazwy_kolumn_quantity():
    df = pd.DataFrame([
        _wiersz("2026-05-28 07:15:00", ["A", "B"], 1, "a1.rowery"),
        _wiersz("2026-05-28 07:16:00", ["A", "B"], 1, "a3.hulajnogi"),
        _wiersz("2026-05-28 07:17:00", ["A", "B"], 1, "i1.piesi"),
        _wiersz("2026-05-28 07:18:00", ["A", "B"], 1, "i2.piesi.potrzeby"),
    ])
    wynik = konwertuj_history_na_quantity(df)
    assert len(wynik) == 1
    wiersz = wynik.iloc[0]
    assert wiersz["rowery"] == 1
    assert wiersz["hulajnogi"] == 1
    assert wiersz["pieszy"] == 1
    assert wiersz["pieszy potrzeby"] == 1


def test_grupuje_po_godzinie_nie_po_minucie():
    df = pd.DataFrame([
        _wiersz("2026-05-28 07:05:00", ["A", "B"], 1, "c.osobowe"),
        _wiersz("2026-05-28 07:55:00", ["A", "B"], 1, "c.osobowe"),
        _wiersz("2026-05-28 08:05:00", ["A", "B"], 1, "c.osobowe"),
    ])
    wynik = konwertuj_history_na_quantity(df)
    assert len(wynik) == 2
    assert set(wynik["Godz"]) == {"2026-05-28 07:00", "2026-05-28 08:00"}
    wiersz_7 = wynik[wynik["Godz"] == "2026-05-28 07:00"].iloc[0]
    assert wiersz_7["c.osobowe"] == 2


def test_kolejnosc_kolumn_zgodna_z_prawdziwym_quantity_csv():
    df = pd.DataFrame([_wiersz("2026-05-28 07:15:00", ["A", "B"], 1, "c.osobowe")])
    wynik = konwertuj_history_na_quantity(df)
    assert list(wynik.columns) == [
        "Kod", "Godz", "b.moto", "c.osobowe", "c3.mikrobusy", "d.dostawcze",
        "e.ciezarowe", "f.ciezarowe.z.naczepami", "g.autobusy", "h.rolne",
        "rowery", "hulajnogi", "pieszy", "pieszy potrzeby",
    ]
