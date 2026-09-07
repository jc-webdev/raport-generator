# Projekt: Przebudowa raportu z pomiaru ruchu drogowego (Toruń, Orange Polska)

## Kontekst
Przebudowujemy raport z pomiaru ruchu drogowego (3 skrzyżowania w Toruniu) z formy
wysłanej do klienta na wzorcową wersję zgodną z wewnętrznym standardem firmy (patrz
`źródła/standard-4-*.md` i pozostałe pliki `źródła/standard-*.md`) oraz zbrandowaną
jako Orange Polska. To referencyjny dokument na przyszłość dla kolejnych raportów.

Pliki źródłowe (dokumentacja standardu, oryginalny raport, szablon z placeholderami)
NIE są w tym eksporcie — trzeba je skopiować z Projektu w Claude (Project knowledge)
do folderu `źródła/` przed dalszą pracą. Kluczowe z nich:
- `standard-4-raport-word--01-wzor-szablon-raportu-word.md` — obowiązkowa struktura raportu
- `standard-4-raport-word--02-wymagania-tabele-wykresy.md` — reguły obliczeń, format Quantity.csv
- `standard-3-analityka--05-kontrola-jakosci-danych.md` — zasady QC danych
- `Raport-z-pomiaru-ruchu-szablon-placeholders--2026-07-24.docx` — wzorcowa struktura/nazewnictwo sekcji
- `Raport_ruchu_drogowego_Torun_3_maj_2026_poprawiony___kopia.docx` — oryginalny raport (dane źródłowe)

## Stan prac (zrobione)
1. **Branding Orange**: logo (`assets/orange_logo.png`) w nagłówku + stronie tytułowej,
   kolor akcentu #FF7900, stopka "Orange Restricted" + numeracja stron.
2. **Struktura wg szablonu** (nie mojej wcześniejszej numeracji ze standardu):
   nazwy sekcji punktowych = "Lokalizacja i karta skrzyżowania", "Organizacja ruchu
   i geometria skrzyżowania", "Ruch według kierunków i relacji", "Rozkład dobowy
   i pory ruchu", "Struktura rodzajowa ruchu", "Komentarz analityczny", (opcjonalnie)
   "Uwagi o jakości danych".
