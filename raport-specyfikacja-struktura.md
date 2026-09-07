# Specyfikacja generatora raportu z pomiaru ruchu drogowego

> Dokument opisuje DOCELOWĄ, kompletną strukturę raportu Word generowanego
> automatycznie z danych pomiarowych AISP. Wzorcem referencyjnym jest
> Punkt 1 (sekcja 3.1) — każdy kolejny punkt pomiarowy musi mieć
> **identyczną** strukturę, różniącą się wyłącznie danymi i liczbą
> wierszy w tabelach relacji (zależną od geometrii skrzyżowania).
>
> Towarzyszący plik `raport-reguly-obliczen-i-danych.md` opisuje wzory,
> źródła danych i przypadki brzegowe. Ten plik opisuje WYŁĄCZNIE
> strukturę dokumentu: co, w jakiej kolejności, z jakimi kolumnami/
> podpisami.

---

## 0. Zasady ogólne

- **Numeracja rozdziałów**: automatyczna, wielopoziomowa lista Worda
  (nie ręcznie wpisywane cyfry). Struktura najwyższego poziomu:
  1. Cel i zakres opracowania
  2. Metodologia
  3. Wyniki pomiarów w punktach pomiarowych (kontener — każdy punkt to
     podrozdział 3.1 / 3.2 / 3.3 / ...)
  4. Podsumowanie
  5. Literatura i spis załączników

- **Numeracja rysunków i tabel wewnątrz punktu**: dwa **niezależne**
  liczniki, każdy zaczyna się od 1 przy starcie punktu (`Rysunek 3.n.1,
  3.n.2, ...` i `Tabela 3.n.1, 3.n.2, ...` osobno). Numer nigdy się nie
  powtarza w obrębie jednego licznika, nigdy nie ma dziur — jeśli jakiś
  element jest pomijany dla danego punktu (patrz przypadki brzegowe),
  kolejne numery przesuwają się w dół automatycznie (liczniki, nie
  twarde stringi).

- **Zapowiedzi**: każdy rysunek i każda tabela ma zdanie zapowiadające
  bezpośrednio przed nim, np. "Rysunek 3.1.4 przedstawia diagram
  przepływów ruchu dla SDR (całodobowo)." oraz podpis (caption) pod
  spodem w kursywie, np. "Rysunek 3.1.4. Diagram natężeń ruchu
  drogowego [poj./dobę] - SDR - Łódzka / Włocławska."

- **Wyrównanie w tabelach**: nagłówki i tekst do lewej, liczby do
  prawej. Nagłówek tabeli: wypełnienie pomarańczowe (`#FF7900`), tekst
  biały, bold.

- **Czcionka**: Calibri (lub Carlito jako zamiennik metrycznie
  identyczny — używać go we WSZYSTKICH generowanych wykresach
  matplotlib/PNG, żeby nie odstawały wizualnie od reszty dokumentu,
  która jest w Calibri).

- **Branding**: nagłówek strony — małe logo + "Raport z pomiaru ruchu
  drogowego — Toruń" (lub nazwa miasta z danych), z pomarańczową linią
  pod spodem. Stopka — "Orange Restricted" (szary, lewo), "Orange
  Restricted" (pomarańczowy bold, środek), "Strona X z Y" (prawo).
  Nagłówek/stopka nie występują na stronie tytułowej.

- **Budżet stron**: każdy punkt pomiarowy (cała sekcja 3.n) musi zająć
  **dokładnie 10 stron** przy typowej geometrii skrzyżowania (~12
  relacji ruchu). Jeśli skrzyżowanie ma znacząco więcej relacji (np.
  >16), dopuszczalne jest przekroczenie tego budżetu — ale generator
  MUSI działać poprawnie (bez błędów, bez obcinania danych) niezależnie
  od liczby relacji; tabele relacji muszą zawsze mieć tyle wierszy, ile
  faktycznie istnieje relacji w danym punkcie (nigdy nie przycinać do
  góry ograniczenia liczby wierszy).

