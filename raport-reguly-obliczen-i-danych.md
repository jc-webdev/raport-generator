# Reguły obliczeń, źródła danych i przypadki brzegowe

> Towarzyszy plikowi `raport-specyfikacja-struktura.md` (który opisuje
> UKŁAD dokumentu). Ten plik opisuje SKĄD biorą się liczby i jak je
> liczyć.

---

## 1. Dane wejściowe

Dla każdego punktu pomiarowego: plik
`wynik_tabele_Punkt{N}_{ID}.xlsx` z arkuszami:

| Arkusz | Zawartość |
|---|---|
| `Parametry pomiaru` | Metadane pomiaru (data, godziny, warunki) |
| `Ruch wg kierunkow` | Zestawienie relacji (pomocniczy, zwykle niepotrzebny — patrz niżej) |
| `Pory doby` | Agregaty dzień/wieczór/noc (stary podział — NIE używać, przeliczać z arkusza godzinowego) |
| `Struktura rodzajowa` | Sumy dobowe per kategoria (12 kategorii) — **źródło prawdy dla SDR i sum kategorii** |
| `Godzinowa szczegolowa` | Wiersz = (Wlot, Kierunek/manewr, Godzina), kolumny = 12 kategorii pojazdów. **Główne źródło do wszystkich tabel/wykresów godzinowych i relacyjnych.** |

Kolumny arkusza `Godzinowa szczegolowa`: `Wlot, Kierunek, Godz,
b.moto, c.osobowe, c3.mikrobusy, d.dostawcze, e.ciezarowe,
f.ciezarowe.z.naczepami, g.autobusy, h.rolne, rowery, hulajnogi,
pieszy, pieszy potrzeby`.

Grupy kategorii:
- **Zmotoryzowane (SDR)**: `b.moto, c.osobowe, c3.mikrobusy,
  d.dostawcze, e.ciezarowe, f.ciezarowe.z.naczepami, g.autobusy,
  h.rolne` (8 kategorii).
- **Niezmotoryzowane**: `rowery, hulajnogi, pieszy, pieszy potrzeby`
  (4 kategorie).
- **Ciężkie**: `e.ciezarowe, f.ciezarowe.z.naczepami` (2 kategorie,
  podzbiór zmotoryzowanych).

## 2. Reguła sortowania relacji (obowiązuje we wszystkich tabelach)

Klucz sortowania: `(kolejność_wlotu, kolejność_manewru)`.

```
WLOT_ORDER = {PN: 0, WSCH: 1, PD: 2, ZACH: 3}
MANEWR_ORDER = {Prawo: 0, Wprost: 1, Lewo: 2, Zawracający: 3}
```

## 3. Generowanie opisu relacji (kolumna "Opis relacji")

Dla skrzyżowań o regularnej geometrii krzyżowej (4 wloty, kąty ~90°):

```
bearing = {PN: 0, WSCH: 90, PD: 180, ZACH: 270}   # stopnie, zgodnie z ruchem wskazówek zegara
heading(wlot) = (bearing[wlot] + 180) mod 360      # kierunek jazdy wjeżdżającego pojazdu

exit_bearing(wlot, manewr):
  Wprost      -> heading(wlot)
  Prawo       -> heading(wlot) + 90
  Lewo        -> heading(wlot) - 90
  Zawracający -> bearing(wlot)                      # wraca tym samym wlotem

opis = "{Z/Ze} {wlot_dopełniacz} na {exit_biernik}, {manewr_tekst}"
```

Przykład: `ZACH, Lewo` → heading=90(wschód) → exit=0(północ) → "Z
zachodu na północ, w lewo".

