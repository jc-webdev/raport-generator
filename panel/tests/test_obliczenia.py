import pandas as pd

from panel.silnik.kategorie import KATEGORIE_WSZYSTKIE
from panel.silnik.obliczenia import (
    oblicz_godzinowa, oblicz_pory_doby, oblicz_relacje_ciezkie, oblicz_relacje_sdr,
    oblicz_relacje_z_niezmot, oblicz_sdr_i_szczyt_dobowy, oblicz_strukture_rodzajowa,
    oblicz_szczyty_okna_stale, oblicz_upc,
)


def _buduj_df_mapped(wiersze):
    """wiersze: list of (wlot, manewr, godzina, {kolumna: wartosc})."""
    dane = []
    for wlot, manewr, godzina, wartosci in wiersze:
        wiersz = {"wlot": wlot, "manewr": manewr, "Godzina": godzina}
        wiersz.update({k: 0 for k in KATEGORIE_WSZYSTKIE})
        wiersz.update(wartosci)
        dane.append(wiersz)
    return pd.DataFrame(dane)


def _fixture_happy_path():
    return _buduj_df_mapped([
        ("PN", "Wprost", 0, {"c.osobowe": 10}),
        ("ZACH", "Prawo", 0, {"c.osobowe": 5}),
        ("PN", "Wprost", 7, {"c.osobowe": 50, "d.dostawcze": 5, "e.ciezarowe": 3, "rowery": 2}),
        ("ZACH", "Prawo", 7, {"c.osobowe": 20, "e.ciezarowe": 1, "rowery": 1}),
        ("PN", "Wprost", 15, {"c.osobowe": 80, "f.ciezarowe.z.naczepami": 1, "g.autobusy": 2, "pieszy": 5}),
        ("ZACH", "Prawo", 15, {"c.osobowe": 30, "f.ciezarowe.z.naczepami": 2}),
    ])


def test_sdr_i_szczyt_dobowy():
    df = _fixture_happy_path()
    sdr, szczyt = oblicz_sdr_i_szczyt_dobowy(df)
    assert sdr == 209
    assert szczyt == {"wartosc": 115, "godzina": "15:00"}


def test_relacje_sdr():
    df = _fixture_happy_path()
    sdr, _ = oblicz_sdr_i_szczyt_dobowy(df)
    relacje = oblicz_relacje_sdr(df, sdr, geometria_regularna=True)

    assert [r["wlot"] for r in relacje] == ["PN", "ZACH"]

    pn = relacje[0]
    assert pn["manewr"] == "Wprost"
    assert pn["sdr"] == 151
    assert pn["udzial"] == 72.2
    assert pn["szczyt"] == 83
    assert pn["godzinaSzczytu"] == "15:00"
    assert pn["opis"] == "Z północy na południe, na wprost"

    zach = relacje[1]
    assert zach["sdr"] == 58
    assert zach["udzial"] == 27.8
    assert zach["szczyt"] == 32
    assert zach["opis"] == "Z zachodu na południe, w prawo"


def test_relacje_z_niezmot_happy_path():
    df = _fixture_happy_path()
    sdr, _ = oblicz_sdr_i_szczyt_dobowy(df)
    relacje_sdr = oblicz_relacje_sdr(df, sdr, True)

    relacje, dostepne = oblicz_relacje_z_niezmot(df, relacje_sdr)
    assert dostepne is True
    assert relacje[0]["suma"] == 158  # 151 + (2 rowery + 5 pieszy)
    assert relacje[0]["udzial"] == 72.8
    assert relacje[1]["suma"] == 59  # 58 + 1 rower
    assert relacje[1]["udzial"] == 27.2


