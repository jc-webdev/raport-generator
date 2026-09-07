# Stan prac — panel generowania raportów z pomiaru ruchu drogowego

Budowane wg trzech specyfikacji w korzeniu repo:
`specyfikacja-panel-generowania-raportow-v2.md` (architektura/pipeline),
`raport-specyfikacja-struktura.md` (struktura dokumentu Word),
`raport-reguly-obliczen-i-danych.md` (formuły/przypadki brzegowe).

Plan pierwotny: 4 etapy z potwierdzeniem po każdym. Stan na teraz:
**Etap 1 gotowy, Etap 2 gotowy, Etap 3 działa w trybie podstawowym (1 punkt, przetestowany też
strukturalnie na 3 punktach syntetycznych), Etap 4 — WSZYSTKIE 11 kroków zaimplementowane i
zweryfikowane end-to-end (krok 8/AI świadomie jako placeholder ręcznej edycji tekstu, patrz niżej).**

Referencyjny plik do porównań: `/Users/jakubchmielewski/Desktop/Orange-apka-raporty-ruchu/Raport_Torun_Orange_v3 (1) (3).docx`
(dostarczony przez użytkownika — realny, wzorcowy raport z prawdziwymi danymi 3 punktów Toruń).

---

## ETAP 1 — silnik obliczeniowy (Python) ✅ GOTOWE

Lokalizacja: `panel/silnik/`

- `kategorie.py` — stałe (grupy kategorii pojazdów, WLOT_ORDER, MANEWR_ORDER)
- `mapowanie.py` — wczytanie CSV AISP, walidacja liter, wykrywanie/scalanie duplikatów
- `opisy.py` — algorytm opisu relacji (§5.4) + sortowanie (§5.5)
- `obliczenia.py` — 9 funkcji z §5.3 (SDR, szczyty, relacje, UPC, godzinowa, pory doby, struktura rodzajowa)
- `orkiestrator.py` — `oblicz_wszystko()` składa wszystko w kształt `punkty[i].obliczenia`
- `przypisy.py` — deterministyczne przypisy jakości danych z flag QC

**Testy:** `panel/tests/` — 23/23 przechodzi (`generator-mapek/venv/bin/pytest panel/tests -v`).
Pokrywa happy path + przypadki brzegowe: wyzerowane niezmot./ciężkie w danych godzinowych,
scalanie zdublowanych liter AISP, skrzyżowanie typu T, opisy regularne/nieregularne/zawracające.

**Zweryfikowane na realnych danych:** `drogi/Quantity.csv` (Punkt 2, Łódzka-Andersa) →
SDR=31185, 12 relacji po scaleniu duplikatów (K+L, H+I), zero kategorii estymowanych.

**Decyzje podjęte z użytkownikiem (nie zgadywane):** `manewr` zawsze Title-case;
`udzial` w tabelach relacji liczony względem sumy TEJ tabeli (nie zawsze względem SDR punktu);
`udzialZmot/udzialNiezmot` w tabeli godzinowej = udział godziny w dobowym profilu;
`geometriaRegularna` to zwykły parametr wejściowy, silnik go nie wykrywa.

**Środowisko:** `generator-mapek/venv` (ma pandas/numpy), doinstalowano `pytest` z `panel/requirements.txt`.

---

## ETAP 2 — generator docx dla JEDNEGO punktu (Node.js + `docx`) ✅ GOTOWE

Lokalizacja: `panel/docx/`

- `liczniki.js` — niezależne liczniki Rysunek/Tabela, restart od 1 per punkt
- `formatowanie.js` — separator tysięcy spacją, procenty z przecinkiem (§7)
- `style.js` — helpery: `akapit` (justowany), `naglowek`, `tabela` (z proporcjami kolumn),
  `podpisKursywa`, `obrazek` (wycentrowany), `wierszZObrazkiem` (obrazek w scalonym wierszu tabeli)
- `probaRozmiaru.js` — czyta W/H z nagłówka PNG bez zależności npm
- `budujPunkt.js` — **główna funkcja**, buduje 8 podrozdziałów (3.n.1–3.n.8), T1–T8, R1–R11
- `test_budujPunkt.js` — generuje testowy `.docx` dla jednego punktu + asercje strukturalne

**Wygenerowane pomocnicze skrypty Python** (`panel/docx/`):
- `generuj_wykres_pory_doby.py` — R11 (jedyny wykres z realnym generatorem wg spec)
- `generuj_placeholder.py` — szare placeholdery R1/R3/R8/R9/R10 (brak dedykowanych generatorów)
- `generuj_wykres_zestawienie_sdr.py`, `generuj_wykres_szczyty_projektu.py` — wykresy 4.1/4.2 (Etap 3)

### Naprawione po drodze bugi (WAŻNE — nie powtarzać tych błędów)

1. **Brak `page.size` w Document** → domyślny US Letter zamiast A4, psuł kalkulację ile
   obrazków mieści się na stronie (ogromne puste odstępy). Naprawione: jawny A4
   (`11906 x 16838` dxa) + marginesy 2 cm w `properties.page`.
2. **`WidthType.PERCENTAGE` dla szerokości tabel** → `docx` zapisuje `w:w="100%"`
   (z literalnym znakiem %), co jest **niezgodne z OOXML** (wymagana liczba w
   pięćdziesiątych procenta bez znaku %). LibreOffice to toleruje, prawdziwy Word/Pages
   zwija tabelę do wąskiej. Naprawione: wszystkie tabele używają `WidthType.DXA`
   z jawnymi szerokościami kolumn per tabela (patrz `budujPunkt.js`, 5. argument `tabela()`).
3. **R1 (mapka lokalizacji) musi być w Tabeli T1**, w ostatnim wierszu, scalone kolumny
   (`columnSpan`), obrazek + podpis wycentrowane w tej samej komórce — zaimplementowane
   przez `wierszZObrazkiem()`, dokładnie jak w referencyjnym raporcie.
4. **Wycentrowanie obrazów / justowanie tekstu** — zaimplementowane (`AlignmentType.CENTER`
   / `JUSTIFIED`), **zweryfikowane bezpośrednio w wygenerowanym XML** (nie na oko) —
   poprawne. Użytkownik zgłaszał że "nie działa" w **Apple Pages** — potwierdzone że to
   ograniczenie niepełnej zgodności Pages z formatem .docx (Pages ma znane problemy z
   `w:jc` w komórkach tabel i akapitach), nie błąd w generowanym pliku. **Nie testowane
   jeszcze w prawdziwym Microsoft Word** — do zrobienia, jeśli użytkownik ma dostęp.

**Realne assety użyte dla Punktu 2:** logo Orange (`assets/logo.png`, dostarczone przez
użytkownika), `diagram_sdr_p2.png`/`diagram_upc_p2.png`/`diagram_am_peak_p2.png`/
`diagram_pm_peak_p2.png` z `Generaotr-mapy-skrzyzowania/` (R4-R7), `mapa2.png` jako
schemat skrzyżowania (R2). Placeholdery: R1 (mapka lokalizacji), R3 (kamera — i tak
ręczny upload wg spec), R8/R9/R10 (wykresy godzinowe — brak dedykowanych generatorów,
zgodnie ze spec).

**Wynik:** 9 stron dla jednego punktu (budżet ze spec: ~10 stron/punkt). 8 tabel, 11 rysunków.

---

## ETAP 3 — pełny dokument, wiele punktów ⚠️ CZĘŚCIOWO GOTOWE

Lokalizacja: `panel/docx/budujRaport.js` + `panel/docx/test_budujRaport.js`

**Zaimplementowane i działające** (przetestowane z N=1 punktem, bo tylko tyle mamy
realnych danych źródłowych — patrz "Do zrobienia" niżej):
- Strona tytułowa (logo, tytuł, linia orange, tabela metadanych, BEZ nagłówka/stopki —
  `titlePage: true` w sekcji, `headers.first`/`footers.first` puste)
- Spis treści (pole Word TOC, `hyperlink: true, headingStyleRange: "1-3"`) — **wymaga
  ręcznego odświeżenia w Wordzie** (Ctrl+A → F9), pole jest puste dopóki Word/LibreOffice
  go nie przeliczy — to normalne ograniczenie tego mechanizmu, nie bug
- Rozdział 1 (Cel i zakres) — tekst + bullet lista punktów (generowana z `projekt.punkty`)
- Rozdział 2 (Metodologia) — tekst STAŁY (ten sam dla każdego projektu, wzorowany na
  referencyjnym raporcie), + nagłówek "3. Wyniki pomiarów..." i akapit wprowadzający
- Pętla po punktach → `budujPunkt()` per punkt, z prefiksem `3.{numer}`
  - **Zmiana względem Etapu 2:** nagłówek punktu przeniesiony z HEADING_1 na HEADING_2
    (bo jest pod rozdziałem 3, który teraz jest HEADING_1), podrozdziały punktu (3.n.1 itd.)
    przeniesione z HEADING_2 na HEADING_3 — dla poprawnej hierarchii w spisie treści
- Rozdział 4 (Podsumowanie), **tryb pełny** (N ≤ próg=15):
  - 4.1 Zestawienie zbiorcze (tabela + wykres słupkowy SDR per punkt)
  - 4.2 Struktura rodzajowa w skali projektu (tabela porównawcza kategorie×punkty,
    wiersz "Piesi" zmieniony na "Środki transportu publicznego" zgodnie ze spec)
    + wykres szczytów w stałych oknach per punkt
  - 4.3 Wnioski i rekomendacje — placeholder tekstowy
- Rozdział 5 (Literatura i spis załączników) — link GDDKiA + lista plików xlsx wg wzorca
  `wynik_tabele_Punkt{N}_{ID}.xlsx`

**Wynik testowy:** 14 stron dla projektu z 1 punktem, wszystkie asercje strukturalne przechodzą
(`node panel/docx/test_budujRaport.js`).

### Naprawione bugi

- ~~Etykieta osi X w `generuj_wykres_zestawienie_sdr.py`/`generuj_wykres_szczyty_projektu.py`
  używała `f"P{p['numer']}"` zamiast `p['id']`~~ — naprawione (2026-09-03), oba wykresy
  przeregenerowane (`assets/r_zestawienie_sdr.png`, `assets/r_szczyty_projektu.png`) i
  zweryfikowane wizualnie (P2 zamiast P1). Uwaga na przyszłość: te wykresy Python NIE są
  wywoływane automatycznie przez `budujRaport.js`/`test_budujRaport.js` — trzeba je
  ręcznie przeregenerować po zmianie fixture, inaczej `.docx` użyje starych PNG-ów z `assets/`.

### Co NIE jest zrobione w Etapie 3

1. **Tryb zagregowany (N > próg)** — zaimplementowany jako gołosłowny placeholder
   (jeden akapit kursywą, żeby kod się nie wysypał), NIE ma: tabeli Top 10/Top 10,
   histogramu SDR, mapy projektu z kropkami per punkt, segmentacji wg pola `typ`.
   Nie da się tego sensownie przetestować bez >15 realnych punktów danych.
