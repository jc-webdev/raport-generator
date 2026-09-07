"use strict";

const path = require("path");
const { HeadingLevel } = require("docx");
const { Liczniki } = require("./liczniki");
const { liczba, procent } = require("./formatowanie");
const { akapit, naglowek, tabela, podpisKursywa, obrazek, wierszZObrazkiem, SZEROKOSC_TRESCI_CM } = require("./style");

/**
 * Buduje pełny blok jednego punktu pomiarowego (8 podrozdziałów, T1-T8,
 * R1-R11) zgodnie z raport-specyfikacja-struktura.md §5.
 *
 * @param {object} punkt - jeden element punkty[] z projekt.json (patrz fixture)
 * @param {string} prefiks - "3.{n}" numer rozdziału.punktu, np. "3.1"
 * @param {string} baseDir - katalog bazowy do rozwiązywania względnych ścieżek assets
 * @returns {{children: Paragraph[]|Table[], liczbaRysunkow: number, liczbaTabel: number}}
 */
function budujPunkt(punkt, prefiks, baseDir) {
  const liczniki = new Liczniki(prefiks);
  const o = punkt.obliczenia;
  const dzieci = [];

  const sciezka = (plik) => path.resolve(baseDir, plik);
  const dodajRysunek = (assetKlucz, zapowiedz, podpis, szerokoscCm) => {
    const nr = liczniki.nastepnyRysunek();
    dzieci.push(akapit(zapowiedz(nr)));
    dzieci.push(obrazek(sciezka(punkt.assets[assetKlucz].plik), szerokoscCm));
    dzieci.push(podpisKursywa(podpis(nr)));
    return nr;
  };
  let liczbaPodrozdzialow = 0;
  const dodajPodrozdzial = (tytul) => {
    liczbaPodrozdzialow += 1;
    dzieci.push(naglowek(tytul, HeadingLevel.HEADING_3));
  };

  // Nagłówek punktu jako Heading2 (pod rozdziałem 3, który jest Heading1 w
  // budujRaport.js) — podpunkty punktu (3.n.1 itd.) schodzą wtedy do
  // Heading3, żeby hierarchia w spisie treści była poprawna.
  dzieci.push(naglowek(`Punkt ${punkt.numer} - ${punkt.nazwa}`, HeadingLevel.HEADING_2, { pageBreakBefore: true }));
  dzieci.push(akapit(punkt.teksty.lokalizacja));

  // --- 3.n.1 Lokalizacja i karta skrzyżowania -----------------------------
  dodajPodrozdzial("Lokalizacja i karta skrzyżowania");

  const nrT1 = liczniki.nastepnaTabela();
  const nrR1 = liczniki.nastepnyRysunek();
  dzieci.push(akapit(
    `Tabela ${nrT1} przedstawia podstawowe parametry pomiaru dla tego punktu wraz z mapą `
    + `lokalizacji (Rysunek ${nrR1}) w ostatnim wierszu.`,
  ));
  dzieci.push(tabela(
    ["Parametr", "Wartość"],
    [
      ["ID", punkt.id],
      ["Nazwa", punkt.nazwa],
      ["Data pomiaru", punkt.metadanePomiaru.dataPomiaru],
      ["Dzień tygodnia", punkt.metadanePomiaru.dzienTygodnia],
      ["Czas rozpoczęcia", punkt.metadanePomiaru.czasRozpoczecia],
      ["Czas zakończenia", punkt.metadanePomiaru.czasZakonczenia],
      ["Czas trwania", "24 h"],
      ["SDR", `${liczba(o.sdr)} poj./dobę`],
      ["Szczyt dobowy", `${liczba(o.szczytDobowy.wartosc)} poj./h o godz. ${o.szczytDobowy.godzina}`],
      ["Warunki atmosferyczne", punkt.metadanePomiaru.warunkiAtmosferyczne],
      ["Metoda pomiaru", "Pomiar wideo z automatyczną klasyfikacją i weryfikacją manualną"],
    ],
    [false, false],
    [30, 70],
    // Ostatni wiersz: scalone obie kolumny, mapka lokalizacji + jej podpis
    // wycentrowane w środku tej samej komórki — jak w referencyjnym raporcie.
    wierszZObrazkiem(
      sciezka(punkt.assets.mapkaLokalizacji.plik), 2,
      `Rysunek ${nrR1}. Mapka lokalizacji - ${punkt.nazwa}.`,
    ),
  ));
  dzieci.push(podpisKursywa(`Tabela ${nrT1}. Parametry pomiaru - Punkt ${punkt.numer}.`));

  dodajRysunek("wykresPogoda",
    (nr) => `Rysunek ${nr} przedstawia przebieg temperatury i opadów w trakcie pomiaru.`,
    (nr) => `Rysunek ${nr}. Przebieg warunków atmosferycznych (temperatura, opady) - ${punkt.nazwa}.`,
    SZEROKOSC_TRESCI_CM);

  dodajRysunek("schematSkrzyzowania",
    (nr) => `Rysunek ${nr} przedstawia schemat skrzyżowania z oznaczeniem wlotów.`,
    (nr) => `Rysunek ${nr}. Schemat skrzyżowania - ${punkt.nazwa}.`);

  dodajRysunek("zdjecieKamery",
    (nr) => `Rysunek ${nr} przedstawia widok z kamery pomiarowej.`,
    (nr) => `Rysunek ${nr}. Widok z kamery - ${punkt.nazwa}.`);

  const nrT2 = liczniki.nastepnaTabela();
  dzieci.push(akapit(`Tabela ${nrT2} przedstawia wykaz wlotów skrzyżowania.`));
  dzieci.push(tabela(
    ["Nr wlotu", "Opis wlotu", "Kierunek", "Uwagi"],
    punkt.wloty.map((w) => [String(w.nrWlotu), w.opis, w.kierunek, w.uwagi || "-"]),
    [true, false, false, false],
    [12, 43, 20, 25],
  ));
  dzieci.push(podpisKursywa(`Tabela ${nrT2}. Wykaz wlotów - Punkt ${punkt.numer}.`));

  // --- 3.n.2 Diagramy przepływów ruchu ------------------------------------
  dodajPodrozdzial("Diagramy przepływów ruchu");
  dzieci.push(akapit(punkt.teksty.organizacjaRuchu));

  const nrT3 = liczniki.nastepnaTabela();
  dzieci.push(akapit(`Tabela ${nrT3} przedstawia zestawienie relacji ruchu zmotoryzowanego (SDR) i szczytów godzinowych.`));
  dzieci.push(tabela(
    ["Opis relacji", "SDR [poj./dobę]", "Udział w SDR", "Szczyt [poj./h]", "Godz. szczytu"],
    o.relacjeSDR.map((r) => [r.opis, liczba(r.sdr), procent(r.udzial), liczba(r.szczyt), r.godzinaSzczytu]),
    [false, true, true, true, true],
    [40, 16, 16, 14, 14],
  ));
  dzieci.push(podpisKursywa(`Tabela ${nrT3}. Zestawienie relacji ruchu (SDR) i szczytów godzinowych - Punkt ${punkt.numer}.`));

  dodajRysunek("sankeySDR",
    (nr) => `Rysunek ${nr} przedstawia diagram natężeń ruchu drogowego (SDR, całodobowo).`,
    (nr) => `Rysunek ${nr}. Diagram natężeń ruchu drogowego [poj./dobę] - SDR - ${punkt.nazwa}.`);

  dodajRysunek("sankeyUPC",
    (nr) => `Rysunek ${nr} przedstawia udział pojazdów ciężkich w ruchu dobowym wg relacji (UPC).`,
    (nr) => `Rysunek ${nr}. Udział pojazdów ciężkich w ruchu dobowym wg relacji [%] - UPC - ${punkt.nazwa}.`);

  dodajRysunek("sankeyPoranny",
    (nr) => `Rysunek ${nr} przedstawia diagram przepływów w godzinie szczytu porannego (${o.szczytOknoPoranne.zakres}).`,
    (nr) => `Rysunek ${nr}. Diagram natężeń ruchu drogowego w godzinie szczytu porannego (${o.szczytOknoPoranne.zakres}) - ${punkt.nazwa}.`);

  dodajRysunek("sankeyPopoludniowy",
    (nr) => `Rysunek ${nr} przedstawia diagram przepływów w godzinie szczytu popołudniowego (${o.szczytOknoPopoludniowe.zakres}).`,
    (nr) => `Rysunek ${nr}. Diagram natężeń ruchu drogowego w godzinie szczytu popołudniowego (${o.szczytOknoPopoludniowe.zakres}) - ${punkt.nazwa}.`);

  // --- 3.n.3 Ruch według kierunków i relacji ------------------------------
  dodajPodrozdzial("Ruch według kierunków i relacji");
  dzieci.push(akapit(punkt.teksty.ruchWgKierunkow));

  if (o.relacjeZNiezmotDostepne) {
    const nrT4 = liczniki.nastepnaTabela();
    dzieci.push(akapit(`Tabela ${nrT4} przedstawia zestawienie relacji ruchu łącznie z ruchem nie zmotoryzowanym.`));
    dzieci.push(tabela(
      ["Opis relacji", "Suma [poj./dobę]", "Udział"],
      o.relacjeZNiezmot.map((r) => [r.opis, liczba(r.suma), procent(r.udzial)]),
      [false, true, true],
      [55, 25, 20],
    ));
    dzieci.push(podpisKursywa(`Tabela ${nrT4}. Zestawienie relacji ruchu łącznie z ruchem nie zmotoryzowanym - Punkt ${punkt.numer}.`));
  } else {
    dzieci.push(akapit(
      "Arkusz godzinowy dla tego punktu nie rejestruje ruchu nie zmotoryzowanego w rozbiciu na relacje "
      + "(dostępna jest wyłącznie suma dobowa), dlatego tabela zestawienia relacji z ruchem nie zmotoryzowanym "
      + "nie jest prezentowana.",
      { italic: true },
    ));
  }

  dodajRysunek("godzinowaRelacje",
    (nr) => `Rysunek ${nr} przedstawia rozkład godzinowy ruchu według relacji.`,
    (nr) => `Rysunek ${nr}. Rozkład godzinowy ruchu według relacji - ${punkt.nazwa}.`,
    SZEROKOSC_TRESCI_CM);

  // --- 3.n.4 Ruch pojazdów ciężkich według kierunków i relacji ------------
  dodajPodrozdzial("Ruch pojazdów ciężkich według kierunków i relacji");
  dzieci.push(akapit(punkt.teksty.ruchPojazdowCiezkich));

  const nrT5 = liczniki.nastepnaTabela();
  dzieci.push(akapit(`Tabela ${nrT5} przedstawia zestawienie relacji ruchu pojazdów ciężkich.`));
  dzieci.push(tabela(
    ["Opis relacji", "Suma [poj./dobę]", "Udział w ruchu ciężkim"],
    o.relacjeCiezkie.map((r) => [r.opis, liczba(r.suma), procent(r.udzial)]),
    [false, true, true],
    [50, 25, 25],
  ));
  dzieci.push(podpisKursywa(`Tabela ${nrT5}. Zestawienie relacji ruchu pojazdów ciężkich - Punkt ${punkt.numer}.`));
  if (o.relacjeCiezkieEstymowane) {
    dzieci.push(akapit(
      "Arkusz godzinowy dla tego punktu nie rejestruje kategorii ciężarowe/ciężarowe z naczepami w rozbiciu "
      + "na relacje (dostępna jest wyłącznie suma dobowa). Powyższy rozkład kierunkowy jest oszacowany "
      + "proporcjonalnie do ogólnego udziału każdej relacji w SDR punktu.",
      { italic: true },
    ));
  }

  dodajRysunek("godzinowaCiezkie",
    (nr) => `Rysunek ${nr} przedstawia rozkład godzinowy ruchu pojazdów ciężkich według relacji.`,
    (nr) => `Rysunek ${nr}. Rozkład godzinowy ruchu pojazdów ciężkich według relacji - ${punkt.nazwa}.`,
    SZEROKOSC_TRESCI_CM);

  // --- 3.n.5 Rozkład godzinowy ruchu według relacji -----------------------
  dodajPodrozdzial("Rozkład godzinowy ruchu według relacji");

  const nrT6 = liczniki.nastepnaTabela();
  const nrR10 = liczniki.nastepnyRysunek();
  dzieci.push(akapit(
    `Tabela ${nrT6} oraz Rysunek ${nrR10} przedstawiają rozkład godzinowy ruchu zmotoryzowanego `
    + "i nie zmotoryzowanego zsumowanego dla wszystkich relacji łącznie.",
  ));
  dzieci.push(tabela(
    ["Godzina", "Ruch zmotoryzowany [poj./h]", "Udział w dobie [%]", "Ruch nie zmotoryzowany [poj./h]", "Udział w dobie [%]"],
    o.godzinowa.map((g) => [g.godzina, liczba(g.zmotoryzowany), procent(g.udzialZmot), liczba(g.niezmotoryzowany), procent(g.udzialNiezmot)]),
    [false, true, true, true, true],
    [12, 25, 21, 21, 21],
  ));
  dzieci.push(podpisKursywa(`Tabela ${nrT6}. Rozkład godzinowy ruchu - Punkt ${punkt.numer}.`));
  dzieci.push(akapit(
    "Pełny rozkład godzinowy ruchu w podziale na relacje dostępny jest wyłącznie w załączonym pliku "
    + `wynik_tabele_Punkt${punkt.numer}_${punkt.id}.xlsx.`,
    { italic: true },
  ));
  if (o.niezmotGodzinowoEstymowane) {
    dzieci.push(akapit(
      "Arkusz godzinowy dla tego punktu nie rejestruje ruchu nie zmotoryzowanego w rozbiciu godzinowym "
      + "(dostępna jest wyłącznie suma dobowa). Powyższy rozkład godzinowy jest oszacowany proporcjonalnie "
      + "do godzinowego profilu ruchu zmotoryzowanego tego samego punktu.",
      { italic: true },
    ));
  }
  dzieci.push(obrazek(sciezka(punkt.assets.profilKategorie.plik)));
  dzieci.push(podpisKursywa(`Rysunek ${nrR10}. Rozkład godzinowy ruchu wg kategorii z udziałem dobowym - ${punkt.nazwa}.`));

  // --- 3.n.6 Rozkład dobowy i pory ruchu ----------------------------------
  dodajPodrozdzial("Rozkład dobowy i pory ruchu");

  const nrT7 = liczniki.nastepnaTabela();
  dzieci.push(akapit(`Tabela ${nrT7} przedstawia ruch według pór doby.`));
  const sumaPor = o.poryDoby.dzien[0] + o.poryDoby.noc[0];
  dzieci.push(tabela(
    ["Pora", "Zakres godzin", "Suma [poj.]", "Udział [%]"],
    [
      ["Dzień", "06:00-22:00", liczba(o.poryDoby.dzien[0]), procent(o.poryDoby.dzien[1])],
      ["Noc", "22:00-06:00", liczba(o.poryDoby.noc[0]), procent(o.poryDoby.noc[1])],
      ["Suma", "-", liczba(sumaPor), procent(100.0)],
    ],
    [false, false, true, true],
    [20, 30, 25, 25],
  ));
  dzieci.push(podpisKursywa(`Tabela ${nrT7}. Ruch według pór doby - Punkt ${punkt.numer}.`));

  dodajRysunek("wykresPoryDoby",
    (nr) => `Rysunek ${nr} przedstawia udział pory dziennej i nocnej w ruchu.`,
    (nr) => `Rysunek ${nr}. Udział pory dziennej i nocnej w ruchu - ${punkt.nazwa}.`);

  dzieci.push(akapit(punkt.teksty.poryDoby));

  // --- 3.n.7 Struktura rodzajowa ruchu ------------------------------------
  dodajPodrozdzial("Struktura rodzajowa ruchu");
  dzieci.push(akapit(punkt.teksty.strukturaRodzajowa));

  const nrT8 = liczniki.nastepnaTabela();
  dzieci.push(akapit(`Tabela ${nrT8} przedstawia strukturę rodzajową ruchu.`));
  dzieci.push(tabela(
    ["Kategoria", "Suma [poj./dobę]", "Udział zmotoryzowane [%]", "Udział całe [%]"],
    [
      ...o.strukturaRodzajowa.map((k) => [
        k.kategoria, liczba(k.suma),
        k.udzialZmotoryzowane === null ? "-" : procent(k.udzialZmotoryzowane),
        procent(k.udzialCale),
      ]),
      ["Suma", liczba(o.strukturaRodzajowaSumaCala), "-", procent(100.0)],
    ],
    [false, true, true, true],
    [34, 22, 22, 22],
  ));
  dzieci.push(podpisKursywa(`Tabela ${nrT8}. Struktura rodzajowa ruchu - Punkt ${punkt.numer}.`));
  dzieci.push(akapit(
    `Suma kategorii (${liczba(o.strukturaRodzajowaSumaCala)} poj./dobę) jest wyższa niż SDR `
    + `(${liczba(o.sdr)} poj./dobę), ponieważ SDR nie uwzględnia ruchu nie zmotoryzowanego.`,
    { italic: true },
  ));
  dzieci.push(akapit(
    "Pełna godzinowa struktura rodzajowa ruchu dostępna jest wyłącznie w załączonym pliku xlsx "
    + "(nie prezentowana w treści raportu ze względu na objętość).",
    { italic: true },
  ));

  // --- 3.n.8 Komentarz analityczny ----------------------------------------
  dodajPodrozdzial("Komentarz analityczny");
  dzieci.push(akapit(punkt.teksty.komentarzAnalityczny));

  return {
    children: dzieci,
    liczbaRysunkow: liczniki.r,
    liczbaTabel: liczniki.t,
    liczbaPodrozdzialow,
  };
}

module.exports = { budujPunkt };
