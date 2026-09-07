import pandas as pd

from panel.silnik.kategorie import KATEGORIE_WSZYSTKIE
from panel.silnik.obliczenia import (
    oblicz_godzinowa, oblicz_relacje_ciezkie, oblicz_relacje_sdr,
    oblicz_relacje_z_niezmot, oblicz_sdr_i_szczyt_dobowy, oblicz_strukture_rodzajowa,
)


def _buduj_df_mapped(wiersze):
    dane = []
    for wlot, manewr, godzina, wartosci in wiersze:
        wiersz = {"wlot": wlot, "manewr": manewr, "Godzina": godzina}
        wiersz.update({k: 0 for k in KATEGORIE_WSZYSTKIE})
        wiersz.update(wartosci)
        dane.append(wiersz)
    return pd.DataFrame(dane)


def test_niezmot_zerowane():
    # Jak fixture happy-path, ale niezmot = 0 we wszystkich godzinach.
    df = _buduj_df_mapped([
        ("PN", "Wprost", 0, {"c.osobowe": 10}),
        ("ZACH", "Prawo", 0, {"c.osobowe": 5}),
        ("PN", "Wprost", 7, {"c.osobowe": 50, "d.dostawcze": 5, "e.ciezarowe": 3}),
        ("ZACH", "Prawo", 7, {"c.osobowe": 20, "e.ciezarowe": 1}),
        ("PN", "Wprost", 15, {"c.osobowe": 80, "f.ciezarowe.z.naczepami": 1, "g.autobusy": 2}),
        ("ZACH", "Prawo", 15, {"c.osobowe": 30, "f.ciezarowe.z.naczepami": 2}),
    ])
    sdr, _ = oblicz_sdr_i_szczyt_dobowy(df)  # 209, jak w happy path
    relacje_sdr = oblicz_relacje_sdr(df, sdr, True)

    relacje, dostepne = oblicz_relacje_z_niezmot(df, relacje_sdr, suma_dobowa_niezmot=40)
    assert relacje == []
    assert dostepne is False

    godzinowa, estymowane = oblicz_godzinowa(df, sdr, suma_dobowa_niezmot=40)
    assert estymowane is True
    by_h = {w["godzina"]: w for w in godzinowa}
    assert by_h["00:00"]["niezmotoryzowany"] == 3   # round(40*15/209)
    assert by_h["07:00"]["niezmotoryzowany"] == 15  # round(40*79/209)
    assert by_h["15:00"]["niezmotoryzowany"] == 22  # round(40*115/209)
    assert sum(w["niezmotoryzowany"] for w in godzinowa) == 40


def test_ciezkie_zerowane():
    # Jak fixture happy-path, ale bez kolumn e/f (ciężkie = 0 wszędzie).
    df = _buduj_df_mapped([
        ("PN", "Wprost", 0, {"c.osobowe": 10}),
        ("ZACH", "Prawo", 0, {"c.osobowe": 5}),
        ("PN", "Wprost", 7, {"c.osobowe": 50, "d.dostawcze": 5, "rowery": 2}),
        ("ZACH", "Prawo", 7, {"c.osobowe": 20, "rowery": 1}),
        ("PN", "Wprost", 15, {"c.osobowe": 80, "g.autobusy": 2, "pieszy": 5}),
        ("ZACH", "Prawo", 15, {"c.osobowe": 30}),
    ])
    sdr, _ = oblicz_sdr_i_szczyt_dobowy(df)
    assert sdr == 202
    relacje_sdr = oblicz_relacje_sdr(df, sdr, True)
    assert relacje_sdr[0]["sdr"] == 147
    assert relacje_sdr[1]["sdr"] == 55

    relacje, estymowane = oblicz_relacje_ciezkie(df, relacje_sdr, suma_dobowa_ciezkie=21)
    assert estymowane is True
    assert len(relacje) == 2  # NIE pomijane, w przeciwieństwie do niezmot.
    assert relacje[0]["suma"] == 15  # round(21*147/202)
    assert relacje[1]["suma"] == 6   # round(21*55/202)

    from panel.silnik.obliczenia import oblicz_upc
    upc = oblicz_upc(relacje_sdr, relacje)
    assert upc[0]["upc"] == 10.2  # round(15/147*100, 1)
    assert upc[1]["upc"] == 10.9  # round(6/55*100, 1)


def test_t_skrzyzowanie_niepelna_liczba_relacji():
    df = _buduj_df_mapped([
        ("PN", "Wprost", 7, {"c.osobowe": 40}),
        ("WSCH", "Prawo", 7, {"c.osobowe": 10}),
        ("PD", "Lewo", 7, {"c.osobowe": 15}),
    ])
    sdr, _ = oblicz_sdr_i_szczyt_dobowy(df)
    relacje = oblicz_relacje_sdr(df, sdr, geometria_regularna=False)

    assert len(relacje) == 3
    assert [r["wlot"] for r in relacje] == ["PN", "WSCH", "PD"]
    # geometria_regularna=False -> brak klauzuli "na X"
    assert relacje[0]["opis"] == "Z północy, na wprost"
    assert relacje[1]["opis"] == "Ze wschodu, w prawo"
    assert relacje[2]["opis"] == "Z południa, w lewo"

    # Tabele o stałym kształcie nie zależą od liczby relacji.
    struktura, suma_cala = oblicz_strukture_rodzajowa(df, sdr)
    assert len(struktura) == 12
    godzinowa, _ = oblicz_godzinowa(df, sdr)
    assert len(godzinowa) == 24