def test_relacje_ciezkie_happy_path():
    df = _fixture_happy_path()
    sdr, _ = oblicz_sdr_i_szczyt_dobowy(df)
    relacje_sdr = oblicz_relacje_sdr(df, sdr, True)

    relacje, estymowane = oblicz_relacje_ciezkie(df, relacje_sdr)
    assert estymowane is False
    assert relacje[0]["suma"] == 4  # 3 e.ciezarowe + 1 f.ciezarowe.z.naczepami
    assert relacje[1]["suma"] == 3  # 1 e.ciezarowe + 2 f.ciezarowe.z.naczepami
    assert relacje[0]["udzial"] == 57.1
    assert relacje[1]["udzial"] == 42.9


def test_upc_happy_path():
    df = _fixture_happy_path()
    sdr, _ = oblicz_sdr_i_szczyt_dobowy(df)
    relacje_sdr = oblicz_relacje_sdr(df, sdr, True)
    relacje_ciezkie, _ = oblicz_relacje_ciezkie(df, relacje_sdr)

    upc = oblicz_upc(relacje_sdr, relacje_ciezkie)
    assert upc[0]["upc"] == 2.6  # round(4/151*100, 1)
    assert upc[1]["upc"] == 5.2  # round(3/58*100, 1)


def test_godzinowa_happy_path():
    df = _fixture_happy_path()
    sdr, _ = oblicz_sdr_i_szczyt_dobowy(df)

    godzinowa, estymowane = oblicz_godzinowa(df, sdr)
    assert estymowane is False
    by_h = {w["godzina"]: w for w in godzinowa}

    assert len(godzinowa) == 24
    assert by_h["00:00"]["zmotoryzowany"] == 15
    assert by_h["00:00"]["udzialZmot"] == 7.2
    assert by_h["07:00"]["zmotoryzowany"] == 79
    assert by_h["07:00"]["udzialZmot"] == 37.8
    assert by_h["07:00"]["niezmotoryzowany"] == 3
    assert by_h["07:00"]["udzialNiezmot"] == 37.5
    assert by_h["15:00"]["zmotoryzowany"] == 115
    assert by_h["15:00"]["udzialZmot"] == 55.0
    assert by_h["15:00"]["niezmotoryzowany"] == 5
    assert by_h["15:00"]["udzialNiezmot"] == 62.5
    assert by_h["01:00"]["zmotoryzowany"] == 0
    assert by_h["01:00"]["udzialZmot"] == 0.0


def test_pory_doby_happy_path():
    df = _fixture_happy_path()
    pory = oblicz_pory_doby(df)
    assert pory == {"dzien": [194, 92.8], "noc": [15, 7.2]}


def test_szczyty_okna_stale_happy_path():
    df = _fixture_happy_path()
    poranne, popoludniowe = oblicz_szczyty_okna_stale(df)
    assert poranne == {"wartosc": 79, "zakres": "07:00-08:00"}
    assert popoludniowe == {"wartosc": 115, "zakres": "15:00-16:00"}


def test_struktura_rodzajowa_happy_path():
    df = _fixture_happy_path()
    sdr, _ = oblicz_sdr_i_szczyt_dobowy(df)
    struktura, suma_cala = oblicz_strukture_rodzajowa(df, sdr)

    by_kat = {w["kategoria"]: w for w in struktura}
    assert suma_cala == 217

    assert by_kat["Osobowe"]["suma"] == 195
    assert by_kat["Osobowe"]["udzialZmotoryzowane"] == 93.3
    assert by_kat["Osobowe"]["udzialCale"] == 89.9

    assert by_kat["Ciężarowe"]["suma"] == 4
    assert by_kat["Ciężarowe z naczepami"]["suma"] == 3
    assert by_kat["Dostawcze"]["suma"] == 5
    assert by_kat["Autobusy"]["suma"] == 2
    assert by_kat["Mikrobusy"]["suma"] == 0

    assert by_kat["Rowery"]["suma"] == 3
    assert by_kat["Rowery"]["udzialZmotoryzowane"] is None
    assert by_kat["Rowery"]["udzialCale"] == 1.4
    assert by_kat["Piesi"]["suma"] == 5
    assert by_kat["Piesi"]["udzialCale"] == 2.3
