# Specyfikacja: Panel do generowania raportów z pomiaru ruchu drogowego

*Wersja 2 — zaktualizowana po pełnym przejściu wzorcowego raportu Toruń
(3 punkty pomiarowe, iteracyjna korekta struktury aż do stanu
referencyjnego). Wersja 1 tego dokumentu opierała się na wcześniejszych
założeniach (3 szczyty, osobna sekcja jakości danych, brak sekcji
pojazdów ciężkich) — zweryfikowanych i zmienionych w praktyce. Ten
dokument jest teraz zgodny z `raport-specyfikacja-struktura.md` i
`raport-reguly-obliczen-i-danych.md` — te dwa pliki są źródłem prawdy
dla WYGLĄDU raportu; ten plik opisuje jak go ZBUDOWAĆ narzędziem.*

---

## 1. Cel i zakres

Panel automatyzuje ścieżkę **dane AISP → gotowy raport Word**,
zastępując ręczne kroki opisane w checkliście per pomiar (Story 5)
narzędziem z interfejsem użytkownika. Panel nie zastępuje: nagrania
terenowego (proces fizyczny), przetwarzania w samym AISP (wejściem jest
zawsze gotowy eksport AISP), ani docelowego Sankeya w Visum i innych
docelowych generatorów wykresów analitycznych (do czasu ich integracji
panel wstawia **placeholdery wielokrotnego użytku** — patrz sekcja 5.7).

## 2. Architektura ogólna

```
┌─────────────┐     ┌──────────────────────────┐     ┌─────────────┐
│   UI (Web)  │────▶│  Backend processing        │────▶│  DOCX       │
│  wizard     │     │  (Python: pandas/matplotlib│     │  builder    │
│  krok po    │◀────│  + Node: docx)             │◀────│  (Node.js)  │
│  kroku      │     │                            │     │             │
└─────────────┘     └──────────────────────────┘     └─────────────┘
       │                        │
       ▼                        ▼
  Upload plików           Storage projektu:
  (dane AISP, zdjęcia)    /projekty/<id_projektu>/
                            ├── punkty/<ID>/dane_zrodlowe/
                            ├── punkty/<ID>/wynik_tabele_<ID>.xlsx
                            ├── punkty/<ID>/assets/ (wykresy, sankey, mapka, zdjęcie, schemat)
                            ├── projekt.json  (pełny config)
                            └── raport_final.docx
```

Podział na Python (obliczenia, wykresy, walidacje) i Node.js (budowa
`.docx` biblioteką `docx` — sprawdzone na referencyjnym raporcie
Toruń: numeracja wielopoziomowa, style, obrazy, tabele, nagłówek/
stopka, branding) — komunikacja przez wspólny plik `projekt.json`, żeby
żaden krok nie był zależny od stanu w pamięci drugiego procesu, i żeby
dowolny krok dało się przeliczyć/odtworzyć bez przechodzenia całego
wizarda od nowa.

**Ważna zasada budowy docx (poznana empirycznie):** finalny plik
budujemy zawsze jako **jeden, spójny dokument od zera** wygenerowany
programowo z `projekt.json` — nigdy przez kopiowanie/wklejanie gotowych
fragmentów Worda między plikami ani ręczną edycję po fakcie. Ręczna
edycja gotowego pliku (np. dopisywanie nowego punktu przez kopiowanie
sekcji „Punkt 1” i zmianę treści) jest bardzo zawodna: łatwo
przypadkowo zostawić fragment starych danych pod nowym numerem,
zdublować lub przesunąć numerację rysunków/tabel, rozjechać strukturę
między punktami. Panel ma z założenia to wyeliminować — każdy punkt
w raporcie **musi być wygenerowany z tego samego szablonu kodu**,
różniącego się wyłącznie danymi wejściowymi.

## 3. Model danych — `projekt.json`

To jest **jedyne źródło prawdy** — każdy krok UI czyta i dopisuje do
tego samego pliku. Umożliwia to wznowienie pracy w dowolnym momencie i
pełną odtwarzalność raportu bez ponownego przechodzenia całego wizarda.

