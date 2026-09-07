# 3. Kod generujący tabele i wykresy (dopracowanie)

## Cel

Celem tej sekcji jest podsumowanie działającego kodu (`drogi.ipynb`), który na podstawie danych z AISP (poprzez plik pośredni `Quantity.csv`) automatycznie generuje komplet tabel i wykresów dla jednego punktu pomiarowego, zgodnie z wymaganiami opisanymi w sekcji 4.2. Kod został przetestowany na przykładowych danych — wynik tego testu (tabele i wykresy) jest załączony poniżej jako referencja.

## Zakres

Sekcja obejmuje:
- opis przepływu pracy notatnika (co robi, krok po kroku),
- opis struktury kodu i miejsca konfiguracji,
- przykładowy wynik działania na testowym punkcie pomiarowym (tabele + miejsca na wykresy).

Sekcja nie obejmuje: szczegółowych reguł obliczeń (patrz 4.2), standardu kategoryzacji pojazdów (3.3), budowy Sankeya w Visum (3.4 — ten notatnik już go nie generuje, patrz niżej).

---

## Co robi notebook

Notatnik przyjmuje jeden plik wejściowy (`Quantity.csv` — naszą agregację z `History`, patrz 4.2) oraz konfigurację jednego punktu pomiarowego, i generuje z nich komplet materiałów do raportu: 5 tabel w formacie CSV/Excel oraz 3 wykresy w formacie PNG, stylistycznie zgodne z marką Orange Polska.

Przepływ pracy:

1. **Wczytanie i walidacja** — wczytuje `Quantity.csv`, wylicza godzinę z timestampu, wypisuje podstawowe statystyki kontrolne (liczba wierszy, wykryte kierunki i godziny, suma kontrolna SDR).
2. **Obliczenie SDR i szczytów** — liczy średni dobowy ruch (SDR) oraz godzinę szczytową, osobno per kierunek i łącznie dla punktu.
3. **Generowanie 5 tabel** (patrz niżej — wynik przykładowy).
4. **Generowanie 3 wykresów** (patrz niżej — placeholdery).
5. **Eksport zbiorczy** — wszystkie tabele CSV scalane są automatycznie do jednego pliku `wynik_tabele_<nazwa_punktu>.xlsx` (jeden arkusz na tabelę).
6. **Pomocniczo:** generowany jest też plik tekstowy z gotowym promptem do dalszej analizy AI na podstawie wygenerowanych tabel — element pomocniczy, poza głównym zakresem raportu.

## Struktura kodu

- **Jedna komórka konfiguracyjna** na początku notatnika — to jedyne miejsce, które trzeba zmienić dla nowego punktu pomiarowego. Zawiera:
  - metadane punktu (miasto, nazwa, numer, data pomiaru, warunki),
  - `KIERUNEK_MAPPING` — mapowanie liter kierunku z AISP na wlot i typ relacji (ręczne, per punkt — patrz ograniczenia AISP w sekcji 1),
  - `KOLEJNOSC_KIERUNKOW` — kolejność prezentacji w tabelach i na wykresach,
  - kategorie pojazdów (mechaniczne / niezmotoryzowane),
  - paletę kolorów i styl wykresów zgodny z marką Orange (pomarańcz `#FF7900` jako akcent, czernie/szarości jako kolory drugorzędne).
- **Kolejne komórki** to pojedyncze, niezależne moduły — jeden moduł = jedna tabela lub jeden wykres. Każdy zapisuje swój wynik do osobnego pliku.
- **Diagram Sankey usunięty** — docelowo budowany będzie w Visum (patrz 3.4), więc nie jest już częścią tego notatnika.

## Wynik przykładowy — punkt testowy

Dane wejściowe: `Quantity.csv`, punkt: **Skrzyżowanie Łódzka – Generała Władysława Andersa** (Toruń), pomiar z 27 maja 2026 (środa, dzień roboczy, +20°C, bez opadów), 14 relacji ruchu.

### Tabela 21. Podstawowe parametry pomiaru

