import pandas as pd

from panel.silnik.mapowanie import (
    rozbij_relacje, waliduj_bramki, waliduj_litery, wczytaj_surowe_csv,
    wykryj_duplikaty, zmapuj_kierunki, zmapuj_relacje_z_bramek,
)


def _df_raw(wiersze):
    kolumny_kat = [
        "b.moto", "c.osobowe", "c3.mikrobusy", "d.dostawcze", "e.ciezarowe",
        "f.ciezarowe.z.naczepami", "g.autobusy", "h.rolne",
        "rowery", "hulajnogi", "pieszy", "pieszy potrzeby",
    ]
    dane = []
    for litera, godzina, wartosci in wiersze:
        wiersz = {"Kierunek": litera, "Godzina": godzina}
        wiersz.update({k: 0 for k in kolumny_kat})
        wiersz.update(wartosci)
        dane.append(wiersz)
    return pd.DataFrame(dane)


def test_waliduj_litery_wykrywa_niezmapowane():
    df = _df_raw([("A", 7, {}), ("Z", 7, {})])
    mapping = {"A": {"wlot": "PN", "manewr": "Wprost"}}
    assert waliduj_litery(df, mapping) == ["Z"]


def test_waliduj_litery_pusta_gdy_wszystko_ok():
    df = _df_raw([("A", 7, {})])
    mapping = {"A": {"wlot": "PN", "manewr": "Wprost"}}
    assert waliduj_litery(df, mapping) == []


def test_wykryj_duplikaty():
    mapping = {
        "K": {"wlot": "PN", "manewr": "Wprost"},
        "L": {"wlot": "PN", "manewr": "Wprost"},
        "A": {"wlot": "PD", "manewr": "Prawo"},
    }
    duplikaty = wykryj_duplikaty(mapping)
    assert duplikaty == [{
        "wlot": "PN", "manewr": "Wprost", "litery": ["K", "L"],
        "sugerowanaAkcja": "scal w jedną relację (suma po kluczu wlot+manewr)",
    }]


def test_zmapuj_kierunki_scala_duplikaty():
    mapping = {
        "K": {"wlot": "PN", "manewr": "Wprost"},
        "L": {"wlot": "PN", "manewr": "Wprost"},
    }
    df_raw = _df_raw([
        ("K", 7, {"c.osobowe": 10}),
        ("L", 7, {"c.osobowe": 15}),
    ])
    zmapowane = zmapuj_kierunki(df_raw, mapping)
    assert len(zmapowane) == 1
    wiersz = zmapowane.iloc[0]
    assert wiersz["wlot"] == "PN"
    assert wiersz["manewr"] == "Wprost"
    assert wiersz["Godzina"] == 7
    assert wiersz["c.osobowe"] == 25


# --- Model "bramka -> wlot" (prawdziwy format History/Quantity, Etap 4 krok 5) --

def test_rozbij_relacje():
    assert rozbij_relacje("A-E") == ("A", "E")
    assert rozbij_relacje("A") is None  # niepełny ślad, brak myślnika
    assert rozbij_relacje("") is None
    assert rozbij_relacje(None) is None


def test_waliduj_bramki_wykrywa_niezmapowane():
    df = _df_raw([("A-E", 7, {}), ("A-Z", 7, {})])
    assert waliduj_bramki(df, {"A": "PN", "E": "WSCH"}) == ["Z"]


def test_waliduj_bramki_pusta_gdy_wszystko_ok():
    df = _df_raw([("A-E", 7, {})])
    assert waliduj_bramki(df, {"A": "PN", "E": "WSCH"}) == []


def test_zmapuj_relacje_z_bramek_liczy_manewr_z_geometrii():
    # A=PN, E=WSCH -> wjazd z północy, wyjazd na wschód = w lewo (patrz test_opisy.py)
    mapowanie_bramek = {"A": "PN", "E": "WSCH"}
    df_raw = _df_raw([("A-E", 7, {"c.osobowe": 10})])
    zmapowane = zmapuj_relacje_z_bramek(df_raw, mapowanie_bramek)
    assert len(zmapowane) == 1
    wiersz = zmapowane.iloc[0]
    assert wiersz["wlot"] == "PN"
    assert wiersz["manewr"] == "Lewo"
    assert wiersz["c.osobowe"] == 10


def test_zmapuj_relacje_z_bramek_pomija_niepelny_slad():
    mapowanie_bramek = {"A": "PN", "E": "WSCH"}
    df_raw = _df_raw([("A-E", 7, {"c.osobowe": 10}), ("A", 7, {"c.osobowe": 99})])
    zmapowane = zmapuj_relacje_z_bramek(df_raw, mapowanie_bramek)
    assert len(zmapowane) == 1  # wiersz "A" (bez myślnika) odrzucony
    assert zmapowane.iloc[0]["c.osobowe"] == 10


def test_zmapuj_relacje_z_bramek_dwie_rozne_relacje_do_tego_samego_wlotu_manewru():
    # Dwie różne pary bramek mogą wyliczyć się do tej samej (wlot, manewr) —
    # analogiczne "duplikaty" jak w starym modelu, tu wynikają z geometrii,
    # nie z ręcznego przypisania — powinny się scalić tak samo.
    mapowanie_bramek = {"A": "PN", "E": "WSCH", "G": "PN", "H": "WSCH"}
    df_raw = _df_raw([("A-E", 7, {"c.osobowe": 10}), ("G-H", 7, {"c.osobowe": 5})])
    zmapowane = zmapuj_relacje_z_bramek(df_raw, mapowanie_bramek)
    assert len(zmapowane) == 1
    assert zmapowane.iloc[0]["c.osobowe"] == 15


def test_wczytaj_surowe_csv_akceptuje_format_kod_godz(tmp_path):
    plik = tmp_path / "quantity.csv"
    plik.write_text(
        "Kod;Godz;b.moto;c.osobowe;c3.mikrobusy;d.dostawcze;e.ciezarowe;"
        "f.ciezarowe.z.naczepami;g.autobusy;h.rolne;rowery;hulajnogi;pieszy;pieszy potrzeby\n"
        "A-E;2026-05-28 07:00;0;5;0;0;0;0;0;0;0;0;0;0\n",
        encoding="utf-8",
    )
    df = wczytaj_surowe_csv(plik)
    assert list(df.columns[:2]) == ["Kierunek", "Godzina"]
    assert df.iloc[0]["Kierunek"] == "A-E"
    assert df.iloc[0]["Godzina"] == 7