```json
{
  "metadaneProjektu": {
    "nazwaProjektu": "string",
    "zamawiajacy": "string",
    "dataOd": "YYYY-MM-DD",
    "dataDo": "YYYY-MM-DD",
    "progAnalizyLacznej": 15,
    "linkWytyczneGDDKiA": "https://www.gov.pl/..."
  },
  "punkty": [
    {
      "id": "P1",
      "numer": 1,
      "typ": "skrzyzowanie | rondo | tranzyt | rejestracja",
      "nazwa": "Skrzyżowanie Łódzka / Włocławska",
      "miejscowosc": "Toruń",
      "lokalizacja": { "lat": 53.0138, "lng": 18.6039 },

      "kamery": [
        { "plikZrodlowy": "dane_K1.csv", "przesuniecieLiter": 0 }
      ],

      "metadanePomiaru": {
        "dataPomiaru": "2026-05-28",
        "dzienTygodnia": "czwartek",
        "warunkiAtmosferyczne": "bez opadów, +21°C",
        "statusPrzydatnosci": "akceptowalne | warunkowo_akceptowalne | do_powtorzenia",
        "zaklocenia": "string | null"
      },

      "wloty": [
        { "id": "WSCH", "opis": "ul. Łódzka (od wschodu)", "uwagi": "-" }
      ],
      "geometriaRegularna": true,

      "kierunekMapping": {
        "A": { "wlot": "WSCH", "manewr": "wprost" },
        "B": { "wlot": "WSCH", "manewr": "prawo" }
      },

      "qc": {
        "literyNiezmapowane": [],
        "duplikatyRelacji": [
          { "wlot": "ZACH", "manewr": "wprost", "litery": ["C", "F"], "status": "scalone" }
        ],
        "sumaKontrolna": { "ok": true, "roznica": 0 },
        "kategorieWyzerowaneGodzinowo": [],
        "status": "akceptacja | akceptacja_z_zastrzezeniem | do_korekty | eskalacja"
      },

      "obliczenia": {
        "sdr": 28558,
        "szczytDobowy": { "wartosc": 2285, "godzina": "15:00" },
        "szczytOknoPoranne": { "wartosc": 1949, "zakres": "07:00-08:00" },
        "szczytOknoPopoludniowe": { "wartosc": 4553, "zakres": "15:00-16:00" },

        "relacjeSDR": [
          { "wlot": "PN", "manewr": "Prawo", "opis": "Z północy na zachód, w prawo",
            "sdr": 45, "udzial": 0.2, "szczyt": 6, "godzinaSzczytu": "15:00" }
        ],
        "relacjeZNiezmot": [
          { "opis": "Z północy na zachód, w prawo", "suma": 45, "udzial": 0.2 }
        ],
        "relacjeZNiezmotDostepne": true,

        "relacjeCiezkie": [
          { "opis": "Z północy na zachód, w prawo", "suma": 0, "udzial": 0.0 }
        ],
        "relacjeCiezkieEstymowane": false,
        "ruchCiezkiSuma": 1933,

        "upc": [
          { "opis": "Ze wschodu na zachód, na wprost", "upc": 7.9 }
        ],

        "godzinowa": [
          { "godzina": "00:00", "zmotoryzowany": 126, "udzialZmot": 0.4,
            "niezmotoryzowany": 0, "udzialNiezmot": 0.0 }
        ],
        "niezmotGodzinowoEstymowane": false,

        "poryDoby": { "dzien": [26499, 92.8], "noc": [2059, 7.2] },

        "strukturaRodzajowa": [
          { "kategoria": "Osobowe", "suma": 24054, "udzialZmotoryzowane": 83.0, "udzialCale": 83.0 }
        ],
        "strukturaRodzajowaSumaCala": 28981
      },

      "assets": {
        "zdjecieKamery": "assets/kamera.jpg",
        "mapkaLokalizacji": "assets/mapka.png",
        "schematSkrzyzowania": "assets/schemat.png",
        "sankeySDR": "assets/sankey_sdr.png",
        "sankeyPoranny": "assets/sankey_poranny.png",
        "sankeyPopoludniowy": "assets/sankey_popoludniowy.png",
        "wykresPoryDoby": "assets/pory_doby.png",
        "wykresUPC": { "zrodlo": "placeholder_punkt1", "plik": "assets_p1/sankey_sdr.png" },
        "wykresGodzinowyWgRelacji": { "zrodlo": "placeholder_punkt1", "plik": "assets_p1/kombo_relacje.png" },
        "wykresGodzinowyCiezkichWgRelacji": { "zrodlo": "placeholder_punkt1", "plik": "assets_p1/kombo_ciezkie.png" },
        "wykresProfilDobowyKategorie": { "zrodlo": "placeholder_punkt1", "plik": "assets_p1/profil_dobowy.png" },
        "excelWynikowy": "wynik_tabele_Punkt1_P1.xlsx"
      },

      "teksty": {
        "lokalizacja": "string (z AI)",
        "organizacjaRuchu": "string (z AI)",
        "ruchWgKierunkow": "string (z AI)",
        "ruchPojazdowCiezkich": "string (z AI)",
        "poryDoby": "string (z AI)",
        "strukturaRodzajowa": "string (z AI)",
        "komentarzAnalityczny": "string (z AI)"
      },

      "przypisyJakosciDanych": [
        "string — przypis kursywą przy konkretnej tabeli, NIE osobna sekcja (patrz 5.6)"
      ]
    }
  ],

  "podsumowanie": {
    "trybRenderowania": "pelny | zagregowany",
    "tabelaZbiorcza": "...",
    "statystyki": { "medianaSdr": 0, "kwartyle": [0, 0, 0], "odstajace": ["P7"] },
    "histogramGodzinSzczytu": { "07:00": 42, "08:00": 12 },
    "mapaProjektu": "assets_projekt/mapa_projektu.png",
    "segmentacja": [{ "typ": "skrzyzowanie", "liczbaPunktow": 40, "sredniSdr": 12000 }],
    "excelZbiorczy": "wynik_tabele_zbiorcze.xlsx",
    "tekstWprowadzenie": "string (z AI)",
    "tekstPorownanie": "string (z AI)",
    "tekstWnioski": "string (z AI)"
  }
}
```

