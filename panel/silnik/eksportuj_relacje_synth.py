"""CLI: eksportuje dane punktu (relacja × godzina × kategorie) jako
syntetyczny Quantity.csv (jedna litera = jedna relacja już zmapowana na
wlot+manewr) + gate_mapping.json — dokładnie format jakiego oczekuje
`Generaotr-mapy-skrzyzowania/generate_flow_diagram.py` (diagramy Sankey SDR/
UPC/szczyt poranny/popołudniowy, Etap 4 krok 11).

Ten skrypt istnieje bo generate_flow_diagram.py był pisany pod STARY model
(pojedyncza litera CSV = cała relacja, gate_mapping: litera -> [wlot,
manewr]) — nasz nowy model bramka->wlot (jedna litera = jedna fizyczna
bramka, para "X-Y" = relacja, manewr liczony geometrycznie) już wyprodukował
gotowe (wlot, manewr, Godzina, kategorie) w `df_mapped` — więc zamiast
przerabiać generate_flow_diagram.py, po prostu re-etykietujemy każdą
UNIKALNĄ (wlot, manewr) syntetyczną literą i zapisujemy w formacie który on
już umie czytać.

Użycie: python3 -m panel.silnik.eksportuj_relacje_synth <projekt.json> <numer> <output.csv> <output_mapping.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .kategorie import KATEGORIE_WSZYSTKIE
from .uruchom_dla_punktu import indeks_na_litere, wczytaj_i_zmapuj_punkt


def main() -> None:
    sciezka_projekt = Path(sys.argv[1])
    numer_punktu = int(sys.argv[2])
    sciezka_csv = Path(sys.argv[3])
    sciezka_mapping = Path(sys.argv[4])

    _, df_mapped = wczytaj_i_zmapuj_punkt(sciezka_projekt, numer_punktu)

    kombinacje = sorted(df_mapped[["wlot", "manewr"]].drop_duplicates().itertuples(index=False))
    gate_mapping = {}
    litera_dla = {}
    for i, (wlot, manewr) in enumerate(kombinacje):
        litera = indeks_na_litere(i)
        litera_dla[(wlot, manewr)] = litera
        gate_mapping[litera] = [wlot, manewr]

    df_synth = df_mapped.copy()
    df_synth["Kierunek"] = [litera_dla[(w, m)] for w, m in zip(df_synth["wlot"], df_synth["manewr"])]
    # generate_flow_diagram.py woła pd.to_datetime(df["Czas"]).dt.hour — data
    # sama w sobie nieważna, liczy się tylko godzina.
    df_synth["Czas"] = df_synth["Godzina"].apply(lambda h: f"2026-01-01 {h:02d}:00:00")
    df_synth = df_synth[["Kierunek", "Czas"] + KATEGORIE_WSZYSTKIE]

    sciezka_csv.parent.mkdir(parents=True, exist_ok=True)
    df_synth.to_csv(sciezka_csv, sep=";", index=False, encoding="cp1250")
    sciezka_mapping.write_text(json.dumps({"gate_mapping": gate_mapping}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"ok": True, "relacje": len(gate_mapping)}))


if __name__ == "__main__":
    main()