- **Obrazy — stan przejściowy**: dopóki nie istnieje docelowy generator
  diagramów Sankey/wykresów analitycznych, część rysunków w każdym
  punkcie to **placeholdery wielokrotnego użytku** (patrz sekcja 3.n.2,
  3.n.3, 3.n.4, 3.n.5 niżej) — dla punktów 2, 3, ... używa się
  DOKŁADNIE TEGO SAMEGO pliku graficznego co w Punkcie 1, dopóki nie
  pojawi się właściwa, wygenerowana z danych grafika dla danego punktu.
  Kiedy docelowy generator wykresów/diagramów będzie gotowy, te
  placeholdery zostaną podmienione na realne, point-specific obrazy —
  ale struktura dokumentu (liczba rysunków, ich pozycja, podpisy) się
  nie zmieni.

---

## 1. Strona tytułowa

Bez numeracji rozdziału. Elementy: logo (górny lewy róg + duże na
środku), pomarańczowa pozioma linia, tytuł "RAPORT Z POMIARU RUCHU
DROGOWEGO" (bold, czarny), podtytuł z nazwą miasta i skrzyżowań (bold,
pomarańczowy), tabela metadanych bez obramowania (Punkty pomiarowe /
Zakres dat pomiaru / Zamawiający / Wykonawca / Data sporządzenia
raportu).

## 2. Spis treści

Pole TOC Worda (`hyperlink: true`, `headingStyleRange: '1-3'`) —
generowane automatycznie z nagłówków. Wymaga ręcznego odświeżenia w
Wordzie po otwarciu pliku (F9 / prawy klik → Aktualizuj pole).

## 3. Rozdział 1 — Cel i zakres opracowania

- Akapit: cel opracowania, odniesienie do wskazanych punktów.
- Lista punktrowana: punkty pomiarowe objęte opracowaniem (P1, P2, P3,
  ... — nazwa + miasto).
- Akapit: zakres czasowy pomiaru (daty, typ pomiaru).
- Akapit: ograniczenie zakresu (np. różne dni tygodnia pomiaru między
  punktami — jeśli dotyczy).

## 4. Rozdział 2 — Metodologia

Stałe akapity opisujące (nie zmieniają się między projektami, tylko
między różnymi konwencjami raportowania — patrz plik reguł):
1. Metoda pomiaru (rejestracja wideo + klasyfikacja automatyczna +
   weryfikacja manualna).
2. Kategoryzacja pojazdów — 12 kategorii, definicja SDR (suma kategorii
   mechanicznych, bez pieszych/rowerów/hulajnóg).
3. Interwały czasowe — godzinowe (00–23) + dwie pory doby (dzień
   06:00–22:00, noc 22:00–06:00) + dwa stałe okna szczytowe wspólne dla
   wszystkich punktów (poranny 7:00–8:00, popołudniowy 15:00–16:00).
4. Numeracja wlotów i nazewnictwo relacji — wloty oznaczone skrótem
   kierunku geograficznego (WSCH/ZACH/PN/PD), manewry: wprost/prawo/
   lewo/zawracający. Kolejność sortowania w tabelach: wlot wg zegara
   PN→WSCH→PD→ZACH, w obrębie wlotu wg manewru prawo→wprost→lewo→
   zawracający.
5. Ograniczenie porównywalności danych — mapowanie AISP jest ręczne per
   punkt, mogą wystąpić techniczne artefakty (duplikaty etykiet itp.),
   scalane automatycznie w kroku agregacji.

## 5. Rozdział 3 — Wyniki pomiarów w punktach pomiarowych

Akapit wprowadzający (1x, dla całego rozdziału, przed pierwszym
podpunktem): opis układu podrozdziałów wspólnego dla każdego punktu.

### 5.N Struktura pojedynczego punktu pomiarowego (3.n, gdzie n = 1, 2, 3...)

Każdy punkt = **dokładnie 8 podrozdziałów**, w tej kolejności. Rysunki
(`R`) i tabele (`T`) numerowane niezależnymi licznikami od 1.

---

#### 3.n.1 Lokalizacja i karta skrzyżowania

Nagłówek punktu (`## Punkt n - {nazwa skrzyżowania}`) + akapit
lokalizacyjny (lokalizacja, liczba i oznaczenie wlotów, charakter
skrzyżowania) — **przed** pierwszym podrozdziałem 3.n.1.