### 3.1 Kluczowe zmiany względem wersji 1 tego modelu

| Pole | v1 | v2 (aktualne) | Powód zmiany |
|---|---|---|---|
| Pory doby | 3: dzienna/wieczorna/nocna | **2: dzień (06–22) / noc (22–06)** | Ujednolicenie prezentacji, patrz reguły obliczeń §4 |
| Szczyty | 3: poranny/popołudniowy/wieczorny, okna 06–10/11–17/18–22 | **2 stałe okna: 7:00–8:00 i 15:00–16:00**, wspólne dla wszystkich punktów projektu | Porównywalność diagramów Sankey między punktami |
| `relacjeCiezkie` | brak pola w ogóle | nowe, **ta sama liczba wierszy i ta sama kolejność co `relacjeSDR`** | Nowa sekcja 3.n.4 w raporcie, wymaga struktury lustrzanej do 3.n.3 |
| `upc` | brak | nowe (Udział Pojazdów Ciężkich per relacja) | Nowy rysunek w sekcji 3.n.2 |
| `godzinowa` | brak niezmotoryzowanych | **dwie pary kolumn** (zmot. + niezmot.) | Rozszerzona tabela 3.n.5 |
| `strukturaRodzajowa` | jedna kolumna % | **dwie kolumny %** (`udzialZmotoryzowane`, `udzialCale`) | Rozróżnienie mianownika (SDR vs suma całkowita) |
| `teksty.uwagiJakosciDanych` | osobne pole, renderowane jako sekcja „Uwagi o jakości danych” | **usunięte jako sekcja** — zastąpione `przypisyJakosciDanych[]`, renderowanymi jako przypisy kursywą przy konkretnej tabeli | Ujednolicenie struktury — każdy punkt ma identyczny zestaw podrozdziałów, bez wyjątków |
| `assets.*` | zawsze point-specific | część pól ma `zrodlo: "placeholder_punkt1"` | Do czasu powstania dedykowanych generatorów wykresów analitycznych (patrz 5.7) |

## 4. Flow UI — krok po kroku

| Krok | Ekran | Wejście | Wyjście do `projekt.json` |
|---|---|---|---|
| 1 | Liczba punktów + metadane projektu | liczba, nazwa projektu, zamawiający, link do wytycznych GDDKiA | `metadaneProjektu`, szkielet `punkty[]` |
| 2 | Dane podstawowe punktu | nazwa, typ, lokalizacja, współrzędne, liczba kamer | `punkty[i].id/typ/nazwa/lokalizacja` |
| 3 | Upload danych źródłowych (po 1 per kamera) | pliki eksportu AISP | `punkty[i].kamery[]`, auto `przesuniecieLiter` |
| 4 | Metadane pomiaru | warunki atmosferyczne, status przydatności, zakłócenia | `punkty[i].metadanePomiaru` |
| 5 | Mapowanie kierunków | UI: lista liter wykrytych w danych × wybór wlotu + manewru; flaga `geometriaRegularna` (4 wloty, kąty ~90°) czy nie (np. skrzyżowanie typu T) | `punkty[i].wloty`, `kierunekMapping`, `geometriaRegularna` |
| 5b | Walidacja mapowania *(automatyczna, blokująca)* | — | `qc.literyNiezmapowane`, `qc.duplikatyRelacji` (z propozycją scalenia) |
| 6 | Zdjęcie z kamery + schemat skrzyżowania | upload `.jpg/.png` (zdjęcie), upload lub auto-generacja (schemat z etykietami wlotów) | `assets.zdjecieKamery`, `assets.schematSkrzyzowania` |
| 7 | Obliczenia + wykresy + mapka | — (automatyczne) | `obliczenia`, część `assets.*` (patrz 5.7 co jest placeholderem) |
| 7b | Kontrola jakości — bramka *(blokująca)* | przegląd `qc.sumaKontrolna`, `qc.kategorieWyzerowaneGodzinowo` | `qc.status` (wymaga potwierdzenia jeśli nie „akceptacja”) |
| 8 | Generowanie tekstów (AI) | prompt zbudowany z `obliczenia` + `qc` | `teksty.*`, `przypisyJakosciDanych[]` |
| 9 | Podgląd i edycja punktu | — | ewentualne ręczne poprawki `teksty.*` |
| — | *(pętla 2–9 dla każdego kolejnego punktu)* | | |
| 10 | Podsumowanie (dawniej: analiza łączna) | automatyczny wybór trybu wg liczby punktów | `podsumowanie` |
| 11 | Budowa raportu Word | pełny `projekt.json` | `raport_final.docx` |

