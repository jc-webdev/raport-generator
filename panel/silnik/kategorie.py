"""Stałe kategorie pojazdów i kolejność sortowania relacji.

Źródło: raport-reguly-obliczen-i-danych.md §1-2, zgodne z kolumnami
surowego eksportu AISP (Quantity.csv).
"""

KATEGORIE_ZMOTORYZOWANE = [
    "b.moto", "c.osobowe", "c3.mikrobusy", "d.dostawcze",
    "e.ciezarowe", "f.ciezarowe.z.naczepami", "g.autobusy", "h.rolne",
]

KATEGORIE_NIEZMOT = ["rowery", "hulajnogi", "pieszy", "pieszy potrzeby"]

KATEGORIE_CIEZKIE = ["e.ciezarowe", "f.ciezarowe.z.naczepami"]

# Stała kolejność wszystkich 12 kategorii (8 zmotoryzowanych + 4 niezmotoryzowane).
KATEGORIE_WSZYSTKIE = KATEGORIE_ZMOTORYZOWANE + KATEGORIE_NIEZMOT

# Nazwy wyświetlane w raporcie — kolejność tego dicta = kolejność wierszy
# w tabeli "Struktura rodzajowa ruchu" (T8).
KATEGORIE_PELNE = {
    "c.osobowe": "Osobowe",
    "d.dostawcze": "Dostawcze",
    "f.ciezarowe.z.naczepami": "Ciężarowe z naczepami",
    "e.ciezarowe": "Ciężarowe",
    "g.autobusy": "Autobusy",
    "c3.mikrobusy": "Mikrobusy",
    "h.rolne": "Rolne",
    "b.moto": "Moto",
    "rowery": "Rowery",
    "hulajnogi": "Hulajnogi",
    "pieszy": "Piesi",
    "pieszy potrzeby": "Pieszy potrzeby",
}

WLOT_ORDER = {"PN": 0, "WSCH": 1, "PD": 2, "ZACH": 3}
MANEWR_ORDER = {"Prawo": 0, "Wprost": 1, "Lewo": 2, "Zawracający": 3}