1. **T1 — Parametry pomiaru.** Kolumny: `Parametr | Wartość`. Wiersze:
   ID punktu, Nazwa, Data pomiaru, Dzień tygodnia, Czas rozpoczęcia,
   Czas zakończenia, Czas trwania, SDR, Szczyt dobowy, Warunki
   atmosferyczne, Metoda pomiaru (11 wierszy + nagłówek).
   Wewnątrz/zaraz po tej tabeli osadzona jest:
   - **R1 — Mapka lokalizacji** (point-specific; miasto z zaznaczonym
     punktem pomiaru).
2. **R2 — Schemat skrzyżowania** z oznaczeniem wlotów (etykiety w
   formacie "{ulica} – Wlot {kierunek słownie}"). Point-specific.
3. **R3 — Widok z kamery** rejestrującej ruch w punkcie pomiarowym.
   Point-specific.
4. **T2 — Tabela wlotów.** Kolumny: `Nr wlotu | Opis wlotu | Kierunek |
   Uwagi`. Liczba wierszy = liczba wlotów skrzyżowania (zwykle 3 lub 4;
   dla skrzyżowań typu T w kolumnie Uwagi info o brakującym wlocie).

#### 3.n.2 Diagramy przepływów ruchu

*(bez dopisku "(Sankey)" w tytule)*

Akapit wprowadzający: opis dominujących relacji + odniesienie do
stałych okien szczytowych.

1. **T3 — Zestawienie relacji ruchu zmotoryzowanego (SDR) i szczytów
   godzinowych.** Kolumny: `Opis relacji | SDR [poj./dobę] | Udział w
   SDR | Szczyt [poj./h] | Godz. szczytu`. **Bez** osobnych kolumn
   Wlot/Manewr (są zakodowane w kolumnie "Opis relacji"). Liczba
   wierszy = liczba relacji o niezerowym ruchu (zwykle 12, może być
   więcej lub mniej). Sortowanie: patrz zasady ogólne.
2. **R4 — Diagram natężeń ruchu drogowego — SDR (całodobowo).**
   Point-specific (docelowo Visum, obecnie placeholder point-specific,
   bo mamy realny materiał).
3. **R5 — Udział pojazdów ciężkich w ruchu dobowym wg relacji (UPC).**
   ⚠️ Placeholder wielokrotnego użytku: dopóki nie ma dedykowanego
   diagramu UPC, używa się TEGO SAMEGO obrazu co R4 (SDR) — zarówno
   wewnątrz punktu 1, jak i we wszystkich kolejnych punktach.
4. **R6 — Diagram przepływów, szczyt poranny (7:00–8:00).**
   Point-specific.
5. **R7 — Diagram przepływów, szczyt popołudniowy (15:00–16:00).**
   Point-specific.

#### 3.n.3 Ruch według kierunków i relacji

Akapit analityczny (bespoke tekst per punkt — opis dominujących
relacji, koncentracji ruchu, godzin szczytu; NIE jest to
fill-in-the-blank szablon, tekst pisany od nowa dla każdego punktu na
bazie jego własnych danych).

1. **T4 — Zestawienie relacji ruchu łącznie z ruchem nie zmotoryzowanym.**
   Kolumny: `Opis relacji | Suma [poj./dobę] | Udział`. Ta sama
   struktura/kolejność wierszy co T3, tylko z doliczonym ruchem
   nie zmotoryzowanym (rowery, hulajnogi, piesi) do każdej relacji.
   🟡 **Warunkowa**: jeśli dane źródłowe nie pozwalają rozdzielić
   niezmotoryzowanych na relacje (patrz przypadek brzegowy w pliku
   reguł), tabela jest pomijana i zastępowana jednym zdaniem
   wyjaśniającym — bez zmiany numeracji pozostałych elementów (licznik
   tabel po prostu przeskakuje).
2. **R8 — Wykres: rozkład godzinowy ruchu według relacji** (wszystkie
   kategorie). ⚠️ Placeholder wielokrotnego użytku (patrz 3.n.2/R5) —
   dla punktów 2, 3... używa się obrazu z Punktu 1, dopóki nie powstanie
   docelowy generator (docelowo: wykres kombo, słupki = suma godzinowa
   wszystkich relacji, linie = 3–4 relacje dominujące, duże fonty).

#### 3.n.4 Ruch pojazdów ciężkich według kierunków i relacji

