import json

from panel.silnik.eksportuj_godzinowe_relacje import main as eksportuj_main


def _zbuduj_projekt_testowy(tmp_path):
    dir_zrodla = tmp_path / "zrodla" / "P1"
    dir_zrodla.mkdir(parents=True)
    (dir_zrodla / "quantity.csv").write_text(
        "Kod;Godz;b.moto;c.osobowe;c3.mikrobusy;d.dostawcze;e.ciezarowe;"
        "f.ciezarowe.z.naczepami;g.autobusy;h.rolne;rowery;hulajnogi;pieszy;pieszy potrzeby\n"
        "A-B;2026-05-28 07:00;0;10;0;0;2;0;0;0;0;0;0;0\n"
        "B-A;2026-05-28 08:00;0;5;0;0;0;0;0;0;0;0;0;0\n",
        encoding="utf-8",
    )
    projekt = {
        "punkty": [{
            "numer": 1, "id": "P1", "nazwa": "Testowe skrzyżowanie",
            "metadanePomiaru": {"dataPomiaru": "2026-05-28", "dzienTygodnia": "Czwartek", "warunkiAtmosferyczne": ""},
            "kamery": [{"plikZrodlowy": "quantity.csv", "przesuniecieLiter": 0}],
            "bramkiMapping": {"A": "PN", "B": "PD"},
            "geometriaRegularna": True,
            "obliczenia": {},
        }],
    }
    sciezka_projekt = tmp_path / "projekt.json"
    sciezka_projekt.write_text(json.dumps(projekt), encoding="utf-8")
    return sciezka_projekt


def test_eksportuje_24_godziny_i_obie_serie(tmp_path, monkeypatch):
    sciezka_projekt = _zbuduj_projekt_testowy(tmp_path)
    sciezka_json = tmp_path / "godzinowe.json"
    monkeypatch.setattr("sys.argv", ["prog", str(sciezka_projekt), "1", str(sciezka_json)])
    eksportuj_main()

    dane = json.loads(sciezka_json.read_text(encoding="utf-8"))
    assert dane["godziny"] == [f"{h:02d}:00" for h in range(24)]
    assert len(dane["relacjeZmot"]) == 2
    assert len(dane["relacjeCiezkie"]) == 2
    for seria in dane["relacjeZmot"]:
        assert len(seria["wartosci"]) == 24

    ab = next(r for r in dane["relacjeZmot"] if r["wlot"] == "PN")
    assert ab["wartosci"][7] == 12  # A-B, 07:00, c.osobowe(10) + e.ciezarowe(2), oba zmotoryzowane
    ab_ciezkie = next(r for r in dane["relacjeCiezkie"] if r["wlot"] == "PN")
    assert ab_ciezkie["wartosci"][7] == 2  # A-B, 07:00, e.ciezarowe