Prefiks "Ze" (zamiast "Z") tylko dla wlotu `WSCH` (eufonia: "Ze
wschodu").

**Dla skrzyżowań o nieregularnej geometrii** (np. typu T, brak jednego
wlotu) — NIE zgadywać kierunku docelowego geometrycznie (może dać
błędny/niemożliwy wynik). Używać formy skróconej: `"{Z/Ze}
{wlot_dopełniacz}, {manewr_tekst}"` (bez klauzuli "na X"). Przykład:
"Z południa, w lewo".

Rozpoznanie "nieregularne": liczba wlotów ≠ 4, lub gdy suma kątów
wlotów nie odpowiada standardowemu krzyżowi.

## 4. Wzory obliczeniowe

| Wielkość | Wzór |
|---|---|
| **SDR (relacja)** | suma kategorii zmotoryzowanych dla danej (wlot, manewr), zsumowana po wszystkich godzinach |
| **SDR (punkt)** | suma SDR wszystkich relacji |
| **Szczyt (relacja)** | max godzinowej sumy zmotoryzowanych tej relacji + godzina wystąpienia |
| **Relacja z niezmot.** | SDR(relacja) + suma niezmotoryzowanych tej relacji |
| **Ruch ciężki (relacja)** | suma kategorii ciężkich dla danej (wlot, manewr) |
| **Ruch ciężki (punkt)** | suma ruchu ciężkiego wszystkich relacji (lub suma z arkusza `Struktura rodzajowa`, jeśli arkusz godzinowy jest niewiarygodny — patrz przypadki brzegowe) |
| **UPC (relacja)** | ruch_ciężki(relacja) / SDR(relacja) × 100% |
| **Dzień** | suma zmotoryzowanych godz. 06:00–21:59 |
| **Noc** | suma zmotoryzowanych godz. 22:00–05:59 |
| **Struktura — Udział zmotoryzowane** | wartość_kategorii / SDR × 100% (tylko 8 kategorii mechanicznych; "-" dla 4 niezmotoryzowanych) |
| **Struktura — Udział całe** | wartość_kategorii / suma_wszystkich_12_kategorii × 100% (wszystkie 12 wierszy) |

## 5. Wykres kombo — rozkład godzinowy wg relacji (docelowy generator, R8/R9)

- Słupki: suma godzinowa wszystkich relacji (24 wartości).
- Linie: 3–4 relacje o najwyższym SDR (nie więcej — przy większej
  liczbie serii wykres staje się nieczytelny).
- Font: Carlito/Calibri, rozmiar osi/legendy ≥10–11pt w eksporcie PNG.
- Paleta: pomarańcz marki (`#FF7900`) dla słupków, ciemniejsze/
  kontrastowe kolory dla linii.

## 6. Wykres kombo — profil dobowy wg kategorii (docelowy generator, R10)

- Słupki skumulowane (stacked bar), 12 kategorii, 24 godziny.
- Linia (prawa oś): udział godziny w ruchu dobowym całkowitym [%].
- Legenda: wszystkie 12 kategorii + linia %.

## 7. Format liczb

- Separator tysięcy: spacja (`28 558`, nie `28,558` ani `28558`).
- Procenty: przecinek dziesiętny, zawsze 1 miejsce po przecinku
  (`43,1%`, nie `43%` ani `43.1%`).
- Godziny: format `HH:MM` (`07:00`, nie `7:00`).

## 8. Przypadki brzegowe (data quality)

### 8.1 Kategoria wyzerowana w arkuszu godzinowym mimo niezerowej sumy w arkuszu struktury rodzajowej

Obserwowane w praktyce dla różnych kategorii w różnych punktach (nie
jest to odosobniony przypadek — sugeruje błąd systemowy w kroku
agregacji History → Quantity dla niektórych kombinacji kategoria ×
punkt; **wymaga zbadania w pipeline'ie źródłowym**, nie tylko obejścia
w warstwie raportowej).

**Wykrywanie**: dla danej grupy kategorii (niezmotoryzowane lub
ciężkie), jeśli `suma(arkusz godzinowy) == 0` ale `suma(arkusz
struktury rodzajowej) > 0` → dane godzinowe/relacyjne dla tej grupy są
niewiarygodne.

**Obsługa — niezmotoryzowani wyzerowani**:
- Tabela T4 (relacje z niezmot., 3.n.3) — **pomijana całkowicie**,
  zastąpiona jednym zdaniem wyjaśniającym. Nie da się wiarygodnie
  rozbić na relacje.
- Kolumna "Ruch niezmotoryzowany" w T6 (3.n.5, godzinowa) —
  **szacowana**: `suma_dobowa_niezmot (z arkusza struktury rodzajowej)
  × (ruch_zmotoryzowany[godzina] / SDR_calosc)` — czyli rozłożona wg
  godzinowego profilu ruchu zmotoryzowanego tego samego punktu.
  Przypis kursywą pod tabelą wyjaśnia metodę.

**Obsługa — ciężkie wyzerowane**:
- Tabela T5 (3.n.4) — **NIE pomijana** (w przeciwieństwie do
  niezmotoryzowanych) — relacje szacowane proporcjonalnie: `suma_
  ciężkich_dobowa (z arkusza struktury rodzajowej) × (SDR(relacja) /
  SDR(punkt))`, zaokrąglone do liczb całkowitych, z zachowaniem TEJ
  SAMEJ liczby wierszy co T3/T4. Przypis kursywą wyjaśnia metodę.

W obu przypadkach: **żadna osobna sekcja "Uwagi o jakości danych" nie
jest tworzona** — tylko krótki przypis kursywą w miejscu wystąpienia,
w tym samym stylu co istniejące przypisy (np. "Suma kategorii jest
wyższa niż SDR...").

### 8.2 Drobna rozbieżność sum między arkuszami (rzędu 1–2%)

Nawet dla kategorii, które nie są całkowicie wyzerowane, suma z arkusza
godzinowego może się nieznacznie różnić od sumy w arkuszu struktury
rodzajowej. **Autorytatywne źródło dla SDR/sum kategorii pokazywanych w
tabeli parametrów i strukturze rodzajowej: arkusz `Struktura
rodzajowa`.** Tabele relacji (T3, T4, T5) bazują na arkuszu godzinowym
i mogą się sumować do nieznacznie innej wartości — to nie błąd
generatora, tylko cecha danych źródłowych; nie wymaga specjalnej
obsługi poza upewnieniem się, że liczba wyświetlana jako "SDR" w
parametrach zawsze pochodzi z arkusza struktury rodzajowej, nie z sumy
tabeli relacji.

### 8.3 Zduplikowane etykiety relacji AISP

Dwie bramki o identycznym (wlot, manewr) — sumowane automatycznie w
kroku agregacji po kluczu (wlot, manewr). Nie wymaga żadnej specjalnej
wzmianki w treści raportu (dzieje się to niejawnie podczas budowy
tabel).

### 8.4 Skrzyżowanie o nietypowej liczbie relacji

- **Typowo ~12 relacji** (4 wloty × 3 manewry, część kombinacji
  zerowa). Może być mniej (skrzyżowania typu T, 4-6 relacji) lub
  więcej (skrzyżowania z zawracaniem na każdym wlocie, do 16).
- Generator MUSI działać poprawnie niezależnie od liczby wierszy —
  tabele T3/T4/T5 zawsze mają tyle wierszy, ile jest faktycznych
  relacji (T5 dokładnie tyle samo co T3/T4, patrz sekcja struktury).
- Budżet 10 stron/punkt jest kalibrowany na ~12 relacji. Przy istotnie
  większej liczbie (>16) punkt może przekroczyć 10 stron — akceptowalne,
  priorytetem jest poprawność danych, nie sztywne dotrzymanie stron.

## 9. Obrazy — zasady doboru pliku (stan przejściowy)

| Rysunek | Źródło |
|---|---|
| R1 Mapka lokalizacji | point-specific (osadzona mapa miasta) |
| R2 Schemat skrzyżowania | point-specific (schemat z etykietami wlotów) |
| R3 Widok z kamery | point-specific (zrzut z nagrania) |
| R4 SDR (diagram przepływów) | point-specific (docelowo Visum) |
| R5 UPC | **placeholder = ten sam plik co R4 tego samego punktu**, dopóki nie ma dedykowanego generatora UPC |
| R6 Szczyt poranny | point-specific (docelowo Visum) |
| R7 Szczyt popołudniowy | point-specific (docelowo Visum) |
| R8 Godzinowy wg relacji (3.n.3) | **placeholder = plik z Punktu 1** dla wszystkich punktów, dopóki nie ma dedykowanego generatora |
| R9 Godzinowy ciężkich wg relacji (3.n.4) | **placeholder = plik z Punktu 1** (inny plik niż R8, ale też z Punktu 1) |
| R10 Profil dobowy wg kategorii | **placeholder = plik z Punktu 1** |
| R11 Udział dnia/nocy | point-specific (prosty wykres 2-słupkowy, generator już gotowy — liczyć naprawdę dla każdego punktu) |

Reguła ogólna: **gdy tylko powstanie dedykowany, poprawny generator
dla danego typu rysunku, przestaje on być placeholderem i staje się
point-specific dla wszystkich punktów** — bez zmiany numeracji ani
pozycji w dokumencie.

## 10. Nazwy plików załączników

Wzorzec: `wynik_tabele_Punkt{N}_{ID}.xlsx`, gdzie `{N}` = numer punktu
(1, 2, 3...), `{ID}` = identyfikator punktu (P1, P2, P3...). Lista
trafia do rozdziału 5 (Literatura i spis załączników) bez opisów.