**Struktura identyczna z 3.n.3** — różni się WYŁĄCZNIE kategorią
pojazdów (tylko ciężarowe + ciężarowe z naczepami zamiast wszystkich
kategorii). To nie jest przypadek — to świadoma reguła projektowa.

Akapit analityczny (bespoke tekst, analogiczny w stylu do 3.n.3, ale
opisujący wyłącznie ruch ciężki: dominujące relacje ciężkie, ich udział
w całkowitym ruchu ciężkim punktu, UPC).

1. **T5 — Zestawienie relacji ruchu pojazdów ciężkich.** Kolumny:
   `Opis relacji | Suma [poj./dobę] | Udział w ruchu ciężkim`.
   **KRYTYCZNE**: musi mieć **dokładnie tyle samo wierszy i te same
   relacje (w tej samej kolejności)**, co tabela T3/T4 w 3.n.2/3.n.3 —
   łącznie z relacjami o zerowym ruchu ciężkim (wtedy `0` / `0,0%`, nie
   pomijać wiersza). Nigdy nie przycinać do tylko-niezerowych.
2. **R9 — Wykres: rozkład godzinowy ruchu pojazdów ciężkich według
   relacji.** ⚠️ Placeholder wielokrotnego użytku — jak wyżej, dopóki
   nie ma dedykowanego generatora, używa się obrazu z Punktu 1
   (identycznego jak w 3.1.4, nie mylić z R8 z 3.n.3 — to inny slot,
   ale też placeholder z Punktu 1).

#### 3.n.5 Rozkład godzinowy ruchu według relacji

Zdanie zapowiadające łączy tabelę i pierwszy wykres tej sekcji:
"Tabela 3.n.6 oraz Rysunek 3.n.10 przedstawiają rozkład godzinowy
ruchu zmotoryzowanego i niezmotoryzowanego zsumowanego dla wszystkich
relacji łącznie."

1. **T6 — Rozkład godzinowy ruchu (suma wszystkich relacji).** 24
   wiersze (godziny 00–23) + nagłówek. Kolumny: `Godzina | Ruch
   zmotoryzowany [poj./h] | Udział w dobie [%] | Ruch niezmotoryzowany
   [poj./h] | Udział w dobie [%]`.
2. Przypis kursywą: odniesienie do pliku źródłowego xlsx (rozbicie
   godzinowe per relacja, nie tylko suma, jest wyłącznie w załączniku).
3. 🟡 Jeśli dane niezmotoryzowane są estymowane (patrz plik reguł) —
   dodatkowy przypis kursywą wyjaśniający metodę estymacji.
4. **R10 — Wykres kombo: rozkład godzinowy ruchu zmotoryzowanego wg
   kategorii** (12 kategorii, słupki skumulowane) **+ udział w ruchu
   dobowym** (linia, prawa oś). ⚠️ Placeholder wielokrotnego użytku —
   dla wszystkich punktów obraz z Punktu 1, dopóki brak docelowego
   generatora z poprawnymi danymi.

#### 3.n.6 Rozkład dobowy i pory ruchu

1. **T7 — Ruch według pór doby.** 3 wiersze (Dzień, Noc, Suma) +
   nagłówek. Kolumny: `Pora | Zakres godzin | Suma [poj.] | Udział
   [%]`.
2. **R11 — Udział pory dziennej i nocnej w ruchu.** Prosty wykres
   słupkowy (2 słupki). Point-specific — to jeden z tych wykresów, dla
   których MAMY już generator z poprawnymi danymi (nie jest to
   placeholder z Punktu 1, tylko realnie liczony wykres dla każdego
   punktu z osobna).
3. Akapit: interpretacja podziału dzień/noc (udział %, uzasadnienie
   podziału na dwie, nie trzy, pory doby).

#### 3.n.7 Struktura rodzajowa ruchu

Akapit intro (bespoke per punkt: dominujące kategorie, udział ruchu
gospodarczego, niezmotoryzowanego).

1. **T8 — Struktura rodzajowa ruchu (podsumowanie).** 12 wierszy
   kategorii + wiersz Suma. Kolumny: `Kategoria | Suma [poj./dobę] |
   Udział zmotoryzowane [%] | Udział całe [%]`. Kolumna "zmotoryzowane"
   = wartość / SDR (tylko dla 8 kategorii mechanicznych, "-" dla
   rowery/hulajnogi/piesi/piesi z potrzebami). Kolumna "całe" = wartość
   / suma wszystkich 12 kategorii (dla wszystkich wierszy). Te dwie
   kolumny mają się różnić wartościami dla kategorii mechanicznych.
