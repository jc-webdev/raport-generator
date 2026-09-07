"""Testy generatora tekstów bez AI (Etap 4, krok 8/9) — pokrywają gałęzie
decyzyjne (korytarzowy vs rozproszony rozkład ruchu, wysoki vs niski udział
niezmotoryzowanych, obecność/brak przypisów jakości), nie każdą kombinację.
"""
from panel.silnik.teksty import (
    tekst_komentarz_analityczny,
    tekst_lokalizacja,
    tekst_organizacja_ruchu,
    tekst_pory_doby,
    tekst_ruch_ciezkich,
    tekst_ruch_wg_kierunkow,
    tekst_struktura_rodzajowa,
)

RELACJE_KORYTARZOWE = [
    {"wlot": "WSCH", "manewr": "Wprost", "opis": "Ze wschodu na zachód, na wprost",
     "sdr": 12300, "udzial": 43.1, "szczyt": 937, "godzinaSzczytu": "07:00"},
    {"wlot": "ZACH", "manewr": "Wprost", "opis": "Z zachodu na wschód, na wprost",
     "sdr": 13031, "udzial": 45.6, "szczyt": 1147, "godzinaSzczytu": "16:00"},
    {"wlot": "PN", "manewr": "Lewo", "opis": "Z północy na wschód, w lewo",
     "sdr": 615, "udzial": 2.2, "szczyt": 70, "godzinaSzczytu": "07:00"},
]

RELACJE_ROZPROSZONE = [
    {"wlot": "ZACH", "manewr": "Prawo", "opis": "Z zachodu na południe, w prawo",
     "sdr": 6024, "udzial": 19.3, "szczyt": 492, "godzinaSzczytu": "16:00"},
    {"wlot": "PN", "manewr": "Wprost", "opis": "Z północy na południe, na wprost",
     "sdr": 4816, "udzial": 15.4, "szczyt": 347, "godzinaSzczytu": "14:00"},
]


def test_organizacja_ruchu_korytarzowy_przy_dominacji_wprost():
    tekst = tekst_organizacja_ruchu(RELACJE_KORYTARZOWE, 28558)
    assert "korytarzowy" in tekst
    assert "88" in tekst  # (12300+13031)/28558 ≈ 88.9%


def test_organizacja_ruchu_rozproszony_bez_dominacji_wprost():
    tekst = tekst_organizacja_ruchu(RELACJE_ROZPROSZONE, 31185)
    assert "Dominującą pojedynczą relacją" in tekst
    assert "z zachodu na południe, w prawo" in tekst


def test_ruch_wg_kierunkow_wymienia_top_relacje_i_ich_udzial():
    tekst = tekst_ruch_wg_kierunkow(RELACJE_KORYTARZOWE)
    assert "45,6%" in tekst and "43,1%" in tekst


def test_ruch_wg_kierunkow_pojedyncza_relacja_uzywa_liczby_pojedynczej():
    tekst = tekst_ruch_wg_kierunkow([RELACJE_ROZPROSZONE[0]])
    assert "w 1 relacji" in tekst
    assert "relacjach" not in tekst


def test_ruch_ciezkich_wyroznia_relacje_z_wysokim_upc():
    upc = [{"opis": "Ze wschodu na zachód, na wprost", "upc": 18.8},
           {"opis": "Z północy na wschód, w lewo", "upc": 0.2}]
    tekst = tekst_ruch_ciezkich(RELACJE_KORYTARZOWE, upc, 1694, 31185)
    assert "ze wschodu na zachód, na wprost" in tekst
    assert "18,8%" in tekst


def test_pory_doby_zawiera_dokladne_liczby():
    tekst = tekst_pory_doby({"dzien": [29163, 93.5], "noc": [2022, 6.5]})
    assert "93,5%" in tekst and "29 163" in tekst and "6,5%" in tekst


def test_struktura_rodzajowa_wysoki_udzial_niezmotoryzowanych():
    struktura = [
        {"kategoria": "Osobowe", "udzialCale": 75.9},
        {"kategoria": "Rowery", "udzialCale": 8.3},
        {"kategoria": "Piesi", "udzialCale": 6.4},
    ]
    tekst = tekst_struktura_rodzajowa(struktura)
    assert "wysoki udział ruchu nie zmotoryzowanego" in tekst


def test_struktura_rodzajowa_maly_udzial_niezmotoryzowanych():
    struktura = [
        {"kategoria": "Osobowe", "udzialCale": 83.0},
        {"kategoria": "Rowery", "udzialCale": 1.2},
        {"kategoria": "Piesi", "udzialCale": 0.2},
    ]
    tekst = tekst_struktura_rodzajowa(struktura)
    assert "udziałowo mały" in tekst


def test_komentarz_wymienia_liczbe_przypisow_jakosci():
    struktura = [{"kategoria": "Osobowe", "udzialCale": 83.0}]
    tekst = tekst_komentarz_analityczny(
        28558, {"wartosc": 2285, "godzina": "15:00"}, RELACJE_KORYTARZOWE, struktura,
        [{"kotwica": "T4", "tresc": "..."}, {"kotwica": "T5", "tresc": "..."}],
    )
    assert "2 zastrzeżenia jakościowe" in tekst


def test_komentarz_brak_przypisow_jakosci():
    struktura = [{"kategoria": "Osobowe", "udzialCale": 83.0}]
    tekst = tekst_komentarz_analityczny(
        28558, {"wartosc": 2285, "godzina": "15:00"}, RELACJE_KORYTARZOWE, struktura, [],
    )
    assert "Brak istotnych zastrzeżeń jakościowych" in tekst


def test_lokalizacja_nie_odmienia_nazwy_miejscowosci():
    # "w miejscowości Toruń" (nie "w Toruniu") — deklinacja nazw miast jest
    # niedeterministyczna bez słownika odmian, patrz komentarz w teksty.py.
    wloty = [{"id": "PN", "opis": "ul. Stawki (od północy)"}, {"id": "WSCH", "opis": "ul. Szuwarów (od wschodu)"}]
    tekst = tekst_lokalizacja("Skrzyżowanie Stawki / Szuwarów", "Toruń", wloty, False)
    assert "w miejscowości Toruń" in tekst
    assert "geometria nietypowa" in tekst