## 5. Pipeline przetwarzania — szczegóły krytycznych kroków

### 5.1 Dane źródłowe → agregat godzinowy (krok 3, backend)

1. Wczytaj dane każdej kamery osobno.
2. Filtruj po statusie zwalidowanych detekcji (inaczej sumy nie zgodzą
   się z natywnym raportem źródłowym).
3. Dla kamery *k* > 1: przesuń litery kierunków, żeby się nie
   kolidowały z kamerą 1 (wartość przesunięcia zapisz w
   `kamery[].przesuniecieLiter`, żeby było audytowalne).
4. Scal wszystkie kamery w jeden zestaw danych **przed** agregacją
   godzinową.
5. Agreguj do postaci: wiersz = (Wlot/litera, Godzina), kolumny = 12
   kategorii pojazdów (8 zmotoryzowanych + 4 niezmotoryzowane).
6. Nie zakładaj stałej liczby wierszy/kierunków — obserwowane warianty
   to od ~6 do ~16 relacji na punkt, typowo ok. 12. Generator MUSI
   działać poprawnie niezależnie od tej liczby (tabele relacji zawsze
   mają tyle wierszy, ile faktycznie jest relacji — nigdy sztywnego
   limitu).
7. Osobno zachowaj/policz sumy dobowe **niezależnie od agregatu
   godzinowego** (np. z natywnego podsumowania źródła, jeśli dostępne)
   — to jest **autorytatywne źródło** dla SDR i sum kategorii pokazywanych
   w tabeli parametrów i strukturze rodzajowej (patrz 5.3 i przypadki
   brzegowe w regułach obliczeń — suma z agregatu godzinowego może się
   nieznacznie różnić, rzędu 1–2%, od sumy dobowej „urzędowej").

### 5.2 Mapowanie kierunków + walidacja (krok 5/5b)

```
litery_w_danych = unique(dane["Kierunek"])
litery_niezmapowane = litery_w_danych - keys(kierunekMapping)
if litery_niezmapowane:
    zablokuj_przejscie_dalej()
    pokaz_uzytkownikowi(litery_niezmapowane)

# wykrywanie duplikatów relacji
grupy = group_by(kierunekMapping, key=(wlot, manewr))
for (wlot, manewr), litery in grupy:
    if len(litery) > 1:
        qc.duplikatyRelacji.append({
            wlot, manewr, litery,
            sugerowanaAkcja: "scal w jedną relację (suma po kluczu wlot+manewr)"
        })
```

Scalanie duplikatów jest **automatyczne i niejawne** w kroku agregacji —
nie generuje osobnej wzmianki w treści raportu (nie ma już sekcji
„Uwagi o jakości danych”; jeśli coś jest warte wzmianki, trafia jako
krótki przypis, patrz 5.6).

**Flaga `geometriaRegularna`**: ustawiana ręcznie lub automatycznie
(4 wloty ORAZ kąty między nimi w tolerancji ~90° ± margines). Steruje
algorytmem generowania opisu relacji (patrz 5.4) — dla geometrii
nieregularnej (np. skrzyżowanie typu T) generator NIE zgaduje kierunku
docelowego relacji, tylko używa formy skróconej.

### 5.3 Silnik obliczeniowy (krok 7)

Zaimplementować jako osobne, nazwane funkcje — jedna funkcja = jedna
tabela/wartość w `obliczenia`:

| Funkcja | Zwraca | Kluczowa reguła |
|---|---|---|
| `oblicz_sdr_i_szczyt_dobowy()` | `sdr`, `szczytDobowy` | SDR = suma 8 kategorii zmotoryzowanych. Szczyt = maksimum sumy **wszystkich relacji łącznie w danej godzinie**, nie suma szczytów per relacja (mogą wypadać w różnych godzinach) |
| `oblicz_relacje_sdr()` | `relacjeSDR` (lista, sortowana wg §5.5) | suma zmotoryzowanych per (wlot, manewr) + godzina/wartość szczytu tej relacji |
| `oblicz_relacje_z_niezmot()` | `relacjeZNiezmot`, `relacjeZNiezmotDostepne` | jak wyżej + niezmotoryzowani per relacja. Jeśli suma niezmotoryzowanych w agregacie godzinowym = 0 mimo niezerowej sumy dobowej → `relacjeZNiezmotDostepne = false`, pole `relacjeZNiezmot` puste (renderer w Wordzie pokazuje zdanie zamiast tabeli, patrz struktura §3.n.3) |
| `oblicz_relacje_ciezkie()` | `relacjeCiezkie`, `relacjeCiezkieEstymowane` | suma kategorii ciężkich per (wlot, manewr). **Zawsze te same wiersze i kolejność co `relacjeSDR`** (relacje o zerowym ruchu ciężkim → `0`, nie pomijać). Jeśli agregat godzinowy dla kategorii ciężkich = 0 mimo niezerowej sumy dobowej → `relacjeCiezkieEstymowane = true`, wartości szacowane proporcjonalnie do udziału każdej relacji w SDR (patrz reguły obliczeń §8.1) |
| `oblicz_upc()` | `upc` | per relacja: ruch_ciężki(relacja) / SDR(relacja) × 100% |
| `oblicz_godzinowa()` | `godzinowa`, `niezmotGodzinowoEstymowane` | 24 wiersze, suma wszystkich relacji, dwie pary kolumn (zmot./niezmot.). Estymacja niezmotoryzowanych analogicznie do `relacjeCiezkie` — rozkład wg profilu godzinowego ruchu zmotoryzowanego |
| `oblicz_pory_doby()` | `poryDoby` | 2 okna: dzień 06:00–21:59, noc 22:00–05:59 (na bazie zmotoryzowanych) |
| `oblicz_szczyty_okna_stale()` | `szczytOknoPoranne`, `szczytOknoPopoludniowe` | suma w oknach 7:00–8:00 i 15:00–16:00 — **stałe dla wszystkich punktów projektu**, nie lokalne maksima |
| `oblicz_strukture_rodzajowa()` | `strukturaRodzajowa`, `strukturaRodzajowaSumaCala` | 12 kategorii **rozdzielone** (autobusy i mikrobusy osobno). Dwie kolumny %: `udzialZmotoryzowane` = wartość/SDR (tylko 8 kat. mech., "-" dla 4 niezmot.), `udzialCale` = wartość/suma_12_kategorii (wszystkie wiersze) |

**Twarda bramka jakości** (krok 7b, nie tylko log): `suma(kategorie
mechaniczne z agregatu godzinowego) ≈ SDR_z_zrodla_urzedowego`
(tolerancja np. 2%) → jeśli przekroczona, `qc.sumaKontrolna.ok = false`
i UI wymaga świadomego potwierdzenia przed przejściem dalej. Osobno:
`qc.kategorieWyzerowaneGodzinowo` wypełniane automatycznie, gdy dowolna
grupa kategorii (niezmotoryzowane lub ciężkie) sumuje się do zera w
agregacie godzinowym mimo niezerowej sumy dobowej — to steruje flagami
`relacjeZNiezmotDostepne` / `relacjeCiezkieEstymowane` opisanymi wyżej,
NIE generuje osobnej sekcji w raporcie.

### 5.4 Generowanie opisu relacji

```
bearing = {PN: 0, WSCH: 90, PD: 180, ZACH: 270}
heading(wlot) = (bearing[wlot] + 180) mod 360

exit_bearing(wlot, manewr):
  Wprost -> heading(wlot)
  Prawo  -> heading(wlot) + 90
  Lewo   -> heading(wlot) - 90
  Zawracajacy -> bearing(wlot)

if geometriaRegularna:
    opis = "{Z/Ze} {wlot_dopelniacz} na {exit_biernik}, {manewr_tekst}"
else:
    opis = "{Z/Ze} {wlot_dopelniacz}, {manewr_tekst}"   # bez zgadywania celu
```

Prefiks „Ze” zamiast „Z” wyłącznie dla wlotu `WSCH`. Pełna tabela
form gramatycznych (dopełniacz/biernik dla PN/WSCH/PD/ZACH) — stały
słownik w kodzie, nie do konfiguracji per projekt.

### 5.5 Sortowanie relacji (obowiązuje we wszystkich tabelach relacji)

```
WLOT_ORDER = {PN: 0, WSCH: 1, PD: 2, ZACH: 3}
MANEWR_ORDER = {Prawo: 0, Wprost: 1, Lewo: 2, Zawracajacy: 3}
klucz_sortowania = (WLOT_ORDER[wlot], MANEWR_ORDER[manewr])
```

`relacjeSDR`, `relacjeZNiezmot`, `relacjeCiezkie` muszą być posortowane
tym samym kluczem i mieć te same wiersze w tej samej kolejności
(pierwsze dwie różnią się liczbą wierszy tylko jeśli
`relacjeZNiezmotDostepne = false`; `relacjeCiezkie` ma zawsze identyczną
liczbę wierszy co `relacjeSDR`).

### 5.6 Przypisy jakości danych (zamiast osobnej sekcji)

Zamiast generowania sekcji „Uwagi o jakości danych” (usunięte ze
standardu — patrz `raport-specyfikacja-struktura.md` §0), panel
generuje **krótkie przypisy kursywą**, doczepiane do konkretnej
tabeli/wykresu, w tym samym stylu co istniejące przypisy typu „Suma
kategorii jest wyższa niż SDR...”. Każdy przypis to jeden element
`przypisyJakosciDanych[]`, z polem wskazującym, pod którą tabelą ma się
pojawić (`kotwica: "T4" | "T5" | "T6"`):

```json
{
  "kotwica": "T5",
  "tresc": "Arkusz godzinowy dla tego punktu nie rejestruje kategorii ciężarowe/ciężarowe z naczepami w rozbiciu na relacje (dostępna jest wyłącznie suma dobowa). Powyższy rozkład kierunkowy jest oszacowany proporcjonalnie do ogólnego udziału każdej relacji w SDR punktu."
}
```

Generowane automatycznie przez backend (na bazie flag
`relacjeCiezkieEstymowane` / `niezmotGodzinowoEstymowane`), NIE przez
AI — treść jest deterministyczna funkcją stanu QC, więc nie ma potrzeby
(ani ryzyka niespójności) zlecania jej modelowi językowemu.

### 5.7 Obrazy — reguła placeholderów wielokrotnego użytku

**Kluczowa zasada projektowa**: dopóki nie istnieje dedykowany,
poprawny generator dla danego typu rysunku, panel **nie próbuje** go
prowizorycznie zastępować własnym uproszczonym wykresem dla każdego
punktu z osobna — zamiast tego świadomie **reużywa dokładnie ten sam
plik graficzny z Punktu 1** we wszystkich punktach projektu. To
zapewnia spójny, jednoznacznie rozpoznawalny stan „do podmiany” (łatwo
znaleźć wszystkie miejsca wymagające uzupełnienia — wystarczy poszukać,
gdzie `assets.*.zrodlo == "placeholder_punkt1"`) zamiast rozproszonych,
różniących się między sobą prowizorek.

| Rysunek | Status | Reguła |
|---|---|---|
| Mapka lokalizacji | ✅ generator gotowy | point-specific (statyczna mapa OSM/Mapbox wokół współrzędnych punktu) |
| Schemat skrzyżowania | ✅ generator gotowy | point-specific (etykiety wlotów na bazie `wloty[]`) |
| Zdjęcie z kamery | — (upload) | point-specific, wgrywane ręcznie |
| Diagram SDR / poranny / popołudniowy | ⚠️ docelowo Visum (3.4), obecnie placeholder generowany z danych | point-specific już teraz (mamy generator wystarczająco dobry do roboczego użytku) |
| Wykres UPC | ❌ brak dedykowanego generatora | **placeholder = plik `sankeySDR` tego samego punktu** (nie z Punktu 1 — bo SDR jest już point-specific, patrz wyżej) |
| Wykres godzinowy wg relacji (3.n.3) | ❌ brak dedykowanego generatora | **placeholder = plik z Punktu 1** (`zrodlo: placeholder_punkt1`) |
| Wykres godzinowy ciężkich wg relacji (3.n.4) | ❌ brak dedykowanego generatora | **placeholder = plik z Punktu 1** (inny plik niż wyżej, ale też z Punktu 1) |
| Profil dobowy wg kategorii (3.n.5) | ❌ brak dedykowanego generatora | **placeholder = plik z Punktu 1** |
| Udział dnia/nocy (3.n.6) | ✅ generator gotowy | point-specific |

Gdy tylko powstanie dedykowany generator dla któregoś z placeholderów —
zmienia się WYŁĄCZNIE to, skąd bierze się plik (`zrodlo` z powrotem
`"generowany"` zamiast `"placeholder_punkt1"`); struktura dokumentu,
liczba rysunków, ich pozycja i podpisy **się nie zmieniają**.

### 5.8 Prompt do AI (krok 8)

Prompt musi dostawać **nie tylko liczby**, ale też wynik QC — inaczej
model może zmyślić zastrzeżenia, których nie było, albo pominąć realne
(choć realne zastrzeżenia i tak trafiają do `przypisyJakosciDanych[]`
deterministycznie, nie przez AI — patrz 5.6). Struktura promptu:

```
Dane wejściowe do promptu (na punkt pomiarowy):
- obliczenia — pełne liczby (SDR, relacjeSDR, relacjeZNiezmot,
  relacjeCiezkie, upc, godzinowa, poryDoby, strukturaRodzajowa)
- qc — status, ewentualne anomalie (dla kontekstu, nie do wypisania wprost)
- metadanePomiaru (warunki, status przydatności)
- kontekst: typ punktu, liczba wlotów, nazwa, geometriaRegularna

Wymagany format odpowiedzi: JSON ze stałymi kluczami:
  lokalizacja, organizacjaRuchu, ruchWgKierunkow,
  ruchPojazdowCiezkich, poryDoby, strukturaRodzajowa,
  komentarzAnalityczny

Zasada dla ruchPojazdowCiezkich: tekst analogiczny w stylu do
ruchWgKierunkow (dominujące relacje, koncentracja, UPC), ale
WYŁĄCZNIE na bazie danych z `relacjeCiezkie` i `upc` — nigdy nie
kopiować/parafrazować tekstu o ruchu całkowitym.

Zasada ogólna: teksty NIE są uzupełnianiem szablonu o stałej treści —
każdy punkt ma inną dominującą relację, inną skalę ruchu, inny
charakter (tranzytowy/lokalny) — tekst ma to odzwierciedlać, nie być
przeredagowanym kopiuj-wklej.
```

Przy 80–150 punktach to 80–150 wywołań modelu (× 6 pól tekstowych) —
technicznie trywialne do zrównoleglenia (batch), ale krok 9
(podgląd/edycja) jest obowiązkowy, bo tekst analityczny to jedyne
miejsce w pipeline, gdzie błąd nie jest wykrywalny automatycznie.

## 6. Rozdział „Podsumowanie” — tryb dualny

*(dawniej „Analiza łączna” + „Wnioski i podsumowanie” jako dwa osobne
rozdziały — teraz scalone w jeden rozdział „Podsumowanie”, patrz
`raport-specyfikacja-struktura.md` §6)*

```
N = liczba punktów w projekcie
PROG = metadaneProjektu.progAnalizyLacznej  # domyślnie 15

if N <= PROG:
    tryb = "pelny"
    # pełna tabela zbiorcza, słupkowy wykres SDR z etykietami per punkt,
    # tabela porównawcza struktury rodzajowej, wykres szczytów w stałych
    # oknach (7-8 i 15-16) per punkt, tekst punkt-po-punkcie
else:
    tryb = "zagregowany"
    # 1. Tabela w Wordzie: Top 10 najwyższe SDR + Top 10 najniższe
    # 2. Pełna tabela wszystkich N punktów -> wynik_tabele_zbiorcze.xlsx
    # 3. Statystyki: mediana, kwartyle, odstające (|z-score| > 2)
    #    -> tylko odstające punkty wymieniane z ID w tekście
    # 4. Histogram rozkładu SDR (zamiast wykresu słupkowego per punkt)
    # 5. Histogram godzin szczytu w skali projektu (stałe okna 7-8/15-16)
    # 6. Mapa projektu: kropka per punkt, kolor/rozmiar = SDR
    #    -> główny element wizualny przy dużym N
    # 7. Segmentacja wg pola "typ" (skrzyzowanie/rondo/tranzyt/rejestracja)
    #    -> osobne mini-podsumowanie per segment zamiast per punkt
```

Próg `15` to parametr w `metadaneProjektu` — do skalibrowania
empirycznie po pierwszych kilku dużych projektach, nie sztywna wartość
w kodzie.

## 7. Budowa dokumentu Word (krok 11)

Generator Node.js/`docx` buduje dokument w jednym przebiegu z pełnego
`projekt.json`, w stałej kolejności:

| Kolejność | Sekcja | Ile razy |
|---|---|---|
| 1 | Strona tytułowa | 1× |
| 2 | Spis treści (pole TOC) | 1× |
| 3 | Cel i zakres opracowania | 1× |
| 4 | Metodologia | 1× |
| 5 | Rozdział „Wyniki pomiarów” — nagłówek + akapit wprowadzający | 1× |
| 5.n | Pełna sekcja punktu (8 podrozdziałów, patrz `raport-specyfikacja-struktura.md` §5) | 1× na punkt |
| 6 | Podsumowanie (tryb pelny/zagregowany wg §6) | 1× |
| 7 | Literatura i spis załączników | 1× |

**Numeracja rozdziałów**: wyłącznie przez automatyczną, wielopoziomową
listę Worda podpiętą pod style `Heading 1/2/3` — nigdy wpisywana jako
tekst. **Numeracja rysunków/tabel wewnątrz punktu**: dwa niezależne
liczniki (osobno dla `Rysunek`, osobno dla `Tabela`), każdy startuje od
1 przy początku sekcji punktu, inkrementowany programowo w kodzie
budującym dokument (nie ręcznie wyliczany w `projekt.json`) — dzięki
temu pominięcie warunkowego elementu (np. brak `relacjeZNiezmot`) samo
przesuwa kolejne numery bez ręcznej interwencji.

Pełna specyfikacja treści każdego podrozdziału (kolumny tabel, opisy,
podpisy) — patrz `raport-specyfikacja-struktura.md`.

## 8. Zasady jakości — mapowanie na checklistę (Story 5)

| Bramka w panelu | Odpowiada punktowi checklisty |
|---|---|
| Blokada przy niezmapowanych literach (5b) | Faza 2, sekcja 4.2 |
| Wykrywanie duplikatów relacji (5b) | Faza 2, sekcja 4.3 |
| Suma kontrolna jako twarda bramka (7b) | Faza 2, sekcja 4.3 |
| Wykrywanie wyzerowanych kategorii godzinowych (7b) | rozszerzenie — nowy typ anomalii spotkany w praktyce (patrz reguły obliczeń §8.1); wymaga zbadania też na poziomie samego pipeline'u danych źródłowych, nie tylko obejścia w raporcie |
| Wymagane pola: warunki atm., status przydatności (krok 4) | Faza 1, sekcja 3.2 |
| Automatyczna numeracja Word + podpisy (budowa docx) | Faza 3, standard 4.4 |
| Próg trybu Podsumowania | rozszerzenie checklisty o kryterium skali |

## 9. Stos technologiczny (propozycja)

- **Backend obliczeniowy:** Python (pandas — agregacje, matplotlib —
  wykresy i placeholdery Sankey, czcionka **Carlito** wymuszona we
  wszystkich generowanych PNG, żeby nie odstawały wizualnie od reszty
  dokumentu w Calibri).
- **Budowa docx:** Node.js + biblioteka `docx` (sprawdzone na Toruniu —
  numeracja wielopoziomowa, style, obrazy, tabele, branding Orange:
  nagłówki tabel `#FF7900`, nagłówek/stopka strony).
- **UI:** dowolny framework webowy (wizard krokowy) — kluczowe, żeby
  każdy krok zapisywał się do `projekt.json` natychmiast (możliwość
  przerwania i wznowienia pracy nad projektem z 80–150 punktami, który
  realnie nie powstanie w jednej sesji).
- **AI:** wywołania modelu przez API, wymuszony schemat JSON w
  odpowiedzi (structured output), z krokiem podglądu/edycji przed
  zamrożeniem tekstu (krok 9) — jedyne miejsce w pipeline bez
  automatycznej weryfikacji poprawności.

## 10. Otwarte decyzje do podjęcia przed implementacją

| Decyzja | Rekomendacja | Status |
|---|---|---|
| Próg trybu Podsumowania | 15 punktów, jako parametr konfigurowalny | do potwierdzenia po pilotażu |
| Format mapy (statyczna mapa OSM vs. własny rysowany obrys) | statyczna mapa OSM/Mapbox | do potwierdzenia |
| Zachowanie przy braku zgodności sumy kontrolnej | wymagane świadome potwierdzenie, nie blokada permanentna | do potwierdzenia |
| Docelowy provider Sankeya/UPC/kombo-wykresów (placeholder vs. integracja) | placeholder z Punktu 1 do czasu integracji, jawnie oznaczony w `assets.*.zrodlo` | zgodne z §5.7 |
| Przyczyna wyzerowanych kategorii w agregacie godzinowym | zbadać w pipeline źródłowym (History → agregat) — obserwowane dla różnych kategorii w różnych punktach, sugeruje błąd systemowy, nie odosobniony przypadek | do zbadania, poza zakresem samego panelu |
| Tolerancja rozbieżności sumy kontrolnej (agregat godzinowy vs. suma urzędowa) | roboczo 2% | do potwierdzenia |

## 11. Powiązane dokumenty

- `raport-specyfikacja-struktura.md` — dokładny układ dokumentu: co, w
  jakiej kolejności, jakie kolumny/podpisy (źródło prawdy dla wyglądu
  raportu).
- `raport-reguly-obliczen-i-danych.md` — źródła danych, wzory,
  przypadki brzegowe (źródło prawdy dla obliczeń — ten dokument je tylko
  cytuje/mapuje na architekturę).