2. Przypis kursywą: suma kategorii jest wyższa niż SDR (bo SDR nie
   uwzględnia niezmotoryzowanych) — z realnymi liczbami.
3. Przypis kursywą: pełna tabela godzinowa struktury rodzajowej jest
   wyłącznie w załączniku xlsx (nie w treści raportu, ze względu na
   objętość).

#### 3.n.8 Komentarz analityczny

Jeden akapit podsumowujący punkt (bespoke, ~5-6 zdań): charakterystyka
ruchu, porównanie skali do innych punktów projektu, spójność danych,
zastrzeżenia jakościowe jeśli występują.

---

## 6. Rozdział 4 — Podsumowanie

*(scalone dawne rozdziały "Analiza łączna" + "Wnioski i podsumowanie")*

Akapit wprowadzający: zakres projektu, punkty objęte pomiarem,
zastrzeżenia porównywalności (np. różne dni tygodnia pomiaru między
punktami).

### 4.1 Zestawienie zbiorcze punktów pomiarowych
- Tabela: `ID | Nazwa punktu | Zakres pomiaru | SDR [poj./dobę] |
  Szczyt dobowy`, jeden wiersz na punkt.
- Akapit interpretacyjny.
- Wykres porównawczy SDR (słupkowy, jeden słupek na punkt).

### 4.2 Struktura rodzajowa i szczyty godzinowe w skali projektu
- Tabela porównawcza struktury rodzajowej (kategorie w wierszach,
  punkty w kolumnach, w %). Wiersz "Środki transportu publicznego" (NIE
  "Transport publiczny" — to ostatnie sugeruje pieszych/pasażerów).
- Wykres porównawczy struktury (grupowany słupkowy).
- Akapit: wszystkie punkty używają tych samych stałych okien
  szczytowych (7–8, 15–16) — porównywalność.
- Wykres: natężenie w oknach szczytowych, per punkt.

### 4.3 Wnioski i rekomendacje
- Akapit: charakterystyka poszczególnych punktów i różnice między nimi.
- Akapit: kluczowe różnice (dominująca relacja, struktura rodzajowa,
  rytm dobowy).
- Akapit: rekomendacje do dalszych opracowań (jakość danych,
  ujednolicenie metodologii między pomiarami).

## 7. Rozdział 5 — Literatura i spis załączników

Wyłącznie:
1. Zdanie: "Niniejszy raport został opracowany zgodnie z wytycznymi
   GDDKiA: [link do oficjalnej strony gov.pl]."
2. Zdanie: "Nierozłącznym elementem niniejszego raportu są pliki xlsx
   zgodnie z wykazem. W plikach tych zestawiono wyniki pomiarów a także
   ich kluczowe charakterystyki."
3. Goła lista nazw plików `.xlsx` (bez opisów, bez dodatkowych kolumn) —
   jeden plik na punkt pomiarowy, nazwa wzorcowa:
   `wynik_tabele_Punkt{N}_{ID}.xlsx`.

---

## 8. Podsumowanie liczby elementów na punkt (typowy przypadek, ~12 relacji)

| Podrozdział | Tabele | Rysunki |
|---|---|---|
| 3.n.1 | T1, T2 (2) | R1, R2, R3 (3) |
| 3.n.2 | T3 (1) | R4, R5, R6, R7 (4) |
| 3.n.3 | T4 (1, warunkowa) | R8 (1) |
| 3.n.4 | T5 (1) | R9 (1) |
| 3.n.5 | T6 (1) | R10 (1) |
| 3.n.6 | T7 (1) | R11 (1) |
| 3.n.7 | T8 (1) | — |
| 3.n.8 | — | — |
| **Razem** | **8 tabel** | **11 rysunków** |

Jeśli T4 jest pomijana (przypadek brzegowy braku danych), zostaje 7
tabel — reszta numeracji tabel przesuwa się o 1 w dół, numeracja
rysunków się NIE zmienia (T i R to niezależne liczniki).