| Parametr | Wartość |
|:---|:---|
| Data pomiaru | 27 maja 2026 |
| Czas rozpoczęcia | 27.05.2026 00:00:00 |
| Czas zakończenia | 27.05.2026 23:59:59 |
| Czas trwania | 24 godziny |
| SDR | 31 185 poj./dobę |
| Szczyt ruchu | 2352 poj./h o godz. 15:00 |
| Dzień tygodnia | Środa (dzień roboczy) |
| Warunki atmosferyczne | Bez opadów, temperatura +20°C |
| Metoda pomiaru | Rejestracja wideo, klasyfikacja automatyczna z weryfikacją |

### Tabela 22. Ruch według kierunków

| Parametr | B | A | C | E | D | F | G | I | J | H | M | K | L | N |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Wlot | PD | PD | PD | WSCH | WSCH | WSCH | ZACH | ZACH | ZACH | ZACH | PN | PN | PN | PN |
| Relacja | Wprost | Prawo | Lewo | Wprost | Lewo | Prawo | Lewo | Wprost | Prawo | Wprost | Lewo | Wprost | Wprost | Prawo |
| SDR [poj./dobę] | 1948 | 939 | 482 | 4039 | 931 | 688 | 1680 | 3362 | 6024 | 2501 | 2727 | 2084 | 2732 | 1048 |
| SDR osobowe | 1849 | 885 | 458 | 2918 | 780 | 622 | 1592 | 2306 | 5608 | 2222 | 2584 | 1987 | 2371 | 981 |
| SDR dostawcze | 46 | 46 | 16 | 291 | 42 | 28 | 67 | 299 | 207 | 165 | 102 | 41 | 198 | 48 |
| SDR ciężarowe z naczepami | 3 | 0 | 0 | 493 | 6 | 2 | 4 | 373 | 20 | 29 | 0 | 5 | 10 | 2 |
| SDR ciężarowe | 6 | 5 | 2 | 268 | 20 | 10 | 9 | 306 | 23 | 26 | 5 | 8 | 50 | 9 |
| SDR autobusy i mikrobusy | 32 | 1 | 0 | 32 | 74 | 1 | 1 | 37 | 97 | 20 | 4 | 36 | 72 | 3 |
| Szczyt [poj./h] | 160 | 71 | 48 | 335 | 87 | 67 | 168 | 250 | 492 | 240 | 206 | 186 | 186 | 84 |
| Godz. szczytu | 18:00 | 11:00 | 15:00 | 07:00 | 15:00 | 17:00 | 15:00 | 15:00 | 16:00 | 15:00 | 07:00 | 18:00 | 07:00 | 16:00 |

### Tabela 23. Rozkład według pór doby

| Pora | B | A | C | E | D | F | G | I | J | H | M | K | L | N | Suma | Udział |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dzienna (06:00–18:00) | 1400 | 688 | 342 | 3034 | 651 | 502 | 1221 | 2459 | 4468 | 2000 | 2032 | 1524 | 1969 | 775 | 23 065 | 74,0% |
| Wieczorna (18:00–22:00) | 498 | 210 | 131 | 628 | 227 | 171 | 387 | 549 | 1174 | 400 | 482 | 489 | 526 | 226 | 6 098 | 19,6% |
| Nocna (22:00–06:00) | 50 | 41 | 9 | 377 | 53 | 15 | 72 | 354 | 382 | 101 | 213 | 71 | 237 | 47 | 2 022 | 6,5% |
| **Suma** | 1948 | 939 | 482 | 4039 | 931 | 688 | 1680 | 3362 | 6024 | 2501 | 2727 | 2084 | 2732 | 1048 | **31 185** | **100%** |

### Tabela 24. Struktura rodzajowa pojazdów

