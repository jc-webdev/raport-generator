"""Test regresyjny/sanity na realnych danych (drogi/Quantity.csv) —
sprawdza że silnik nie wywala się i zwraca sensowne rzędy wielkości.
Nie liczony ręcznie (14 kierunków x 24h za dużo na weryfikację ręczną).
"""
from pathlib import Path

from panel.silnik.mapowanie import wczytaj_surowe_csv, zmapuj_kierunki
from panel.silnik.orkiestrator import oblicz_wszystko

SCIEZKA_CSV = Path(__file__).parents[2] / "drogi" / "Quantity.csv"

# Przepisane 1:1 z drogi/drogi.ipynb (sprawdzony mapping dla tego pliku).
KIERUNEK_MAPPING = {
    "A": {"wlot": "PD", "manewr": "Prawo"},
    "B": {"wlot": "PD", "manewr": "Wprost"},
    "C": {"wlot": "PD", "manewr": "Lewo"},
    "D": {"wlot": "WSCH", "manewr": "Lewo"},
    "E": {"wlot": "WSCH", "manewr": "Wprost"},
    "F": {"wlot": "WSCH", "manewr": "Prawo"},
    "G": {"wlot": "ZACH", "manewr": "Lewo"},
    "H": {"wlot": "ZACH", "manewr": "Wprost"},
    "I": {"wlot": "ZACH", "manewr": "Wprost"},
    "J": {"wlot": "ZACH", "manewr": "Prawo"},
    "K": {"wlot": "PN", "manewr": "Wprost"},
    "L": {"wlot": "PN", "manewr": "Wprost"},
    "M": {"wlot": "PN", "manewr": "Lewo"},
    "N": {"wlot": "PN", "manewr": "Prawo"},
}


def test_quantity_csv_smoke():
    df_raw = wczytaj_surowe_csv(SCIEZKA_CSV)
    df_mapped = zmapuj_kierunki(df_raw, KIERUNEK_MAPPING)

    wynik = oblicz_wszystko(df_mapped, geometria_regularna=True)

    assert wynik["sdr"] > 0
    assert len(wynik["relacjeSDR"]) == len(wynik["relacjeCiezkie"])
    assert wynik["relacjeZNiezmotDostepne"] is True
    assert wynik["relacjeCiezkieEstymowane"] is False
    assert wynik["strukturaRodzajowaSumaCala"] >= wynik["sdr"]
    assert len(wynik["godzinowa"]) == 24
    assert len(wynik["strukturaRodzajowa"]) == 12
