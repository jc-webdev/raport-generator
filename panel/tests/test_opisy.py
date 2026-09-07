from panel.silnik.opisy import _exit_bearing, REVERSE_BEARING, klucz_sortowania, oblicz_manewr, opisz_relacje, sortuj_relacje


def test_opis_regularny_przyklad_ze_spec():
    assert opisz_relacje("ZACH", "Lewo", True) == "Z zachodu na północ, w lewo"


def test_opis_nieregularny_przyklad_ze_spec():
    assert opisz_relacje("PD", "Lewo", False) == "Z południa, w lewo"


def test_prefiks_eufoniczny_wschod():
    assert opisz_relacje("WSCH", "Wprost", True).startswith("Ze wschodu")


def test_zawracajacy_bez_klauzuli_na_x():
    assert opisz_relacje("PN", "Zawracający", True) == "Z północy, zawracając"
    # Nawet przy nieregularnej geometrii forma jest identyczna (brak "na X" i tak).
    assert opisz_relacje("PN", "Zawracający", False) == "Z północy, zawracając"


def test_klucz_sortowania():
    assert klucz_sortowania("PN", "Prawo") == (0, 0)
    assert klucz_sortowania("ZACH", "Zawracający") == (3, 3)


def test_oblicz_manewr_jest_scisla_odwrotnoscia_exit_bearing():
    # Dla wszystkich 16 kombinacji (wlot, manewr): wyprowadź wlot_wyjscia via
    # istniejącą (już sprawdzoną) _exit_bearing, potem odtwórz manewr wstecz.
    for wlot_wej in ["PN", "WSCH", "PD", "ZACH"]:
        for manewr in ["Prawo", "Wprost", "Lewo", "Zawracający"]:
            wlot_wyj = REVERSE_BEARING[_exit_bearing(wlot_wej, manewr)]
            assert oblicz_manewr(wlot_wej, wlot_wyj) == manewr


def test_oblicz_manewr_przyklady():
    assert oblicz_manewr("PN", "PD") == "Wprost"
    assert oblicz_manewr("PN", "ZACH") == "Prawo"
    assert oblicz_manewr("PN", "WSCH") == "Lewo"
    assert oblicz_manewr("PN", "PN") == "Zawracający"


def test_sortuj_relacje():
    relacje = [
        {"wlot": "ZACH", "manewr": "Lewo"},
        {"wlot": "PN", "manewr": "Lewo"},
        {"wlot": "PN", "manewr": "Prawo"},
    ]
    posortowane = sortuj_relacje(relacje)
    assert [(r["wlot"], r["manewr"]) for r in posortowane] == [
        ("PN", "Prawo"), ("PN", "Lewo"), ("ZACH", "Lewo"),
    ]