| Kategoria | B | A | C | E | D | F | G | I | J | H | M | K | L | N | Suma | Udział |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Osobowe | 1849 | 885 | 458 | 2918 | 780 | 622 | 1592 | 2306 | 5608 | 2222 | 2584 | 1987 | 2371 | 981 | 27 163 | 84,5% |
| Dostawcze | 46 | 46 | 16 | 291 | 42 | 28 | 67 | 299 | 207 | 165 | 102 | 41 | 198 | 48 | 1 596 | 5,0% |
| Ciężarowe z naczepami | 3 | 0 | 0 | 493 | 6 | 2 | 4 | 373 | 20 | 29 | 0 | 5 | 10 | 2 | 947 | 2,9% |
| Ciężarowe | 6 | 5 | 2 | 268 | 20 | 10 | 9 | 306 | 23 | 26 | 5 | 8 | 50 | 9 | 747 | 2,3% |
| Autobusy | 32 | 1 | 0 | 23 | 69 | 0 | 0 | 31 | 96 | 17 | 0 | 34 | 61 | 1 | 365 | 1,1% |
| Mikrobusy | 0 | 0 | 0 | 9 | 5 | 1 | 1 | 6 | 1 | 3 | 4 | 2 | 11 | 2 | 45 | 0,1% |
| Rolne | 0 | 0 | 0 | 4 | 1 | 2 | 1 | 8 | 2 | 0 | 0 | 0 | 2 | 4 | 24 | 0,1% |
| Moto | 12 | 2 | 6 | 33 | 8 | 23 | 6 | 33 | 67 | 39 | 32 | 7 | 29 | 1 | 298 | 0,9% |
| Rowery | 16 | 48 | 12 | 53 | 44 | 46 | 59 | 28 | 29 | 96 | 55 | 0 | 41 | 52 | 579 | 1,8% |
| Hulajnogi | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 5 | 0 | 0 | 4 | 18 | 0,1% |
| Piesi | 16 | 55 | 19 | 16 | 2 | 0 | 39 | 2 | 22 | 26 | 132 | 0 | 6 | 27 | 362 | 1,1% |
| Pieszy potrzeby | 0 | 2 | 1 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 8 | 0 | 0 | 2 | 15 | 0,0% |
| **Suma** | 1980 | 1047 | 514 | 4108 | 977 | 734 | 1783 | 3392 | 6078 | 2623 | 2927 | 2084 | 2779 | 1133 | **32 159** | **100%** |

### Tabela 25. Rozkład godzinowy szczegółowy

336 wierszy (14 relacji × 24 godziny), pełny rozkład wg wszystkich 12 kategorii pojazdów w podziale godzinowym. Zbyt obszerna do wklejenia w całości — dostępna w pliku `tab25_godzinowa_<nazwa_punktu>.csv` oraz jako arkusz w zbiorczym Excelu.

---

## Wykresy (placeholdery do uzupełnienia na Confluence)

> **[PLACEHOLDER — Wykres 1: Rozkład ruchu według pór doby, per kierunek]**
> Wykres słupkowy grupowany — dla każdego z 14 kierunków trzy słupki (dzienna/wieczorna/nocna pora doby), z liczbą pojazdów nad słupkiem. Pomarańcz (`#FF7900`) oznacza porę dzienną jako serię wiodącą, ciemny i jasny szary — porę wieczorną i nocną. Plik: `wykres_pory_doby_<nazwa_punktu>.png`.

> **[PLACEHOLDER — Wykres 2: Rozkład godzinowy ruchu według relacji]**
> Wykres liniowy — natężenie ruchu [poj./h] w każdej z 24 godzin doby, osobna linia dla każdego z 14 kierunków (kolory z palety marki: pomarańcz/szarości/czerń, cyklicznie przypisywane wg kolejności kierunków). Pozwala zobaczyć kształt szczytów porannych i popołudniowych osobno dla każdej relacji. Plik: `rozklad_godzinowy_relacje_<nazwa_punktu>.png`.

> **[PLACEHOLDER — Wykres 3: Zbiorczy rozkład wg pór doby]**
> Mały wykres słupkowy (3 słupki: dzienna/wieczorna/nocna) pokazujący sumę ruchu na całym punkcie w każdej porze doby, z wartością bezwzględną i udziałem % nad słupkiem. Przeznaczony jako kompaktowa grafika do wstawienia obok tekstu w raporcie. Plik: `wykres_slupkowy_pory_doby_<nazwa_punktu>.png`.

---

## Status

Kod działa end-to-end na przykładowych danych (`Quantity.csv` dla punktu testowego powyżej) — wygenerowano bez błędów 5 tabel, 3 wykresy PNG oraz zbiorczy plik Excel. Wynik zgodny z wymaganiami opisanymi w sekcji 4.2 (dane wejściowe, reguły obliczeń, format wynikowy).