3. **Sankeye przeniesione do sekcji "Organizacja ruchu i geometria skrzyżowania"**
   (WAŻNE: użytkownik to wymusił — Sankey ZASTĘPUJE stare "diagramy natężeń dla
   szczytów", nie jest osobną sekcją na końcu punktu).
4. **Numeracja automatyczna Worda** (nie ręczne cyfry w tekście!) via `numbering.config`
   w docx-js: poziom 0 = Heading1 (1., 2., 3...), poziom 1 = Heading2 (X.1, X.2...).
   Numer sekcji punktu = `idx + 3` (bo 1=Cel, 2=Metodologia, więc Punkt1=3, Punkt2=4,
   Punkt3=5, Analiza łączna=6, Wnioski=7, Załączniki=8). Numery tabel/rysunków w
   `buildPointSection()` używają `p.secNum`, NIE `p.num` — jeśli dodasz/usuniesz
   sekcję przed punktami, trzeba przeliczyć `secNum` i ręczne stringi w
   `summaryChildren`/`conclusionChildren`.
5. **3 pliki Excel** (`wynik_tabele_Punkt{N}_{ID}.xlsx`) — pełne tabele godzinowe
   ("Struktura rodzajowa pojazdów w dobie", setki wierszy) wyniesione z Worda do
   Excela zgodnie ze standardem 4.2 (`wynik_tabele_<nazwa_punktu>.xlsx`, jeden
   arkusz na tabelę). W Wordzie zostało tylko odesłanie + sekcja "Załączniki".

## Zidentyfikowane i naprawione problemy jakości danych (Punkt 2 — Łódzka-Andersa)
- **Zduplikowane etykiety relacji**: "ZACH – wprost" i "PN – wprost" występowały
  2x w oryginalnym raporcie (osobne bramki AISP bez unikalnej etykiety) — SCALONE
  w tabeli relacji (5863 = 3362+2501, 4816 = 2084+2732), opisane w "Uwagi o
  jakości danych".
- **Niespójna metoda liczenia %**: oryginalny tekst liczył udziały struktury
  rodzajowej względem SDR (kategorie mechaniczne, 87,1%), tabela liczyła względem
  sumy wszystkich kategorii (84,5%) — poprawna metoda wg standardu 4.2 to ta druga.
  Skorygowano tekst.
- **Sprzeczność faktograficzna**: oryginalny tekst twierdził "brak ruchu pieszego
  i rowerowego (wartości 0)", a tabela pokazywała niezerowe wartości — usunięte
  w przebudowanym tekście.

## Ważne dane wyliczone samodzielnie (nie było ich w oryginalnym raporcie)
Standard (5.3, 6.5) wymaga 3 szczytów: porannego/popołudniowego/wieczornego —
oryginalny raport podawał tylko szczyt dobowy. Wyliczone z surowych danych
godzinowych (`data/relations_peak.json`, `data/full_hourly.json`):
- Wszystkie 3 punkty mają IDENTYCZNE godziny szczytu: 07:00 / 15:00 / 18:00
  (mimo ~15-krotnej różnicy w natężeniu) — to kluczowy wniosek w "Analiza łączna".

## Struktura tego eksportu
```
scripts/   — wszystkie skrypty node.js/python generujące raport i wykresy
data/      — dane pośrednie (JSON) wyliczone z oryginalnego raportu
assets/    — logo Orange + wygenerowane wykresy/diagramy PNG
output/    — finalny raport .docx + 3 pliki .xlsx
źródła/    — (PUSTE, do uzupełnienia) dokumentacja standardu + oryginalne pliki
```

## Jak odtworzyć / kontynuować
Wymaga: Node.js (pakiet `docx`), Python 3 (`matplotlib`, `openpyxl`), LibreOffice
(`soffice`) do podglądu PDF.

```bash
cd scripts
npm install docx          # jeśli brak node_modules
python3 -m pip install matplotlib openpyxl --break-system-packages

# kolejność generowania (dane -> wykresy -> dokument):
python3 parse_relations_by_hour.py   # -> ../data/relations_data.json
python3 extract_full_hourly.py       # -> ../data/full_hourly.json (wymaga oryginalnego raportu w źródła/)
python3 sankey_diagrams.py           # -> ../assets/sankey_p*.png
python3 charts.py                    # -> ../assets/rys_4_*.png
python3 pory_doby_charts.py          # -> ../assets/rys_pory_doby_p*.png
python3 build_excel.py               # -> ../output/wynik_tabele_*.xlsx
node build_final.js                  # -> ../output/Raport_Torun_Orange_FINAL.docx
```
Uwaga: skrypty mają wpisane bezwzględne ścieżki `/home/claude/raport/...` z
poprzedniego środowiska — po przeniesieniu do VS Code trzeba je zamienić na
ścieżki względne (`__dirname` / `pathlib.Path(__file__).parent`).

## Do zrobienia (otwarte punkty)
1. **Zdjęcia z kamer i mapki lokalizacji** (Rysunek X.1/X.2 w każdym punkcie) —
   obecnie placeholdery, potrzebny materiał źródłowy (zdjęcia/screeny z AISP lub
   Google Maps).
2. **Dane na stronie tytułowej**: `[NAZWA ZAMAWIAJĄCEGO]` i `[DATA SPORZĄDZENIA]`
   wciąż jako placeholdery.
3. **Font marki Orange** — obecnie Calibri jako zamiennik; jeśli jest oficjalny
   plik fontu (.ttf/.otf), do podmiany w `build_final.js` (stała `FONT`).
4. Docelowe Sankeye z Visum zastąpią matplotlibowe przybliżenia w `assets/sankey_*.png`
   (obecne są jawnie oznaczone jako placeholder zgodnie ze standardem 4.2, sekcja
   o diagramie Sankey-like).
5. Spis treści w .docx to pole Worda — po otwarciu w Wordzie: Ctrl+A → F9, żeby
   się wygenerował (LibreOffice/PDF preview go nie pokazują).