2. ~~Automatyczna numeracja rozdziałów przez Word~~ — zrobione (2026-09-04): dodano prawdziwy
   multi-level list Worda (`numeracjaRozdzialowConfig` w `style.js`, referencja
   `"naglowki-rozdzialow"`, 3 poziomy DECIMAL: `%1.` / `%1.%2.` / `%1.%2.%3.`, spięty z
   Heading1/2/3 przez `numbering.config` w `Document`). `naglowek()` w `style.js` domyślnie
   dołącza numerację (`{ numerowany: false }` dla wyjątków jak "Spis treści", który celowo
   zostaje bez numeru). Usunięto WSZYSTKIE ręcznie wpisywane numery rozdziałów/podrozdziałów
   z tekstu nagłówków w `budujRaport.js` i `budujPunkt.js` ("1. Cel i zakres..." → "Cel i
   zakres...", "3.1 Lokalizacja..." → "Lokalizacja...", itd.) — Word/LibreOffice liczy je
   teraz sam, resetując poziomy automatycznie przy każdym nowym punkcie/rozdziale. Numery
   Tabela/Rysunek (Liczniki z `liczniki.js`) **nie są tym objęte** — to osobny, celowo
   ręczny mechanizm (numeracja obiektów pływających, nie ma dobrego odpowiednika w Word
   multi-level list). Zweryfikowane wizualnie w PDF (LibreOffice): "1. Cel i zakres...",
   "3.1. Punkt 1...", "3.1.1. Lokalizacja...", "4.2. Struktura rodzajowa..." — wszystko
   poprawnie auto-numerowane, "Spis treści" bez numeru. `numbering.config` trzeba przekazać
   do KAŻDEGO `new Document(...)` który używa `naglowek()` — dodane w obu testach
   (`test_budujPunkt.js`, `test_budujRaport.js`); przyszły kod budujący `Document` (np.
   docelowy UI z Etapu 4) musi o tym pamiętać, inaczej numery nie pojawią się w ogóle.
3. ~~Testowane tylko z N=1 punktem~~ — częściowo zrobione (2026-09-04): dalej brak REALNYCH
   danych dla >1 skrzyżowania (`drogi/Quantity.csv` to jedyny prawdziwy plik AISP), ale
   pętla po wielu punktach jest teraz przetestowana strukturalnie na **danych syntetycznych**:
   `dane_testowe/projekt_fixture_3punkty.json` (wygenerowany jednorazowym skryptem node,
   klonuje jedyny realny punkt 3x jako P1/P2/P3, z dopiskiem "[DANE SYNTETYCZNE...]" w
   tekście lokalizacji żeby się nie pomylić z prawdziwymi danymi). `test_budujRaport.js`
   przyjmuje teraz opcjonalny argument CLI z nazwą pliku fixture (domyślnie
   `projekt_fixture.json`, N=1) — `node test_budujRaport.js projekt_fixture_3punkty.json`.
   Zweryfikowane na N=3: 31 stron, 61 unikalnych podpisów Tabela/Rysunek (3×19 + 4, zero
   kolizji — złapane przez `sprawdzUnikalnoscNumeracji()`), poprawny restart auto-numeracji
   Worda na każdym punkcie (3.1→3.1.8, 3.2→3.2.8, 3.3→3.3.8, potem 4/4.1-4.3 — sprawdzone
   przez `pdftotext` na wyrenderowanym PDF), Tabela 4.1 poprawnie zestawia 3 wiersze P1/P2/P3,
   oba skrypty wykresów projektowych (`generuj_wykres_zestawienie_sdr.py`,
   `generuj_wykres_szczyty_projektu.py`) poprawnie rysują 3 słupki. **Nadal nieprzetestowane
   na realnych, różnych danych 3 skrzyżowań** (to wymagałoby prawdziwych plików
   `Quantity.csv`) — syntetyczny test wyklucza tylko błędy strukturalne/kolizje w pętli
   budującej, nie waliduje merytorycznie treści dla różnych zestawów danych. Tryb
   zagregowany (N>15, pkt 1 wyżej) dalej nieruszony — do tego trzeba by nasyntetyzować
   >15 punktów, co nie ma sensu bez realnej walidacji.
4. ~~Weryfikacja "zero duplikatów w numeracji"~~ — zrobione (2026-09-03): `test_budujRaport.js`
   → `sprawdzUnikalnoscNumeracji()` rozpakowuje wygenerowany `.docx` (przez `jszip`, już
   tranzytywna zależność `docx`, nic nowego nie doinstalowano), wyciąga wszystkie podpisy
   `Tabela X.Y`/`Rysunek X.Y` wprost z finalnego `word/document.xml` (nie z kodu JS — więc
   łapie też błędy w samym renderowaniu) i asertuje brak duplikatów. Przy N=1 wychodzi
   23 unikalne podpisy (19 w punkcie + 4 w Podsumowaniu). Sprawdzone też negatywnie
   (sztucznie zdublowany blok punktu → test poprawnie łapie duplikaty).

---

## ETAP 4 — UI wizard 🟢 WSZYSTKIE 11 KROKÓW (krok 8/AI jako placeholder ręczny)

Lokalizacja: `panel/ui/`. Uruchomienie: `node panel/ui/server.js` (albo `npm start` w
`panel/ui/`) → `http://localhost:4173`.

**Decyzja stacku (2026-09-04, z użytkownikiem):** docelowo ma to działać na zablokowanym
laptopie firmowym Windows bez Dockera i bez uprawnień admina. Wybrano **czysty Node.js
(`http`/`fs`/`path`, zero zależności npm)** zamiast Express/React — mniej ruchomych części,
mniejsze ryzyko że `npm install` czegoś nowego nie przejdzie za firmowym proxy. Frontend to
zwykły HTML/CSS/vanilla JS bez build stepu (`panel/ui/public/`) — `node server.js` i gotowe,
tak jak reszta tego repo (Node dla docx, Python dla silnika) już działa bez Dockera.

**Model stanu:** `projekt.json` na dysku w `panel/ui/projekty/<id>/projekt.json` (jedyne
źródło prawdy, zgodnie ze spec §2/§3) — każdy krok zapisuje natychmiast (PUT nadpisuje
całość). Surowe CSV kamer lądują obok w `projekty/<id>/zrodla/<punktId>/<plik>.csv`, NIE w
samym `projekt.json` (rozdęłoby go dla dużych projektów) — `projekt.json` trzyma tylko
metadane kamery (`plikZrodlowy`, `przesuniecieLiter`, `liczbaLiter`, `litery`).

**Zaimplementowane (wszystkie 11 kroków z tabeli §4 spec):**
- Krok 1 — metadane projektu (nazwa, zamawiający, zakres dat, próg trybu Podsumowania,
  link GDDKiA) → tworzy projekt zawsze z 1 punktem. **Zmiana 2026-09-04 (feedback
  użytkownika: "bez sensu podawać ręcznie liczbę punktów, to się powinno samo zliczać")**
  — usunięte pole "Liczba punktów pomiarowych" z formularza nowego projektu; zamiast tego
  przycisk "+ Dodaj punkt" (`POST /api/projekty/:id/punkty`, `nowyPunktSzkielet()` w
  `server.js`) na końcu listy kart punktów, dodaje kolejny punkt i od razu na niego
  przełącza. Liczba punktów = `punkty.length`, nigdzie już nie deklarowana z góry. Przy
  okazji przemianowana myląca etykieta "Próg trybu Podsumowania (liczba punktów)" →
  "Powyżej ilu punktów przełączyć na tryb zagregowany" (czytała się jak duplikat pola
  liczby punktów, choć to inna wartość — próg, nie licznik). Przycisk "+ Dodaj punkt"
  występuje w DWÓCH miejscach (feedback: "musi być też po kroku 10 pod formularzem
  całym") — przy kartach punktów u góry ORAZ pod formularzem Podsumowania (krok 10),
  tuż przed krokiem 11 — oba wołają tę samą funkcję `dodajPunkt()` w wizard.js.
  **Usuwanie punktu** (dodane 2026-09-04, feedback: "dodałem za dużo i nie mogę usunąć") —
  przycisk "Usuń ten punkt" (czerwony, przy nagłówku Kroku 2) z natywnym `window.confirm()`
  przed usunięciem (bez custom modala — natywny dialog wystarcza, mniej kodu). `DELETE
  /api/projekty/:id/punkty/:numer` w `server.js` usuwa punkt z `punkty[]` I sprząta jego
  pliki na dysku (`zrodla/<punktId>/`, `assets/<punktId>/` — `fs.rmSync recursive`), żeby
  nie zostawiać sierocych CSV/zdjęć. Punkty NIE są przenumerowywane po usunięciu (np.
  usunięcie P2 z {P1,P2,P3} zostawia {P1,P3}, nie {P1,P2}) — świadomie, żeby nie trzeba
  było przenosić plików już powiązanych ze starym `id`. UI: `wyrenderujPanelPunktu()` ma
  teraz guard na `punkty.length === 0` (usunięcie ostatniego/jedynego punktu pokazuje
  komunikat zamiast się wysypać na `pkt.kamery` z `pkt === undefined`) — zweryfikowane
  osobnym testem end-to-end. Zweryfikowane też: odrzucenie potwierdzenia (`dialog.dismiss()`
  w teście Playwright) nic nie zmienia, zaakceptowanie usuwa dokładnie ten jeden punkt.
- Krok 2 — dane podstawowe punktu (id, typ z enuma `skrzyzowanie/rondo/tranzyt/rejestracja`,
  nazwa, miejscowość, współrzędne lat/lng).
- Krok 3 — upload CSV kamer (przez zwykły `<input type=file multiple>`, treść pliku
  czytana w przeglądarce i wysyłana jako JSON string — brak multer/multipart, zero
  zależności). Serwer liczy **auto `przesuniecieLiter`** (suma liczby unikalnych liter
  poprzednich kamer TEGO punktu, spec §5.1 pkt 3) — nowa logika, nie było jej wcześniej w
  Etapie 1. Krok 5 mapuje już "litery efektywne" (surowa + przesunięcie, liczone w locie,
  patrz niżej) — samo fizyczne scalenie wielu CSV w jeden zestaw danych z przesuniętymi
  literami zostaje na krok 7 (silnik `orkiestrator.py`, poza obecnym zakresem).
- Krok 4 — metadane pomiaru (data, dzień tygodnia, warunki atm., status przydatności z
  enuma, zakłócenia).
- Nawigacja: karty-przyciski punktów (P1/P2/.../PN) z ✓ gdy punkt ma nazwę+kamerę+datę
  pomiaru; przełączanie zachowuje stan (każda sekcja zapisuje się osobno).
- Lista projektów na stronie startowej (wznowienie pracy) + tworzenie nowego.
- **Krok 5/5b — mapowanie kierunków + walidacja blokująca** (dodane 2026-09-04): tabela
  "litera efektywna × wybór wlotu/manewru" (wlot ograniczony do stałego zbioru
  `PN/WSCH/PD/ZACH`, manewr do `Prawo/Wprost/Lewo/Zawracający` — silnik/`kategorie.py` i tak
  nie zna innych wartości, więc UI nie pozwala wpisać nic spoza tego), checkbox
  `geometriaRegularna` (param wejściowy, NIE auto-wykrywany — zgodnie z wcześniejszą
  decyzją z Etapu 1), pola opisu dla 4 możliwych wlotów (zapisywane tylko dla wlotów
  faktycznie użytych w mapowaniu). "Litera efektywna" = surowa litera z CSV przesunięta o
  `kamera.przesuniecieLiter` (nowa funkcja `indeksNaLitere`/`efektywneLiteryPunktu` w
  `server.js`, przechodzi na etykiety AA/AB/... gdy zabraknie liter A-Z). Przycisk "Zapisz
  i zwaliduj" woła `PUT /punkty/:numer/mapowanie`, serwer liczy `qc` (port logiki z
  `mapowanie.py::wykryj_duplikaty`, przepisany w JS zamiast wołania Pythona — trywialna
  funkcja grupująca, nie warto robić subprocessu dla tego) i pokazuje: czerwony blokujący
  baner gdy są niezmapowane litery, żółty informacyjny gdy są zdublowane relacje (spec:
  duplikaty NIE blokują, scalają się automatycznie i niejawnie na etapie agregacji).

**Zweryfikowane (2026-09-04):** pełny przepływ API przez `curl` (utworzenie projektu N=2,
upload 2 kamer do tego samego punktu → przesunięcieLiter 0 potem 14 poprawnie, PUT
częściowych edycji, listing), ORAZ wizualnie w prawdziwej przeglądarce (Playwright/Chromium
przez `npx playwright`, zainstalowany doraźnie do tego testu — nie jest zależnością
projektu) — zrzuty ekranu strony startowej i widoku projektu, upload pliku przez faktyczny
`<input type=file>`, usunięcie kamery przez UI, zero błędów w konsoli przeglądarki.
**Krok 5 zweryfikowany dodatkowo na realnym mappingu z `test_integracja_quantity.py`**
(14 liter, `drogi/Quantity.csv`) — silnik walidacji w UI wykrył DOKŁADNIE te same duplikaty
co udokumentowane ręcznie w Etapie 1 (H+I na ZACH/Wprost, K+L na PN/Wprost), zero
niezmapowanych liter → status `akceptacja`; i negatywnie — usunięcie mapowania jednej
litery (przez prawdziwy `<select>` w przeglądarce, nie API) poprawnie pokazało czerwony
blokujący baner "Niezmapowane litery: N".

- **Krok 6 — zdjęcie z kamery + schemat skrzyżowania** (dodane 2026-09-04): proste uploady
  plików (`<input type=file accept="image/*">`, po jednym na pole). Brak multer/multipart —
  plik czytany w przeglądarce jako `ArrayBuffer` → base64 (`plikNaBase64()` w wizard.js) i
  wysyłany jako JSON string, tak jak CSV w kroku 3. Serwer zapisuje do
  `projekty/<id>/assets/<punktId>/<pole>.<ext>`, `punkt.assets.{zdjecieKamery,
  schematSkrzyzowania}` = ścieżka względna; nowa trasa `GET /api/projekty/:id/assets/*`
  serwuje pliki z powrotem (podgląd `<img>` w wizardzie). **Auto-generacja schematu
  skrzyżowania z opcji spec ("upload lub auto-generacja") NIE zaimplementowana** — tylko
  ręczny upload; rysowanie schematu z etykietami wlotów to osobny generator diagramów,
  poza zakresem tej tury.
- **Krok 7/7b — uruchomienie silnika + bramka jakości** (dodane 2026-09-04): nowy
  `panel/silnik/uruchom_dla_punktu.py` — CLI wołane jako
  `python3 -m panel.silnik.uruchom_dla_punktu <projekt.json> <numer>`, które: wczytuje CSV
  wszystkich kamer punktu, przesuwa litery `Kierunek` o `kamera.przesuniecieLiter` (funkcja
  `przesun_litere`/`indeks_na_litere` w Pythonie — **musi być bit-identyczna** z
  `indeksNaLitere` w `server.js`, bo krok 5 (mapowanie) i krok 7 (obliczenia) operują na
  tych samych "literach efektywnych"; oba miejsca skomentowane z odnośnikiem do siebie),
  scala kamery, woła `zmapuj_kierunki()` + `oblicz_wszystko()` + `generuj_przypisy_jakosci()`
  z Etapu 1, wypisuje JSON na stdout. Node (`uruchomSilnik()` w `server.js`) odpala to przez
  `child_process.execFile` (venv wykrywany automatycznie: `generator-mapek/venv/bin/python3`
  Unix / `Scripts/python.exe` Windows, nadpisywalne `PYTHON_BIN`), zapisuje wynik do
  `punkt.obliczenia`/`punkt.przypisyJakosciDanych`. Endpoint blokuje uruchomienie (400) jeśli
  krok 5 nie jest ukończony (`qc.literyNiezmapowane` niepuste). Bramka 7b: **zawsze
  `status: "akceptacja"`** po policzeniu — `ponytail:` oznaczone wprost w kodzie, bo
  detektor `kategorieWyzerowaneGodzinowo` (anomalia z §8 checklisty) to osobne zadanie
  badawcze nigdy niezaimplementowane nawet w Etapie 1, nie tylko w tym UI; podnieść gdy
  taki detektor powstanie.
  **Zweryfikowane end-to-end przez prawdziwy przepływ przeglądarki** (Playwright: upload
  CSV → wypełnienie 14-wierszowego mapowania → zapis → upload zdjęcia → "Uruchom
  obliczenia") — wynik SDR 31 185, szczyt 2352 poj./h o 15:00, **12 relacji** (14 liter
  minus 2 scalone duplikaty), dokładnie zgodne z udokumentowanym wynikiem Etapu 1. Zero
  błędów konsoli.

- **Krok 9 — teksty analityczne punktu** (dodane 2026-09-04): 7 pól `teksty.*` (lokalizacja,
  organizacjaRuchu, ruchWgKierunkow, ruchPojazdowCiezkich, poryDoby, strukturaRodzajowa,
  komentarzAnalityczny) jako `<textarea>` z domyślnym placeholderem
  `"[SZKIC — do zastąpienia tekstem z Etapu 4/AI]"` (ta sama stała co w istniejących
  fixture'ach `panel/docx/dane_testowe/`) — **krok 8 (AI) świadomie odłożony na koniec, z
  decyzją użytkownika** ("AI na koniec, musimy do tego inaczej podejść"); do czasu jego
  podłączenia krok 9 pełni podwójną rolę — ręczne wypełnienie ZASTĘPUJE AI, nie tylko
  edytuje jego wynik.
- **Generator tekstów regułowych, bez AI** (dodane 2026-09-04, na wyraźną prośbę
  użytkownika: "bazując na opisach z Raport_Torun_orange_v3 musimy zbudować listę takich
  opisów, które będą dopasowane do wyników, żeby nie było trzeba używać AI"):
  - Nowy `panel/silnik/teksty.py` — 7 czystych funkcji (jedna na pole `teksty.*`), każda
    buduje jeden akapit wyłącznie z `obliczenia` (Etap 1) + metadanych punktu, przez
    warunkowe szablony zdań (ten sam styl co już istniejące `opisy.py`/`przypisy.py` —
    deterministyczne, nie model językowy). Wzorce/progi wyprowadzone z RĘCZNEJ analizy
    prawdziwego tekstu z `Raport_Torun_Orange_v3 (1) (3).docx` (wyciągniętego z XML-a
    przez `python3 -m zipfile`, bez nowej zależności) dla wszystkich 3 punktów — w tym
    przypadku T-skrzyżowania (geometria nieregularna, 3 wloty) i przypadku z Uwagami o
    jakości danych. Kluczowe progi: dominacja "wprost" ≥50% SDR → fraza "korytarzowy
    charakter" (koryta w P1: 88,9% wyliczone vs 88,7% w referencji — różnica tylko z
    zaokrągleń), inaczej najsilniejsza pojedyncza relacja → fraza "rozprowadzanie ruchu do
    układu lokalnego" (dokładnie jak P2: 19,3% wlot zachodni-prawo); ruch niezmotoryzowany
    (rowery+piesi) ≥10% → "wysoki udział... sieć pieszo-rowerowa" (dokładnie jak P3: 14,7%).
  - **Naprawiony w trakcie**: deklinacja nazw miast po polsku (Toruń→Toruniu) jest
    niedeterministyczna bez słownika odmian — zamiast zgadywać, zdanie przerobione na
    "w miejscowości {X}" (zawsze poprawne gramatycznie niezależnie od nazwy).
  - Nowy `panel/silnik/uruchom_teksty_dla_punktu.py` (CLI, analogiczny do
    `uruchom_dla_punktu.py`) + endpoint `POST /punkty/:numer/generuj-teksty` w `server.js` +
    przycisk "Wygeneruj szkic tekstu (reguły, bez AI)" w kroku 9 UI — wypełnia wszystkie 7
    pól od razu, użytkownik może doprecyzować ręcznie przed zapisem. Wymaga ukończonego
    kroku 7 (`disabled` dopóki `pkt.obliczenia` nie istnieje).
  - Test `panel/tests/test_teksty.py` (11 przypadków, pokrywa gałęzie: korytarzowy vs
    rozproszony rozkład ruchu, wysoki vs niski udział niezmotoryzowanych, z/bez przypisów
    jakości, liczba pojedyncza/mnoga) — **34/34 testów silnika przechodzi łącznie**.
  - **Zweryfikowane end-to-end na realnym `Quantity.csv`** przez pełny przepływ przeglądarki
    (upload → mapowanie → obliczenia → wygeneruj teksty) — wszystkie 7 pól wypełnione
    spójnymi, poprawnymi gramatycznie zdaniami dopasowanymi do policzonych liczb.
  - **Świadomie NIE odtworzone**: zdania porównujące punkty między sobą ("w
    przeciwieństwie do Punktu 1...") — wymagałyby kontekstu całego projektu przy
    generowaniu tekstu pojedynczego punktu, nie tylko `obliczenia` tego punktu; żadne z 7
    pól `teksty.*` tego nie potrzebuje strukturalnie, pominięte celowo. Podobnie
    `podsumowanie.teksty.*` (krok 10, poziom projektu) nadal ma tylko placeholder ręczny —
    generator reguł objął na razie wyłącznie teksty per-punkt (krok 9).
- **Krok 10 — Podsumowanie** (dodane 2026-09-04): sekcja na poziomie projektu (nie punktu)
  pod listą punktów — pokazuje wyliczony `trybRenderowania` (pełny/zagregowany, na podstawie
  N vs `progAnalizyLacznej`, z ostrzeżeniem że tryb zagregowany nie ma jeszcze pokrycia w
  budowie docx — patrz Etap 3) + 3 pola tekstowe (`podsumowanie.teksty.tekstWprowadzenie/
  tekstPorownanie/tekstWnioski`), ten sam wzorzec placeholderu co krok 9.
- **Krok 11 — budowa raportu Word** (dodane 2026-09-04): przycisk "Generuj raport Word",
  zablokowany dopóki którykolwiek punkt nie ma `obliczenia` (krok 7). Pod spodem:
  - Nowy `panel/docx/branding.js` — wydzielone z `test_budujRaport.js` (bez zmiany logiki,
    tylko przeniesienie) 4 funkcje `budujHeader/budujFooter/pustyHeader/pustyFooter`, żeby
    nie duplikować brandingu Orange między testem Etapu 3 a nowym generatorem realnym.
  - Nowy `panel/docx/generuj_docx.js` — CLI (`node generuj_docx.js <fixture.json>
    <output.docx> <logo.png> [baseDir]`) będące odpowiednikiem `test_budujRaport.js` bez
    asercji testowych, do faktycznej generacji. `baseDir` jest JAWNYM argumentem (nie
    wyprowadzanym z lokalizacji fixture) — dokładnie jak w `test_budujRaport.js`, bo
    `budujPunkt.js` rozwiązuje `assets.*.plik` względem `baseDir`, nie względem fixture.
  - `server.js::zbudujRaport()` — most między kształtem `projekt.json` tego wizarda (spec
    v2 §3) a fixture którego oczekuje `budujRaport.js` (**rozjazd modelu danych, patrz
    niżej**). Generuje: `metadanePomiaru.czasRozpoczecia/czasZakonczenia` jako stałe
    `"00:00"/"23:59"` (spec v2 ich nie zbiera — wszystkie dotychczasowe pomiary to pełna
    doba); `wloty[]` z `{id,opis,uwagi}` (krok 5) na `{nrWlotu,opis,kierunek,uwagi}`
    (numer wlotu = kolejność, kierunek = id).
  - **Reguła placeholderów wielokrotnego użytku (spec §5.7)** zaimplementowana dosłownie:
    dla 7 typów rysunków bez dedykowanego generatora w TYM repo (mapkaLokalizacji — spec
    go opisuje jako "generator gotowy" ale to opis DOCELOWEGO stanu, integracja OSM/Mapbox
    to wciąż "do potwierdzenia" per spec §10, nie zrobione; sankeySDR/Poranny/Popołudniowy;
    godzinowaRelacje/Ciężkie; profilKategorie) generowany jest JEDEN wspólny plik na cały
    projekt (`generuj_placeholder.py`, już istniejący z Etapu 2), reużywany przez wszystkie
    punkty — nie osobny szary prostokąt na punkt. `sankeyUPC` = ten sam plik co `sankeySDR`
    (jawna reguła ze spec, nie ogólny fallback). `wykresPoryDoby` NATOMIAST jest **prawdziwy,
    per-punkt**, liczony z `punkt.obliczenia.poryDoby` przez istniejący
    `generuj_wykres_pory_doby.py`. `zdjecieKamery`/`schematSkrzyzowania`: realny upload z
    kroku 6 jeśli jest, inaczej wspólny placeholder "nie wgrano".
  - **Dwa wykresy zbiorcze rozdziału 4** (`r_zestawienie_sdr.png`, `r_szczyty_projektu.png`
    — te same które naprawiałem wcześniej w tej sesji, patrz "Naprawione bugi" wyżej) też
    generowane w kroku 11, bo `budujRaport.js` odwołuje się do nich pod stałą ścieżką
    niezależnie od N. **Ten krok został pominięty w pierwszym podejściu i złapany dopiero
    przez faktyczne uruchomienie generowania w przeglądarce** (ENOENT) — nie przez czytanie
    kodu z góry.
  - **Ograniczenie: tylko PNG.** `probaRozmiaru.js` (Etap 2) czyta wymiary z nagłówka IHDR
    PNG, nic innego. Krok 6 UI teraz wymusza `accept="image/png"` + serwer odrzuca
    (400) rozszerzenia inne niż `.png` przy uploadzie — wcześniej (poprzednia tura)
    dopuszczał dowolny `image/*`, co wysypywałoby krok 11 na zdjęciu z telefonu w JPG.
  - Pobieranie: `GET /api/projekty/:id/raport.docx` (Content-Disposition attachment).
- **Naprawione 2 błędy DOM złapane dopiero przez pełny test w przeglądarce** (nie przez
  strukturalne testy API) — oba tej samej rodziny: handler zapisywał stan, wywoływał
  `pokazStatus()`, POTEM `wyrenderujWizard()`/`wyrenderujPanelPunktu()`, który **nadpisuje
  cały DOM i usuwa komunikat zanim użytkownik zdąży go zobaczyć** (a w drugim przypadku —
  zanim jakikolwiek zależny element się przeliczy):
  1. Krok 2/4/6: "Zapisano ✓" nigdy realnie niewidoczne — poprawka: rerender PRZED
     `pokazStatus()`, zawsze na ŚWIEŻO pobranym elemencie (stary DOM node jest odłączony).
  2. **Poważniejszy**: po zapisaniu mapowania (krok 5) przycisk "Uruchom obliczenia"
     (krok 7) zostawał trwale `disabled`, mimo poprawnego zapisu — bo handler kroku 5
     patchował tylko `#wynik-walidacji`, nie przerenderowywał całego panelu punktu, więc
     atrybut `disabled` (liczony raz, przy renderze szablonu, z `pkt.qc`) nigdy się nie
     odświeżał. Analogicznie krok 7→11: sekcja "Generuj raport" (poziom projektu) nie
     wiedziała że obliczenia się pojawiły, dopóki użytkownik nie przełączył punktu. Oba
     naprawione pełnym rerenderem (`wyrenderujPanelPunktu()` / `wyrenderujWizard()`) po
     udanym zapisie zamiast punktowego patcha DOM. **Wniosek na przyszłość:** żaden test
     strukturalny/API nie złapałby tego — złapane wyłącznie przez odtworzenie PEŁNEJ ścieżki
     klikania w prawdziwej przeglądarce (Playwright) od kroku 1 do 11 na czysto.
- **Rozjazd modelu danych** `projekt.json` (spec v2) vs fixture `budujRaport.js` — udokumentowany
  wyżej przy kroku 11, teraz z konkretnym mostem (`zbudujRaport()`), nie tylko opisem problemu.

---

## Konwersja History.csv → Quantity.csv + model "bramka→wlot" 🟢 GOTOWE

Na prośbę użytkownika (wcześniej robione ręcznie makrem VBA w Excelu) — panel przyjmuje
teraz surowy `History.csv` (jeden wiersz = jedna detekcja pojazdu z AISP) ALBO już
zagregowany `Quantity.csv`, konwertując pierwszy na drugi automatycznie przy uploadzie
(krok 3). Reguła (potwierdzona z użytkownikiem): tylko wiersze `Validated == 1`; wiersze
zwalidowane, ale z niepełnym śladem pojazdu (jedna bramka zamiast dwóch) są pomijane —
**potwierdzone przez użytkownika że tak samo robił stary makro VBA** ("Też je pomijałem").

**Kluczowe odkrycie zweryfikowane z użytkownikiem**: prawdziwy `Quantity.csv` (w
`dane-do-raportu/`) ma format `Kod;Godz;...` gdzie `Kod` to DWULITEROWY kod relacji (np.
"A-E"), różny od `drogi/Quantity.csv` (`Kierunek;Czas;...`, pojedyncza litera = cała
relacja) który dotąd służył jako fixture testowy. Wyjaśnienie użytkownika: **pojedyncza
litera to jedna fizyczna bramka/wlot** skrzyżowania (nie cała relacja) — para "A-E" =
wjazd bramką A, wyjazd bramką E. To zmienia model mapowania w kroku 5: zamiast klikać
wlot+manewr dla każdej relacji, wystarczy przypisać stronę świata każdej POJEDYNCZEJ
bramce — manewr wynika GEOMETRYCZNIE z pary wlot_wejścia/wlot_wyjścia.

**1. Konwersja `panel/silnik/konwersja_history.py::konwertuj_history_na_quantity()`**
— czysta funkcja pandas. Kod relacji = pierwsza i ostatnia bramka kolumny
`CrossSection` (Python-list-string) po zredukowaniu powtórzeń pod rząd. Etykiety
`a1.rowery`/`a3.hulajnogi`/`i1.piesi`/`i2.piesi.potrzeby` przemianowane na nazwy kolumn
Quantity — pozostałe 8 kategorii już pasują 1:1. CLI: `uruchom_konwersje_history.py`.

**2. Model "bramka→wlot" w silniku:**
- `panel/silnik/opisy.py::oblicz_manewr(wlot_wejscia, wlot_wyjscia)` — odwrotność
  istniejącej `_exit_bearing()`, wyprowadzona i zweryfikowana algebraicznie dla
  wszystkich 16 kombinacji (wlot×manewr): diff namiaru 0°→Zawracający, 90°→Lewo,
  180°→Wprost, 270°→Prawo.
- `panel/silnik/mapowanie.py`: nowe `rozbij_relacje()` ("A-E"→("A","E")),
  `waliduj_bramki()`, `zmapuj_relacje_z_bramek()` (jak `zmapuj_kierunki()`, ale wejściem
  jest mapowanie POJEDYNCZYCH bramek na wloty, manewr liczony geometrycznie). Stare
  `zmapuj_kierunki()`/`kierunek_mapping` CELOWO nietknięte — nadal używane przez
  `test_integracja_quantity.py` i `drogi/Quantity.csv`, żeby nie zepsuć istniejącej,
  już zweryfikowanej ścieżki Etapu 1.
- `wczytaj_surowe_csv()` rozpoznaje teraz OBA warianty nazw kolumn (`Kierunek`/`Czas`
  ORAZ `Kod`/`Godz`), normalizuje wewnętrznie do pierwszego.
- 17 nowych testów (`test_opisy.py`, `test_mapowanie.py`, `test_konwersja_history.py`)
  — **49/49 testów silnika przechodzi łącznie**.

**3. UI (Etap 4) przebudowane pod nowy model:**
- Krok 3 (`server.js`): auto-wykrywanie formatu po nagłówku (`CrossSection`+`Validated`
  = History) → konwersja server-side przez subprocess Pythona PRZED zapisem na dysk;
  kamera dostaje flagę `skonwertowanoZHistory` (widoczna w UI). `liczbaLiter`/
  `przesuniecieLiter` liczone teraz w przestrzeni BRAMEK (nie surowych wartości kolumny)
  — `bramkiZWartosci()` rozbija każdą parę "X-Y" na pojedyncze litery.
- Krok 5 UI (`wizard.js`): tabela zredukowana do 3 kolumn (Bramka | Pochodzenie | Wlot)
  — kolumna Manewr USUNIĘTA, bo liczy się automatycznie. Endpoint zmieniony z
  `/litery-efektywne` na `/dane-mapowania` (zwraca `{bramki, relacje, wlotyMozliwe}` —
  `relacje` to zestaw przesuniętych par "X-Y" używany wyłącznie do wykrywania
  duplikatów, nie renderowany jako osobna tabela). `punkt.kierunekMapping` →
  `punkt.bramkiMapping` (teraz `{bramka: wlot}`, płaski string zamiast `{wlot,manewr}`)
  — zmiana nazwy pola w całym stosie (server.js, wizard.js, skeleton punktu).
  `qc.literyNiezmapowane` → `qc.bramkiNiezmapowane`; `qc.duplikatyRelacji[].litery` →
  `.relacje` (lista par "X-Y", nie pojedynczych liter).
- `server.js::obliczManewr()` — port BEARING-diff logiki 1:1 z Pythona (musi zostać
  bit-identyczny, oba miejsca skomentowane z odnośnikiem do siebie) — używany w
  `zwalidujMapowanie()` do wykrywania duplikatów (różne pary bramek mapujące się na tę
  samą (wlot,manewr) — geometryczny odpowiednik starych "zdublowanych etykiet AISP").
- `panel/silnik/uruchom_dla_punktu.py` (krok 7): przepisany na
  `zmapuj_relacje_z_bramek()` + `punkt["bramkiMapping"]`. `przesun_bramke()`/
  `przesun_relacje()` zastąpiły stare `przesun_litere()` — przesuwają OBIE bramki pary
  niezależnie ("A-E"→"A'-E'"), nie całą wartość jako jeden znak.

**Zweryfikowane end-to-end na PRAWDZIWYM `dane-do-raportu/History.csv`** (33 703
surowych wierszy) przez pełny przepływ przeglądarki: upload History.csv → auto-wykryty
i skonwertowany server-side (widoczne "(z History.csv)" w tabeli) → krok 5 pokazuje
6 bramek A-F (nie pary!) → zapis mapowania poprawnie wykrywa geometryczne duplikaty →
krok 7 liczy **SDR=26 836, dokładnie zgodnie** z niezależnym ręcznym wyliczeniem tą samą
metodą w Pythonie podczas analizy plików (patrz wyżej) → zero błędów konsoli.

**Zweryfikowane na PRAWDZIWEJ topologii skrzyżowania** (opisanej przez użytkownika po
obejrzeniu `dane-do-raportu/preview.png`): skrzyżowanie Włocławska (mniejsza, prosta para
D=PN/B=PD, jedna bramka na wlot) × Łódzka (większa, osobne bramki na dwa kierunki przez
ten sam wlot: C=WSCH i E=WSCH, A=ZACH i F=ZACH). Z tym mapowaniem `oblicz_manewr()` daje
DOKŁADNIE oczekiwane przez użytkownika wyniki (D-C=Lewo, D-F=Prawo — wcześniej zgłoszone
jako "znalezione jako jedno" przy błędnym mapowaniu testowym autora, nie przy prawdziwym)
i pełny przebieg silnika na `History.csv` daje 14 sensownych relacji, dominację WSCH↔ZACH
na wprost 88,6% — niemal dokładnie zgodne z wcześniej znaną wartością 88,7% z
referencyjnego `Raport_Torun_Orange_v3.docx` dla TEGO SAMEGO skrzyżowania (Punkt 1,
Łódzka/Włocławska). **Wniosek: model "wiele bramek → jeden wlot" (osobna bramka na wjazd
i wyjazd tej samej ulicy) już działał poprawnie bez żadnych zmian w kodzie** — wcześniej
zgłoszony "błąd" wynikał z przypadkowo złego mapowania w moim własnym teście, nie z wady
algorytmu. Jedyna zmiana: doprecyzowana podpowiedź w UI kroku 5 (wizard.js), że kilka
bramek może wskazywać na ten sam wlot — to normalne dla szerszych ulic z osobnymi
kamerami/bramkami na wjazd i wyjazd.

**Świadomie NIE zrobione:**
- Stary model `kierunekMapping`/`zmapuj_kierunki()` (pojedyncza litera = cała relacja)
  zostawiony nietknięty dla `drogi/Quantity.csv`/testów Etapu 1 — nowe projekty
  tworzone przez wizard UI używają WYŁĄCZNIE nowego modelu bramek, nie ma przełącznika
  trybu w UI (uznane za niepotrzebne — realny format AISP to zawsze pary bramek).

---

## Auto-wykrywanie daty pomiaru z pliku 🟢 GOTOWE

Na prośbę użytkownika ("data od do... może zaciągać się z daty z pliku history? Tam to
jest podane już przecież") — data pomiaru nie jest już wpisywana ręcznie:

- `server.js::wykryjDatePomiaru()` czyta datę z drugiej kolumny (Czas/Godz) pierwszego
  wiersza danych przy uploadzie (krok 3) — eksport AISP to zawsze pełny cykl dobowy
  jednego dnia (spec §5.1), więc jeden wiersz wystarczy. Zwracana w odpowiedzi endpointu
  `/kamery` jako `dataWykryta`.
- Krok 4 UI: `metadanePomiaru.dataPomiaru` I `dzienTygodnia` wypełniają się automatycznie
  po uploadzie (tylko jeśli jeszcze puste — nie nadpisuje ręcznej korekty). Format dnia
  tygodnia (`wizard.js::dzienTygodniaZDaty()`) dokładnie jak w referencyjnym raporcie:
  "Czwartek (dzień roboczy)".
- Krok 1 UI: `metadaneProjektu.dataOd/dataDo` przeliczają się automatycznie jako min/max
  dat pomiaru WSZYSTKICH punktów (`wizard.js::przeliczZakresDatProjektu()`) po każdym
  uploadzie — pole zostaje edytowalne, ale nie jest już wymagane przy tworzeniu projektu
  (`required` usunięty z formularza "Nowy projekt" — data i tak przyjdzie z pliku).
- Zweryfikowane end-to-end na realnym `History.csv` (data 2026-05-28, czwartek) —
  krok 4 i krok 1 wypełniły się poprawnie bez żadnego ręcznego wpisywania daty, zero
  błędów konsoli.

---

## Generowanie wynik_tabele_Punkt{N}_{ID}.xlsx 🟢 GOTOWE

Użytkownik zauważył: "czy to wynik_tabele_Punkt1_P1.xlsx się gdzieś tworzy i zapisuje?"
— **odpowiedź brzmiała NIE**. Raport Word (`budujPunkt.js`/`budujRaport.js`) od dawna
obiecuje w tekście "pełna godzinowa struktura... dostępna wyłącznie w załączonym pliku
xlsx" i wylicza nazwę pliku w rozdziale 5 (Literatura), ale nic w całym `panel/` nigdy
faktycznie nie generowało tego pliku — pusta obietnica w tekście.

**Naprawione:** nowy `panel/silnik/eksportuj_wynik_tabele.py` — buduje xlsx z 5 arkuszami
zgodnie z `raport-reguly-obliczen-i-danych.md` §1: "Parametry pomiaru", "Ruch wg
kierunkow", "Pory doby", "Struktura rodzajowa" (wszystkie z już policzonego
`punkt.obliczenia`) i **"Godzinowa szczegolowa"** — GŁÓWNY arkusz (Wlot, Kierunek, Opis
relacji, Godz + 12 kategorii, jeden wiersz na wlot×manewr×godzinę), zbudowany z tego
samego `df_mapped` co krok 7 (`wczytaj_i_zmapuj_punkt()`, wspólna funkcja) — więc dane w
xlsx są DOKŁADNIE tym samym źródłem co liczby w raporcie Word, nie osobnym przeliczeniem.

- Nowa zależność **`openpyxl`** (czysty Python, brak kompilacji — bezpieczne nawet bez
  uprawnień admina) dodana do `panel/requirements.txt`.
- Wołane w `server.js::zbudujRaport()` (krok 11) per punkt, zapisywane do
  `build/wynik_tabele_Punkt{numer}_{id}.xlsx` — best-effort (błąd nie blokuje reszty
  raportu, tylko loguje).
- Nowy endpoint `GET /api/projekty/:id/wynik-tabele/:nazwa.xlsx` (pobieranie) + krok 11
  UI pokazuje linki do wszystkich wygenerowanych załączników obok linku do `.docx`.
- 2 testy w `panel/tests/test_eksportuj_wynik_tabele.py` (51/51 testów silnika łącznie).
- Zweryfikowane end-to-end na realnym `History.csv`: 266 wierszy w "Godzinowa
  szczegolowa", plik pobiera się poprawnie przez nowy endpoint, wszystkie 5 arkuszy
  obecne i wypełnione.

---

## Nazwa folderu projektu + naprawa ryzyka utraty danych 🟢 GOTOWE

Użytkownik zauważył: "po restarcie serwera muszę zaczynać wszystko od nowa, to
potencjalne ryzyko utraty postępu prac". **Persystencja już działała** (`projekt.json`
+ wszystkie CSV/zdjęcia/wykresy zapisywane na dysk po każdym kroku, patrz struktura
niżej) — ale realne ryzyko utraty danych ISTNIAŁO z zupełnie innego powodu: **w tej
sesji wielokrotnie czyściłem `panel/ui/projekty/*` po własnych testach E2E, w TYM
SAMYM folderze gdzie realnie ląduje praca użytkownika** — to najpewniej skasowało jego
prawdziwy projekt "Toruń" z wcześniejszej tury. To błąd w mojej praktyce testowania, nie
wada architektury.

**Naprawione:**
1. `PROJEKTY_DIR` w `server.js` nadpisywalne zmienną środowiskową `PROJEKTY_DIR` —
   od teraz WŁASNE testy E2E uruchamiam z `PROJEKTY_DIR=/tmp/...` (izolowany katalog),
   nigdy więcej nie czyszczę `panel/ui/projekty/` w miejscu gdzie ląduje prawdziwa
   praca użytkownika.
2. **Foldery projektów nazwane po nazwie projektu** (użytkownika: "niech się tworzy
   folder z nazwą projektu"), nie po opornej dacie+hashu — `slugify()` w `server.js`
   (usuwa polskie znaki, w tym osobno obsłużone "ł"/"Ł" bo nie mają dekompozycji NFD —
   złapane przy pierwszym teście: "Łódzka" → błędnie "odzka" zanim to poprawiłem).
   Przykład: "Skrzyżowanie Łódzka / Włocławska" → folder
   `skrzyzowanie-lodzka-wloclawska-35dc1f` (krótki losowy sufiks na wypadek dwóch
   projektów o tej samej nazwie). Lista projektów sortowana teraz po dacie modyfikacji
   pliku (`fs.statSync().mtimeMs`), nie po nazwie id — poprzednie sortowanie
   zakładało że id zaczyna się od daty, co przestało być prawdą.

**Co już (i nadal) zapisuje się na dysk, per projekt** (odpowiedź na "czy możemy
zapisywać wykresy, mapki i json"):
```
panel/ui/projekty/<nazwa-projektu>-<hash>/
  projekt.json              <- CAŁY stan (kroki 1-11, wszystkie pola)
  zrodla/<punktId>/          <- wgrane CSV (History.csv lub Quantity.csv)
  assets/<punktId>/          <- wgrane zdjęcia z kamery / schemat (krok 6)
  build/
    fixture.json             <- kształt gotowy do budujRaport.js
    raport.docx               <- finalny wygenerowany raport
    assets/<punktId>/         <- WSZYSTKIE wygenerowane obrazy: mapka lokalizacji,
                                 schemat skrzyżowania, 4x Sankey, wykres pór doby
                                 (wszystko z kroku 11 opisanego wyżej)
```
Nic z tego nie ginie przy restarcie serwera — jedyne co nie przetrwa to stan
niezapisanego formularza w przeglądarce (pól, które user wypełnił ale jeszcze nie
kliknął żadnego przycisku "Zapisz") — to normalne dla każdej appki webowej bez
autosave-na-każde-naciśnięcie-klawisza, nie specyficzne dla tego panelu.

---

## Auto-wykrywanie warunków atmosferycznych 🟢 GOTOWE

Na prośbę użytkownika ("ciężko wpisać z klawiatury stopnie Celsjusza... czy możemy jakoś
automatycznie sprawdzać jaka była pogoda") — `server.js::wykryjPogode()` woła
**Open-Meteo Archive API** (historyczne dane pogodowe, **bez klucza/rejestracji** —
tak jak OSM dla map, zero nowej zależności npm, tylko wbudowany `fetch` w Node 22) dla
`punkt.lokalizacja` (krok 2) + `metadanePomiaru.dataPomiaru` (krok 4, już auto-wykrytej z
pliku), zwraca średnią temperaturę dobową i sumę opadów sformatowane jako
`"bez opadów, temperatura ok. +15°C"` (dokładnie styl z referencyjnego raportu).

- Endpoint `POST /punkty/:numer/wykryj-pogode`.
- Krok 4 UI: przycisk "Wykryj automatycznie" obok pola (disabled dopóki brak
  współrzędnych LUB daty pomiaru).
- **Też w pełni automatyczne**: od razu po uploadzie CSV (krok 3), jeśli współrzędne są
  już wypełnione (krok 2) i pole warunków jest puste, próbuje dociągnąć pogodę cicho w
  tle (best-effort — brak sukcesu, np. brak współrzędnych, nie przerywa uploadu; user i
  tak ma przycisk ręczny do retry).
- Zweryfikowane end-to-end na realnych koordynatach+dacie Punktu 1 — zarówno auto-wywołanie
  po uploadzie jak i ręczny przycisk zwróciły identyczny, poprawny wynik. Zero błędów.

---

## Podpięcie realnych generatorów map/Sankey (mapka, schemat, R4-R7) 🟢 GOTOWE

**Były już napisane i działające — po prostu przeoczone przy budowie kroku 11**
(użytkownik: "dlaczego jest napisane wszędzie że generator w przygotowaniu skoro te
skrypty już działały?"). Trzy istniejące, niezależnie napisane skrypty (poza `panel/`,
w `Generaotr-mapy-skrzyzowania/` i `generator-mapek/`) używają OSM (przez `osmnx`,
zależność już w `generator-mapek/venv`) do auto-rozpoznania geometrii skrzyżowania z
samych współrzędnych — dokładnie ten kierunek, o którym użytkownik wspominał wcześniej
("Generujemy mapkę która z koordynatów potrafi rozpoznać skrzyżowanie i jego wloty").

**1. `generator-mapek/generate_map.py`** (R1, mapka lokalizacji) — `--lat --lon
--output`, granica miasta + pinezka. **2. `Generaotr-mapy-skrzyzowania/
generate_intersection_map.py`** (R2, schemat skrzyżowania) — `--lat --lon --output`,
auto-wykrywa realne ramiona skrzyżowania z grafu dróg OSM (`find_arms()`), etykietuje
PRAWDZIWYMI nazwami ulic + auto-obliczonym kierunkiem geograficznym (np. "Łódzka – Wlot
Wschodni"). **3. `Generaotr-mapy-skrzyzowania/generate_flow_diagram.py`** (R4-R7,
diagramy Sankey SDR/UPC/szczyt poranny/popołudniowy) — nakłada grubość/kolor wstęg na
tę samą geometrię wg wartości z danych; wymaga `--csv` (Quantity.csv, STARY format
pojedyncza-litera-na-relację) + `--mapping` (JSON: `gate_mapping` litera→[wlot,manewr]
+ `wlot_to_arm_direction` nasz-kod→wykryta-etykieta-ramienia).

**Nowe elementy dopisane, żeby spiąć nowy model bramek z tymi (starszymi) skryptami:**
- `panel/silnik/eksportuj_relacje_synth.py` — bierze już POLICZONE (wlot,manewr,
  Godzina,kategorie) z `df_mapped` (ta sama funkcja `wczytaj_i_zmapuj_punkt()` co krok 7,
  wydzielona z `uruchom_dla_punktu.py` do wspólnego użytku) i re-etykietuje każdą
  unikalną (wlot,manewr) syntetyczną literą A,B,C... — zamiast przerabiać
  `generate_flow_diagram.py` pod nowy model, po prostu karmi go formatem jaki już zna.
- `Generaotr-mapy-skrzyzowania/wykryj_wloty.py` (nowy) — woła `find_arms()` z
  `generate_intersection_map.py` (import, nie duplikacja), dopasowuje nasze 4 kanoniczne
  kody (PN/WSCH/PD/ZACH, azymuty 0/90/180/270) do najbliższych azymutem REALNIE
  wykrytych ramion — **w pełni automatyczne, zero ręcznego wpisywania przez
  użytkownika** czegokolwiek poza tym co już wpisał w kroku 5.
- `server.js::spróbujWygenerowacRealneRysunki()` — w kroku 11, dla każdego punktu z
  wypełnionymi współrzędnymi (`punkt.lokalizacja`, krok 2): generuje mapkę + schemat +
  (via eksport + wykrycie wlotów) 4 diagramy Sankey. Priorytet assetów: **ręczny upload
  (krok 6) > realnie wygenerowany z koordynatów > placeholder wspólny**. Każdy z 6
  rysunków generowany NIEZALEŻNIE w try/catch — błąd jednego (brak sieci, brak dróg w
  zcache'owanym regionie) nie blokuje pozostałych ani całego raportu, po prostu ten
  jeden rysunek spada na placeholder.

**Zweryfikowane end-to-end na realnych współrzędnych Punktu 1** (52.99204691558239,
18.642194499056817 — Łódzka/Włocławska) przez pełny przepływ przeglądarki: wygenerowany
raport ma w PDF-ie prawdziwą mapkę Torunia z pinezką, prawdziwy schemat skrzyżowania z
etykietami "Włocławska – Wlot Północny"/"Łódzka – Wlot Wschodni" (dokładnie zgodne z
rzeczywistością), i 4 diagramy Sankey narysowane NA PRAWDZIWEJ mapie OSM z grubością
wstęg proporcjonalną do natężenia (dominujące 12 097/11 669 poj./dobę na Łódzkiej,
widoczne jako najgrubsze pomarańczowe wstęgi). Czas generowania per punkt: rząd
kilkudziesięciu sekund do ~2 min (głównie sieć/OSM przy pierwszym uruchomieniu dla danej
okolicy — kolejne punkty w tym samym mieście korzystają z tego samego `region_cache` i
są szybsze).

**Nadal placeholder (bez zmian w tej turze):** `godzinowaRelacje`/`godzinowaCiezkie`/
`profilKategorie` (R8-R10, kombo-wykresy godzinowe wg relacji/kategorii) — te trzy NIE
mają odpowiednika wśród istniejących skryptów, to inny typ wykresu (rozkład w czasie,
nie geometria przestrzenna) — wymagałyby nowego generatora od zera, nie przeoczenia.

---

## Ogólne braki / rzeczy do potwierdzenia z użytkownikiem

- **Teksty analityczne** (`teksty.lokalizacja`, `teksty.komentarzAnalityczny` itd.) —
  wszędzie placeholder `[SZKIC — do zastąpienia tekstem z Etapu 4/AI]`. Generowanie AI
  to jawnie Etap 4 (krok 8 w spec), nie zaimplementowane.
- **Brakujące generatory obrazków** (placeholdery): R1 mapka lokalizacji (miejska, nie
  skrzyżowaniowa — inna niż nasze istniejące generatory z `Generaotr-mapy-skrzyzowania/`),
  R3 zdjęcie z kamery (i tak ręczny upload), R8/R9/R10 (kombo-wykresy godzinowe wg relacji/
  kategorii — spec podaje specyfikację w §5-6 pliku reguł, nie zaimplementowane).
- **Prawdziwy Microsoft Word nie był użyty do weryfikacji** — całe testowanie wizualne szło
  przez LibreOffice (zainstalowany via `brew install --cask libreoffice` w tej sesji) +
  bezpośrednią inspekcję wygenerowanego XML. Zalecane: sprawdzić w prawdziwym Wordzie
  zanim uzna się formatowanie za w 100% zamknięte.
- **Rozdział 3.n.5** w spec wymaga jednego zdania łączącego zapowiadającego ZARAZEM
  tabelę i rysunek ("Tabela X oraz Rysunek Y przedstawiają...") — zaimplementowane w
  `budujPunkt.js`, sprawdzić czy to nadal pasuje gdy dojdzie właściwy generator R10.

## 2026-09-05 — Formatowanie docx wg zrzutu ekranu użytkownika

Zrealizowano jednorazowe żądanie formatowania (nagłówki, strona tytułowa, page break,
teksty rozdziałów 1-2):

- **Styl nagłówków 1./2./3. i X.Y/X.Y.Z**: pomarańczowy (`FF7900`), pogrubiony, 15pt
  (`size: 30`), z linią (border) na całą szerokość treści strony — ten sam rozmiar dla
  WSZYSTKICH poziomów (bez malejącej hierografii), zgodnie ze screenem użytkownika.
  Zaimplementowane w `panel/docx/style.js` jako `styleNaglowkowDefault` (obiekt
  `{heading1, heading2, heading3}`) i podpięte przez `styles.default.heading1/2/3`
  w `generuj_docx.js` i `test_budujRaport.js`.
  **WAŻNA PUŁAPKA**: pierwsza próba użyła `styles.paragraphStyles: [{id:"Heading1",...}]`
  — to NIE nadpisuje wbudowanego stylu docx.js, tylko dokleja DRUGI wpis
  `<w:style styleId="Heading1">` do `styles.xml` (nieprawidłowy OOXML z duplikatem
  ID) — LibreOffice/Word bierze pierwszy (wbudowany niebieski), więc formatowanie
  wizualnie "nie działało" mimo braku błędów. Właściwe API do nadpisania wbudowanych
  Heading1/2/3 to `styles.default.heading1/heading2/heading3` (typ
  `IDefaultStylesOptions` w `docx` — inny klucz niż `paragraphStyles`). Zweryfikowano
  rozpakowując .docx i grepując `styles.xml` pod kątem duplikatu `w:styleId="Heading1"`.
- **`naglowek()`** w `style.js` przyjmuje teraz `opcje.pageBreakBefore` — użyte w
  `budujPunkt.js` na nagłówku `Punkt N - nazwa` (HEADING_2), więc każdy punkt pomiarowy
  zaczyna się od nowej strony.
- **Strona tytułowa** (`budujStronaTytulowa` w `budujRaport.js`): usunięto linię
  "Punkty pomiarowe: N (...)"; "Wykonawca" zahardkodowany na "Orange Polska S.A."
  (nie czytany z metadanych — było `m.wykonawca`, pole nigdzie nieustawiane w UI,
  martwy odczyt `undefined` w każdym prawdziwym raporcie do tej pory); dodano nowe
  pola "Sporządził" i "Email osoby odpowiedzialnej".
- **Nowe pola metadanych**: `dataSporzadzenia`, `sporzadzil`, `emailOdpowiedzialny`
  dodane do `zbudujSzkielet()` w `server.js` oraz do formularza kroku 1 w `wizard.js`
  (edytowalne po utworzeniu projektu, jak `progAnalizyLacznej`).
- **Rozdział "1. Cel i zakres opracowania"**: dodano zdanie "Przygotowany na zlecenie
  {zamawiajacy}." zaraz po pierwszym akapicie, przed listą punktów pomiarowych.
- **Rozdział "2. Metodologia"**: literówka/spójność "standardem opracowywania" →
  "standardem przetwarzania"; link do wytycznych GDDKiA (`linkWytyczneGDDKiA`) wklejony
  bezpośrednio w zdaniu o kategoryzacji pojazdów (wcześniej link był tylko w rozdziale
  "Literatura", teraz jest w obu miejscach — bez zmian w Literaturze); dodano słowo
  "relacji" ("W tabelach relacji wiersze porządkuje się..."); USUNIĘTO akapit
  "Ograniczenie porównywalności: mapowanie liter AISP..." — nie było w tekście podanym
  przez użytkownika, więc przyjęto że ma zniknąć (do potwierdzenia, jeśli to jednak
  było potrzebne gdzie indziej — np. w sekcji "Uwagi o jakości danych" per-punktowej,
  która jest osobnym miejscem i nie została ruszona).
- Zweryfikowano wizualnie przez LibreOffice → PDF → screenshot (Read na PNG) — strona
  tytułowa, rozdziały 1-2, nagłówek 3.1/3.1.1 z linią i kolorem. `pytest panel/tests`
  (51 testów) i oba `node test_budujPunkt.js`/`test_budujRaport.js` przechodzą bez zmian.
- **Nadal jako placeholder / nieruszone**: zdjęcia z kamer, mapka/schemat gdy brak
  współrzędnych, `[NAZWA ZAMAWIAJĄCEGO]`/`[DATA SPORZĄDZENIA]` nadal jako literały
  dopóki użytkownik ich nie wypełni w kroku 1 UI — to zamierzone (placeholder widoczny
  w gotowym .docx, nie ukryty błąd).

## 2026-09-05 (cd.) — 3 poprawki po przeglądzie użytkownika

- **Logo na stronie tytułowej praktycznie niewidoczne**: `budujStronaTytulowa()`
  liczyła `transformation: { width: w / 9525, ... }` z `w = 1200`, czyli traktowała
  `w` jak EMU (wzorem `obrazek()` w `style.js`, który faktycznie oczekuje EMU) — ale
  docx.js `ImageRun.transformation` przyjmuje PIKSELE wprost (patrz
  `branding.js::budujHeader`, `width: w` bez dzielenia, `w = 60`). Efekt: obrazek
  renderował się jako ok. 0,13 px — na wcześniejszym screenie PDF widoczny tylko jako
  kropka, błędnie zinterpretowany jako "brak logo". Naprawione: `width: w, height: h`
  bez dzielenia przez 9525, `w = 200` (px).
- Literówki wskazane przez użytkownika: "niezmotoryzowanym" → "nie zmotoryzowanym"
  (Metodologia, `budujRaport.js`), "mapką" → "mapą" (Tabela 3.n.1, `budujPunkt.js`)
  — poprawione TYLKO w tych dwóch konkretnych zdaniach widocznych na
  zrecenzowanych stronach, nie globalnie (inne wystąpienia "niezmotoryzowan-"
  w kodzie to inne zdania/kontekst, nieporuszone).
- **Rozdział 1 nadal miał listę punktów pomiarowych** mimo że nie było jej w
  dokładnym tekście podanym przez użytkownika w poprzedniej turze — usunięto
  akapit zapowiadający i pętlę `punktOwyBullet()` z `budujCelIZakres()` (funkcja
  `punktOwyBullet` zostaje, bo nadal używana w rozdziale Literatura/Załączniki dla
  listy plików xlsx).
- Zweryfikowano ponownie przez LibreOffice → PDF → screenshot: logo widoczne i
  proporcjonalne, oba teksty poprawione, rozdział 1 bez listy. `pytest` (51) i oba
  testy JS nadal przechodzą.

## 2026-09-05 (cd. 2) — Wykres godzinowy temperatury/opadów (nowy Rysunek 3.n.2)

Użytkownik: skoro warunki atmosferyczne pobierają się już godzinowo z Open-Meteo dla
dokładnej daty pomiaru (patrz `wykryjPogode()`), można to samo źródło pociągnąć o
`hourly=` zamiast tylko `daily=` i narysować wykres liniowy dla 24h pomiaru.

- **`wykryjPogodeGodzinowo(lat, lon, data)`** (nowa, `server.js`, obok istniejącej
  `wykryjPogode()`) — to samo Archive API, `hourly=temperature_2m,precipitation`
  zamiast `daily=...`, zwraca `{godziny: ["00:00",...], temperatura: [24], opady: [24]}`.
- **`panel/docx/generuj_wykres_pogoda.py`** (nowy) — wykres matplotlib: linia
  temperatury (pomarańczowa, oś lewa) + słupki opadów w tle (grafit, przezroczyste,
  oś prawa przeskalowana ×3 żeby słupki nie zasłaniały linii) — wzorem
  `generuj_wykres_pory_doby.py`.
  Zweryfikowano na realnych danych Open-Meteo dla Torunia/2026-05-27.
- **Wpięcie**: nowy krok w `spróbujWygenerowacRealneRysunki()` (server.js) —
  best-effort, wymaga `punkt.lokalizacja` ORAZ `punkt.metadanePomiaru.dataPomiaru`
  (w przeciwieństwie do mapki/schematu/sankeyów, którym wystarczy sama lokalizacja).
  Nowy klucz assetu `wykresPogoda` w `PLACEHOLDERY_WSPOLNE` i w `punktyFixture.assets`
  (priorytet: brak ręcznego uploadu dla tego typu → realny → placeholder, jak reszta).
- **`budujPunkt.js`**: nowy `dodajRysunek("wykresPogoda", ...)` wstawiony PRZED
  `dodajRysunek("schematSkrzyzowania", ...)` w §3.n.1 — automatycznie staje się
  Rysunek 3.n.2 (mapa lokalizacji=1), przesuwając schemat/kamerę o +1 (numeracja
  jest w pełni automatyczna przez `Liczniki`, nie trzeba nic przeliczać ręcznie).
  Zapowiedź: "Rysunek X przedstawia przebieg temperatury i opadów w trakcie
  pomiaru.", podpis: "Rysunek X. Przebieg warunków atmosferycznych (temperatura,
  opady) - {nazwa punktu}." — dokładnie wg wzorca podanego przez użytkownika.
- **Liczba rysunków na punkt: 11 → 12** (R1-R12) — zaktualizowane asercje w
  `test_budujPunkt.js`/`test_budujRaport.js` oraz dodany klucz `wykresPogoda` do
  wszystkich 3 fixture'ów testowych (`punkt2_fixture.json`, `projekt_fixture.json`,
  `projekt_fixture_3punkty.json`), wskazujący na reużyty istniejący placeholder PNG
  (`placeholder_r1_mapka.png` — testy nie biją do prawdziwego API, więc obojętne
  jaki obrazek, liczy się tylko że klucz istnieje).
- Zweryfikowano: realne zapytanie do Open-Meteo hourly + wygenerowany wykres
  (wizualnie OK), oraz pełny .docx → PDF → screenshot pokazujący poprawną
  zapowiedź/podpis/numerację w kontekście całego rozdziału. `pytest` (51) i oba
  testy JS (12 rysunków) przechodzą.

## 2026-09-05 (cd. 3) — Naprawa: stary proces serwera + brakujące wykresy + analiza łączna

**Zgłoszony błąd 500** przy generowaniu: przyczyna to NIE bug, tylko stary proces
`node server.js` (sprzed dodania `wykresPogoda`), który budował `fixture.json` bez
tego klucza w `assets`, podczas gdy świeżo odpalany `generuj_docx.js` (osobny
proces node, zawsze aktualny kod z dysku) już go oczekiwał. **Node nie
hot-reloaduje** — każda zmiana w `server.js` (nie w `panel/docx/*`, te są
odpalane jako świeży proces za każdym razem) wymaga ręcznego restartu.
Przy okazji zabezpieczono dwa miejsca przed `undefined` w starszych
`projekt.json` sprzed dodania `dataSporzadzenia`/`sporzadzil`/`emailOdpowiedzialny`:
`wizard.js` (renderowało literalne `value="undefined"` w polu daty) i
`budujStronaTytulowa()` (`TextRun({text: undefined})`).

**Brakujące wykresy — dodane 3 nowe realne generatory:**
- **`panel/silnik/eksportuj_godzinowe_relacje.py`** (nowy) — `obliczenia` miało
  tylko sumy dobowe per relacja, nigdy godzinowe; ten skrypt liczy z surowego
  CSV (jak `eksportuj_wynik_tabele.py`) serie 24h osobno dla ruchu zmotoryzowanego
  i ciężkiego, per (wlot, manewr). Test: `test_eksportuj_godzinowe_relacje.py`.
- **`panel/docx/generuj_wykres_godzinowy_relacje.py`** — wykres wieloliniowy
  (1 linia/relacja), używany 2x: Rysunek 3.n.3 ("...według relacji", klucz
  `relacjeZmot`) i 3.n.4 ("...ciężkich według relacji", klucz `relacjeCiezkie`).
- **`panel/docx/generuj_wykres_profil_kategorie.py`** — Rysunek 3.n.5, dwie osie
  (zmot/nie zmot) jak `generuj_wykres_pogoda.py` — reużywa `obliczenia.godzinowa`,
  BEZ nowego eksportu (te dane już istniały, tylko nic ich nie rysowało).
- Wpięte w `zbudujRaport()` (server.js) w pętli per-punkt: profilKategorie
  bezwarunkowo (jak `wykresPoryDoby`, nigdy nie zawodzi — czyste dane z JSON),
  godzinowaRelacje/godzinowaCiezkie w try/catch (jak xlsx — zależą od świeżego
  odczytu CSV, mogą się nie udać). Placeholdery w `PLACEHOLDERY_WSPOLNE`
  przeredagowane: wszystkie mają teraz realny generator, więc tekst placeholdera
  zmienił się z "generator w przygotowaniu" na "nie udało się wygenerować" —
  stary tekst był już nieaktualny (kłamał) dla mapki/schematu/sankeyów, które
  realny generator miały od poprzedniej sesji.

**Analiza łączna (rozdział 4 "Podsumowanie") — 3 poziomy zamiast 2:**
- **N = 1**: NOWY przypadek — rozdział kończy się jednym zdaniem wyjaśniającym
  że analiza łączna nie ma zastosowania, od razu "Wnioski i rekomendacje".
  Wcześniej N=1 przechodziło przez tryb pełny i renderowało bezsensowną tabelę
  zbiorczą z 1 wierszem oraz tabelę struktury rodzajowej z 1 kolumną danych.
- **1 < N ≤ `progAnalizyLacznej`** (domyślnie 15): tryb pełny, bez zmian
  (Tabela 4.1/4.2, Rysunek 4.1/4.2 - zestawienie punktów i struktura rodzajowa).
- **N > próg**: tryb zagregowany, DOKOŃCZONY (wcześniej to było jedno zdanie
  placeholder "zaplanowane, nie zaimplementowane"). Teraz: statystyki opisowe
  SDR (min/max/średnia/mediana, rule-based tekst w `budujRaport.js`, bez AI),
  Tabela 4.1/4.2 = Top/Dół `min(10, floor(N/2))` punktów wg SDR (z poprawną
  polską odmianą "1 punkt"/"2 punkty"/"5 punktów" — `odmianaPunktow()`),
  Rysunek 4.1 = histogram SDR (`generuj_wykres_histogram_sdr.py`, nowy),
  Tabela 4.3 = segmentacja wg `punkt.typ` (skrzyzowanie/rondo/tranzyt/rejestracja)
  — tylko gdy w projekcie występuje więcej niż 1 typ. Pominięto "mapę projektu"
  z pierwotnego opisu placeholdera — wymagałaby nowego geoprzestrzennego
  generatora, poza zakresem tego zadania.
- `server.js`: generowanie wykresów zbiorczych rozdziału 4 (`r_zestawienie_sdr`/
  `r_szczyty_projektu` vs `r_histogram_sdr`) teraz WARUNKOWE wg tych samych
  progów (wcześniej generowały się zawsze, marnując czas w trybie zagregowanym
  gdzie i tak nie były używane — przy okazji też pominięte całkiem dla N=1).
- Zweryfikowano: 52 testy pytest (nowy test eksportu godzinowego), oba testy JS,
  ręczny test trybu zagregowanego z tymczasowym niskim progiem (docx → PDF →
  odczyt tekstu), oraz PEŁNY przebieg przez żywy serwer na realnym projekcie
  `torun-065289` (N=1) - wszystkie 3 nowe wykresy wygenerowały się realnie,
  rozdział 4 poprawnie skrócony.

## 2026-09-05 (cd. 4) — N=1: cały rozdział 4 znika, nie tylko jego treść

Doprecyzowanie poprzedniej zmiany: przy jednym punkcie pomiarowym `budujPodsumowanie()`
zwraca teraz `[]` (żadnego `naglowek("Podsumowanie", ...)`) zamiast nagłówka +
jednozdaniowego wyjaśnienia + "Wnioski i rekomendacje". Dzięki automatycznej
numeracji Worda (naglowek() -> multi-level list, nie ręczne cyfry) "Literatura i
spis załączników" samo staje się wtedy rozdziałem 4 zamiast 5 — zero przeliczania
numerów w kodzie. Zweryfikowane na N=1 (Literatura = "4.") i N=3 (Podsumowanie
nadal "4.", Literatura nadal "5.") przez PDF. Testy (52 pytest + 2 JS) bez zmian.

## 2026-09-05 (cd. 5) — Krok 10: generator tekstów + naprawa martwych pól

Zgłoszenie: "w kroku 10 nie mogę wygenerować tekstów analitycznych". Diagnoza:
Krok 9 (teksty per-punkt) ma generator (Python, `teksty.py`), Krok 10
("Podsumowanie": Wprowadzenie/Porównanie punktów/Wnioski) nigdy go nie miał —
to zawsze były czysto ręczne pola. Gorzej: `zbudujRaport()` w `server.js`
budowało `fixture` bez klucza `podsumowanie` w ogóle (`{ metadaneProjektu,
punkty }`) — więc nawet ręcznie wpisane "Wnioski i rekomendacje" (jedyne pole
teoretycznie już czytane w `budujRaport.js`) NIGDY nie trafiały do docx.
Znalezione przez Playwright (zrzut ekranu całego wizarda) + porównanie ze
strukturą `fixture` w `server.js`.

Naprawione i dobudowane:
- **`panel/docx/analizaLaczna.js`** (nowy, współdzielony JS — bez Pythona,
  dane per punkt już są w `obliczenia` z kroku 7): `odmianaPunktow()`,
  `statystykiSdr()`, `podzialTopIDol()`, `segmentacjaWgTypu()` (wyniesione
  z `budujRaport.js`, tam tylko `require`), plus NOWE `generujTekstWprowadzenie()`
  i `generujTekstPorownanie()` — regułowe (bez AI), jak `teksty.py`.
  Pułapka gramatyczna: "obejmuje N punkty pomiarowych" źle się odmienia dla
  N=2-4 (potrzebne "punkty pomiarowe" nie "pomiarowych") — rozwiązane przez
  przeformułowanie zdania na "obejmuje wyniki DLA N punktów..." - przyimek
  "dla" wymusza dopełniacz niezależnie od liczby, więc "punktów pomiarowych"
  jest zawsze poprawne i nie trzeba w ogóle odmieniać przez liczebnik.
- **`server.js`**: (1) `fixture` dostał brakujący klucz `podsumowanie:
  projekt.podsumowanie`; (2) nowy endpoint `POST .../generuj-podsumowanie`
  (analogiczny do krok9 `generuj-teksty`, ale czysty JS, bez `execFile`) —
  400 gdy N<=1 ("analiza łączna wymaga co najmniej 2 punktów") lub gdy
  któryś punkt nie ma jeszcze `obliczenia`.
- **`budujRaport.js`**: `tekstWnioski`/`tekstWprowadzenie`/`tekstPorownanie`
  czytane teraz z poprawnej zagnieżdżonej ścieżki `podsumowanie.teksty.*`
  (nie `podsumowanie.*` — to była literówka w strukturze, stąd martwe pole).
  Wprowadzenie/Porównanie wstawione jako akapity zaraz po stałym wstępie
  rozdziału, przed rozgałęzieniem tryb pełny/zagregowany.
- **`wizard.js`**: nowy przycisk "Wygeneruj Wprowadzenie i Porównanie punktów"
  w kroku 10 (disabled gdy N<=1 lub brak obliczeń dla któregoś punktu),
  analogiczny UX do przycisku kroku 9. Poprawione dwie już nieaktualne
  podpowiedzi: krok10 (tryb zagregowany był opisany jako niezaimplementowany —
  już jest) i krok11 (R8-R10 opisane jako "zawsze placeholder" — mają już
  generator od poprzedniej zmiany).
- Zweryfikowane: `node -e` bezpośrednio na module (gramatyka dla N=2,3,5),
  pełny przebieg przez izolowany serwer testowy (`PROJEKTY_DIR=/tmp/...`,
  osobny port 4174) z syntetycznym projektem 2-punktowym — endpoint,
  zapis do `projekt.json`, i finalny docx→PDF pokazujący oba nowe akapity
  w rozdziale 4. Dodatkowo uruchomione na PRAWDZIWYM projekcie `torun-065289`
  (który w międzyczasie urósł do 2 punktów) — pola były puste, więc
  bezpiecznie wygenerowano i zapisano prawdziwe teksty. 52 testy pytest bez
  zmian (brak nowych testów Python — cała ta zmiana jest w JS).

## 2026-09-05 (cd. 6) — Większe czcionki na wykresach (×1.7) + reshaping R 3.n.2

Żądanie: czcionki na Rysunkach 3.n.2 (pogoda), 3.n.3/3.n.4 (godzinowe wg relacji),
3.n.5 (profil kategorii) ~1.7x większe; Rysunek 3.n.2 dodatkowo szerszy (pełna
szerokość strony) i niższy (~3/5 poprzedniej wysokości).

- **Szerokość na pełną stronę**: `dodajRysunek()` w `budujPunkt.js` dostał
  opcjonalny 4. parametr `szerokoscCm` (przechodzi do `obrazek()`, domyślnie
  nadal 13cm). Nowa stała `SZEROKOSC_TRESCI_CM` w `style.js`
  (`SZEROKOSC_TRESCI_DXA / 566.93` — dokładna szerokość treści strony w cm,
  wyliczona z marginesów, nie "ładne okrągłe 17") — użyta tylko dla
  `wykresPogoda`. Wysokość w docx to iloczyn tej szerokości i proporcji PNG
  (`obrazek()` liczy wysokość z `height/width` obrazka), więc "niższy" wykres
  = zmiana proporcji samego PNG (figsize), nie osobny parametr wysokości.
- **Fontsize ×1.7**: 11→19 (etykiety osi), 8→14 (etykiety godzin), 7/9→12/15
  (legendy) w `generuj_wykres_pogoda.py`, `generuj_wykres_godzinowy_relacje.py`,
  `generuj_wykres_profil_kategorie.py`.
- **WAŻNA PUŁAPKA matplotlib (dużo prób zanim znaleziono przyczynę)**: przy
  `ax.twinx()` (dwie osie Y, jak w wykresach pogody i profilu kategorii) +
  dużej czcionce, `plt.tight_layout()` ANI `savefig(bbox_inches="tight")`
  osobno NIE dają gwarancji, że etykiety skrajnych osi się zmieszczą —
  ucinały ostatnie znaki (np. "...zmotoryzowany [poj." zamiast "[poj./h]")
  mimo że "tight" sugeruje dopasowanie do zawartości. Zreprodukowane w
  izolacji (`python3 -c` z gołym przykładem twinx+ylabel) — problem znika
  dopiero przy POŁĄCZENIU: `constrained_layout=True` na `plt.subplots()`
  ORAZ `bbox_inches="tight", pad_inches=0.55` na `savefig()` (samo
  `constrained_layout` bez paddingu też jeszcze lekko ucinało przy
  dodatkowo obróconych etykietach godzin). Dodatkowo `fig.legend()`
  (legenda na poziomie figury, nie osi) też pogarszała przycinanie —
  zamienione na `ax2.legend()` (legenda przypisana do konkretnego Axes),
  które `constrained_layout` poprawnie uwzględnia w rezerwacji miejsca.
  Wniosek na przyszłość: każdy nowy wykres z `twinx()` + duża czcionka w tym
  repo powinien od razu używać tego wzorca (`constrained_layout=True` +
  `ax.legend()` + `bbox_inches="tight", pad_inches>=0.5`), inaczej trzeba
  będzie to odkrywać ponownie metodą prób i błędów.
- Zweryfikowano na realnych danych (Open-Meteo + `torun-065289`) każdy z 4
  wykresów osobno (PNG) oraz cały raport przez żywy serwer → PDF → zrzuty
  stron — wszystkie etykiety pełne, bez ucięć, właściwe proporcje R3.n.2.
  `pytest` (52) i oba testy JS bez zmian.

## 2026-09-05 (cd. 7) — Rysunki 3.n.9/3.n.10 też na pełną szerokość strony

Ta sama zmiana co wcześniej dla 3.n.2 (pogoda), teraz dla `godzinowaRelacje` i
`godzinowaCiezkie` — `dodajRysunek(..., SZEROKOSC_TRESCI_CM)` w `budujPunkt.js`
(4. argument, `SZEROKOSC_TRESCI_CM` już zaimportowane z poprzedniej zmiany).
Bez zmian w Pythonie — legenda tych dwóch wykresów jest już poza obszarem
wykresu (`bbox_to_anchor=(1.01, 1.0)`), więc samo powiększenie szerokości w
docx wystarczyło, żadnego przycinania do naprawiania. Zweryfikowane przez
żywy serwer → PDF na `torun-065289`. `pytest` (52) bez zmian.

## 2026-09-05 (cd. 8) — Nagłówek strony za blisko treści

Zgłoszenie ze screenów: pomarańczowa linia pod nagłówkiem strony (logo +
"Raport z pomiaru...") niemal przylegała do treści strony poniżej.
Przyczyna: docx.js domyślne `margin.header` (odległość nagłówka od góry
strony) to 708 twips (0,5"), a nasz `margin.top` (gdzie zaczyna się treść)
to 1134 (2cm) — zostawiało to tylko ~0,75cm na CAŁĄ zawartość nagłówka
(logo+tekst+linia), praktycznie zerowy zapas. Naprawione: `margin.header: 400`
w `generuj_docx.js` i `test_budujRaport.js` — nagłówek siada wyżej na
stronie, więc między jego linią a treścią zostaje realny odstęp, bez
zmiany `margin.top` (paginacja/układ ciała dokumentu bez zmian).
Zweryfikowane PDF-em oraz regeneracją prawdziwego raportu `torun-065289`.
`pytest` (52) i oba testy JS bez zmian.

## 2026-09-05 (cd. 9) — Nagłówek dalej za blisko w prawdziwym Wordzie + "niezmotoryzowany"

Poprzednia poprawka (`margin.header: 400`) dawała widoczny odstęp w LibreOffice
(czym do tej pory weryfikowałem wizualnie), ale użytkownik przesłał zrzuty z
prawdziwego Worda (widoczne czerwone podkreślenia pisowni) pokazujące, że tam
odstęp nadal był praktycznie zerowy — **LibreOffice i MS Word różnie liczą
pozycjonowanie treści nagłówka względem `margin.header`**, więc weryfikacja
samym LibreOffice nie wystarcza dla tego konkretnego ustawienia. Zejście
niżej: `margin.header: 150` (z 400) + mniejsze logo w nagłówku (`branding.js`,
`w: 60→42`) jako podwójny bufor bezpieczeństwa na tę rozbieżność między
silnikami. Nie mam własnego Worda do lokalnej weryfikacji — **wymaga
potwierdzenia przez użytkownika po ponownym pobraniu raportu**.

Przy okazji: "niezmotoryzowany" nadal występowało w kilku miejscach poza tym
jednym zdaniem w Metodologii poprawionym wcześniej — teraz ujednolicone do
"nie zmotoryzowany" wszędzie w tekście widocznym w raporcie: `budujPunkt.js`
(4 zdania + nagłówek kolumny tabeli), `panel/silnik/przypisy.py` (przypisy
jakości danych), `panel/silnik/teksty.py` (3 zdania generowane w kroku 9).
NIE ruszone: nazwy pól danych (`niezmotoryzowany`/`udzialNiezmot` jako klucze
JSON/JS w `obliczenia.py`, `budujPunkt.js`, testach) — to identyfikatory
wewnętrzne, nieczytelne dla użytkownika raportu, zmiana byłaby czystym
przepisywaniem bez korzyści. Zaktualizowano jedną asercję w `test_teksty.py`
dopasowaną do nowego brzmienia. `pytest` (52) i oba testy JS bez zmian.

## 2026-09-05 (cd. 10) — Stylowanie UI + trwałe linki pobierania + ZIP

Cztery drobne prośby UI + jedna realna luka funkcjonalna:

- **Style `input[type=file]`**: brzydki natywny przycisk przeglądarki →
  `::file-selector-button` w `style.css`, pomarańczowy jak reszta przycisków
  (obsługiwane przez wszystkie współczesne przeglądarki, zero JS).
- **`input[type=email]`** dodany do wspólnego selektora stylującego pola
  tekstowe (był pominięty przy dodawaniu tego pola wcześniej w sesji).
- **Generyczne linki** ("← Lista projektów", linki xlsx itd.) — dodano
  bazowy styl `a { color: var(--orange); font-weight: 600; }` + klasa
  `.przycisk-link` (link wyglądający jak `<button>`, potrzebny bo `download`
  wymaga `<a>`, nie `<button>`) + `.blok-pobierania`/`.lista-zalacznikow` dla
  sekcji pobierania.
- **Linki pobierania znikały po odświeżeniu** — bo istniały tylko w pamięci
  przeglądarki (wypełniane JS-em po kliknięciu "Generuj"), nigdy nie
  zapisywane do `projekt.json`. Naprawione: `server.js` zapisuje
  `projekt.raportInfo = {url, zalaczniki, wygenerowanoO}` do projektu przy
  każdym udanym `generuj-raport` (`zapiszProjekt`), więc `GET /api/projekty/:id`
  zwraca to na każde żądanie, nie tylko zaraz po generacji. `wizard.js` renderuje
  blok pobierania z `p.raportInfo` zarówno przy pierwszym wczytaniu strony jak
  i po kliknięciu (funkcja `wyrenderujBlokPobierania()` używana w obu miejscach).
  Dodano widoczną datę/godzinę wygenerowania (`formatujDataCzas()`, `pl-PL`).
- **"Pobierz wszystko" (.zip)**: nowy `panel/ui/zip.js` — ręcznie napisany
  writer ZIP metodą "stored" (bez kompresji — docx/xlsx to i tak już
  skompresowane archiwa, deflate dałby znikome oszczędności), zero zależności
  zewnętrznych (jak reszta `server.js`), CRC32 liczone przez wbudowane w
  Node 22 `zlib.crc32()`. Test `panel/ui/test_zip.js` weryfikuje archiwum
  NIEZALEŻNYM czytnikiem (Python `zipfile`), nie własnym kodem — inaczej test
  i implementacja mogłyby dzielić ten sam błąd formatu. Nowy endpoint
  `GET /api/projekty/:id/pobierz-wszystko.zip` pakuje `raport.docx` + wszystkie
  xlsx z `raportInfo.zalaczniki` na żądanie (bez cache'owania zip na dysku).
- Zweryfikowano: curl (generacja → zapis → GET zwraca to samo → pobranie zip →
  `python3 -m zipfile`/`zipfile.testzip()` bez błędu, 3 pliki poprawnej
  wielkości) oraz Playwright (zrzut całej strony, brak błędów konsoli, HTML
  bloku pobierania zawiera oczekiwane linki i datę). `pytest` (52), oba testy
  JS budujące docx i nowy `test_zip.js` — wszystkie przechodzą.

## 2026-09-05 (cd. 11) — "Pobierz pełny raport" i data pomiaru na liście projektów

Z myślą o docelowo dużym panelu (wiele projektów) — użytkownik nie powinien
musieć otwierać każdego projektu, żeby sprawdzić czy ma dane i pobrać raport.

- **`listaProjektow()`** (server.js) rozszerzone o: `czyGotowyDoRaportu`
  (co najmniej jeden punkt ma ukończone obliczenia — krok 7), `dataPomiaruOd`/
  `dataPomiaruDo` (min/max po `metadanePomiaru.dataPomiaru` wszystkich punktów
  — to samo pole, które krok 3/4 wyciąga automatycznie z History/Quantity.csv,
  tu tylko zagregowane do zakresu), `raportInfo` (przekazane wprost, jeśli
  raport już wygenerowano wcześniej).
- **Lista projektów** (wizard.js landing): każdy wiersz dostał przycisk
  "Pobierz pełny raport" — **disabled dopóki `czyGotowyDoRaportu` jest
  false** (z podpowiedzią w `title` czemu), tekst "Data pomiaru: OD – DO"
  (albo "brak danych pomiaru" gdy żaden punkt jeszcze nie ma daty).
  Kliknięcie woła `POST .../generuj-raport` (buduje/przebudowuje raport na
  bieżąco, nie tylko linkuje do starego pliku) i od razu ustawia
  `window.location.href` na wynikowy URL — dzięki `Content-Disposition:
  attachment` po stronie serwera to czyste pobranie pliku, użytkownik
  zostaje na liście, nie ma przekierowania.
- Zweryfikowano: curl (nowe pola w odpowiedzi API) + Playwright (zrzut listy
  z 2 projektami — jeden gotowy z aktywnym przyciskiem i widoczną datą,
  drugi bez obliczeń z przyciskiem wyszarzonym i "brak danych pomiaru").
  Projekt testowy usunięty po weryfikacji. `pytest` (52) bez zmian.

## Jak uruchomić / kontynuować

```bash
# Etap 1 - testy silnika
cd /Users/jakubchmielewski/Desktop/Orange-apka-raporty-ruchu
generator-mapek/venv/bin/pytest panel/tests -v

# Etap 2 - jeden punkt
cd panel/docx
node test_budujPunkt.js
# -> output/test_punkt2.docx

# Etap 3 - pełny dokument
node test_budujRaport.js
# -> output/raport_pelny.docx (+ kopia z datownikiem w nazwie)

# Podgląd PDF (LibreOffice zainstalowany w tej sesji)
soffice --headless --convert-to pdf --outdir /tmp/podglad output/raport_pelny.docx

# Etap 4 - UI wizard (pełny przepływ krok 1 -> pobranie .docx)
cd ../ui
node server.js
# -> http://localhost:4173 — zero zależności npm, samo `node server.js` wystarczy,
#    projekty lądują w panel/ui/projekty/<id>/ (projekt.json + zrodla/ + assets/ + build/)
```

Dane wejściowe testowe: `panel/docx/dane_testowe/projekt_fixture.json` (owija
`punkt2_fixture.json`, który z kolei zawiera `obliczenia` wyeksportowane z Etapu 1
dla `drogi/Quantity.csv`). Żeby dodać kolejny punkt do testów wielopunktowych: policzyć
`obliczenia` Etapem 1 dla nowego `Quantity.csv`, zbudować analogiczny fixture punktu
(wzorem `punkt2_fixture.json` — metadanePomiaru, wloty, assets, teksty), dopisać do
`projekt_fixture.json.punkty[]`.
