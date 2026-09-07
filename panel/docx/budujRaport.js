"use strict";

const fs = require("fs");
const path = require("path");
const {
  Paragraph, TextRun, TableOfContents, HeadingLevel, AlignmentType,
  PageBreak, ImageRun, BorderStyle,
} = require("docx");
const { budujPunkt } = require("./budujPunkt");
const {
  akapit, naglowek, tabela, podpisKursywa, obrazek, FONT, GRAPHITE, ORANGE,
} = require("./style");
const sizeOf = require("./probaRozmiaru");
const { liczba } = require("./formatowanie");
const { odmianaPunktow, statystykiSdr, podzialTopIDol, segmentacjaWgTypu } = require("./analizaLaczna");

function punktOwyBullet(tekst) {
  return new Paragraph({
    children: [new TextRun({ text: `•  ${tekst}`, font: FONT })],
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 100 },
    indent: { left: 360 },
  });
}

// --- Strona tytułowa -------------------------------------------------------
function budujStronaTytulowa(projekt, logoSciezka) {
  const bufor = fs.readFileSync(logoSciezka);
  const { width, height } = sizeOf(logoSciezka);
  const w = 200; // px — transformation to piksele, NIE EMU (patrz branding.js::budujHeader)
  const h = w * (height / width);
  const m = projekt.metadaneProjektu;
  const miasta = [...new Set(projekt.punkty.map((p) => p.miejscowosc))].join(", ");

  return [
    new Paragraph({
      children: [new ImageRun({ data: bufor, transformation: { width: w, height: h }, type: "png" })],
      spacing: { after: 400 },
    }),
    new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 18, color: ORANGE } },
      spacing: { after: 400 },
      children: [],
    }),
    new Paragraph({
      children: [new TextRun({ text: "RAPORT Z POMIARU RUCHU DROGOWEGO", font: FONT, bold: true, size: 40 })],
      spacing: { after: 200 },
    }),
    new Paragraph({
      children: [new TextRun({ text: miasta, font: FONT, bold: true, color: ORANGE, size: 32 })],
      spacing: { after: 600 },
    }),
    ...[
      ["Zakres dat pomiaru:", m.dataOd === m.dataDo ? m.dataOd : `${m.dataOd} - ${m.dataDo}`],
      ["Zamawiający:", m.zamawiajacy],
      ["Wykonawca:", "Orange Polska S.A."],
      ["Data sporządzenia raportu:", m.dataSporzadzenia],
      ["Sporządził:", m.sporzadzil],
      ["Email osoby odpowiedzialnej:", m.emailOdpowiedzialny],
    ].map(([etykieta, wartosc]) => new Paragraph({
      spacing: { after: 100 },
      children: [
        new TextRun({ text: `${etykieta} `, font: FONT, bold: true }),
        new TextRun({ text: wartosc || "", font: FONT }),
      ],
    })),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// --- Spis treści -------------------------------------------------------
function budujSpisTresci() {
  return [
    naglowek("Spis treści", HeadingLevel.HEADING_1, { numerowany: false }),
    new TableOfContents("Spis treści", { hyperlink: true, headingStyleRange: "1-3" }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// --- 1. Cel i zakres opracowania -------------------------------------------
function budujCelIZakres(projekt) {
  const dzieci = [naglowek("Cel i zakres opracowania", HeadingLevel.HEADING_1)];
  dzieci.push(akapit(
    "Celem opracowania jest przedstawienie wyników pomiaru natężenia i struktury rodzajowej ruchu "
    + `drogowego, w sposób uporządkowany, jednoznaczny i porównywalny między punktami. Dla ${projekt.punkty.length} `
    + "punktów obserwacyjnych. Raport dokumentuje wyniki pomiarów dla wskazanych punktów obserwacji, "
    + "przedstawia natężenia i strukturę rodzajową ruchu drogowego.",
  ));
  dzieci.push(akapit(`Przygotowany na zlecenie ${projekt.metadaneProjektu.zamawiajacy}.`));
  const m = projekt.metadaneProjektu;
  dzieci.push(akapit(
    `Zakres czasowy pomiaru obejmuje okres od ${m.dataOd} do ${m.dataDo}, przy czym szczegóły dotyczące `
    + "czasu pomiaru i warunków jego realizacji zamieszczono w metryce każdego z punktów obserwacji.",
  ));
  const dni = new Set(projekt.punkty.map((p) => p.metadanePomiaru.dzienTygodnia));
  if (dni.size > 1) {
    dzieci.push(akapit(
      "Uwaga dotycząca porównywalności: pomiary poszczególnych punktów zostały wykonane w różnych dniach "
      + "tygodnia, co należy uwzględnić przy porównywaniu wyników między punktami.",
      { italic: true },
    ));
  }
  return dzieci;
}

// --- 2. Metodologia (treść stała, ta sama dla każdego projektu) -----------
function budujMetodologia(projekt) {
  return [
    naglowek("Metodologia", HeadingLevel.HEADING_1),
    akapit(
      "Pomiar wykonano metodą rejestracji wideo z automatyczną klasyfikacją pojazdów. Dane źródłowe "
      + "przetworzono w narzędziu analitycznym AISP, a następnie zagregowano do zestawień godzinowych "
      + "i kierunkowych zgodnie z wewnętrznym standardem przetwarzania.",
    ),
    akapit(
      "Kategoryzacja pojazdów wykonano zgodnie z wytycznymi GDDKiA: "
      + `${projekt.metadaneProjektu.linkWytyczneGDDKiA}, obejmuje 12 kategorii: `
      + "pojazdy osobowe, dostawcze, ciężarowe, ciężarowe z naczepami, autobusy, mikrobusy, pojazdy "
      + "rolnicze, motocykle, rowery, hulajnogi, pieszych oraz pieszych ze szczególnymi potrzebami. "
      + "SDR (średni dobowy ruch) liczony jest jako suma kategorii mechanicznych (bez pieszych, rowerów "
      + "i hulajnóg), natomiast udziały procentowe w strukturze rodzajowej liczone są względem sumy "
      + "wszystkich kategorii łącznie z ruchem nie zmotoryzowanym.",
    ),
    akapit(
      "Interwały czasowe: dane prezentowane są w rozbiciu godzinowym (00-23) oraz w dwóch porach doby - "
      + "dziennej (06:00-22:00) i nocnej (22:00-06:00). Szczyty godzinowe identyfikowane są dla dwóch "
      + "stałych okien, jednolitych dla wszystkich punktów pomiarowych projektu: porannego (7:00-8:00) "
      + "i popołudniowego (15:00-16:00), a nie dla lokalnych maksimów poszczególnych skrzyżowań - dzięki "
      + "temu diagramy przepływów poszczególnych punktów są wzajemnie porównywalne.",
    ),
    akapit(
      "Numeracja wlotów i nazewnictwo relacji: każdy wlot oznaczono skrótem kierunku geograficznego "
      + "(WSCH, ZACH, PN, PD), a manewry opisano jako wprost, w prawo, w lewo lub zawracający. W tabelach "
      + "relacji wiersze porządkuje się wg wlotów w kolejności zegarowej PN, WSCH, PD, ZACH, a w obrębie "
      + "wlotu - wg manewrów w kolejności: w prawo, na wprost, w lewo, zawracający.",
    ),
    naglowek("Wyniki pomiarów w punktach pomiarowych", HeadingLevel.HEADING_1),
    akapit(
      "Poniższe podrozdziały prezentują szczegółowe wyniki pomiaru dla każdego z punktów pomiarowych, w "
      + "jednolitym układzie: lokalizacja i karta skrzyżowania, diagramy przepływów ruchu, ruch według "
      + "kierunków i relacji, rozkład godzinowy i pory ruchu, struktura rodzajowa oraz komentarz analityczny.",
    ),
  ];
}

// --- 4. Podsumowanie ---------------------------------------------------

function budujPodsumowanie(projekt, baseDir) {
  const N = projekt.punkty.length;

  // Analiza łączna (porównawcza) nie ma zastosowania przy jednym punkcie —
  // nie ma z czym go porównać. Cały rozdział znika (nie tylko jego treść) —
  // dzięki automatycznej numeracji Worda "Literatura" staje się wtedy
  // rozdziałem 4 zamiast 5, bez żadnych ręcznych przeliczeń numeracji.
  if (N === 1) return [];

  const dzieci = [naglowek("Podsumowanie", HeadingLevel.HEADING_1)];
  const prog = projekt.metadaneProjektu.progAnalizyLacznej || 15;

  dzieci.push(akapit(
    `Niniejszy rozdział podsumowuje wyniki pomiaru dla wszystkich ${N} punktów objętych projektem. `
    + "Ze względu na różnice w dniach pomiaru między punktami (o ile wystąpiły - patrz rozdział 1), "
    + "porównania należy interpretować z ostrożnością.",
  ));
  const tekstWprowadzenie = projekt.podsumowanie && projekt.podsumowanie.teksty && projekt.podsumowanie.teksty.tekstWprowadzenie;
  const tekstPorownanie = projekt.podsumowanie && projekt.podsumowanie.teksty && projekt.podsumowanie.teksty.tekstPorownanie;
  if (tekstWprowadzenie) dzieci.push(akapit(tekstWprowadzenie));
  if (tekstPorownanie) dzieci.push(akapit(tekstPorownanie));

  if (N <= prog) {
    // --- Tryb pełny -------------------------------------------------
    dzieci.push(naglowek("Zestawienie zbiorcze punktów pomiarowych", HeadingLevel.HEADING_2));
    dzieci.push(tabela(
      ["ID", "Nazwa punktu", "Zakres pomiaru", "SDR [poj./dobę]", "Szczyt dobowy"],
      projekt.punkty.map((p) => [
        p.id, p.nazwa, p.metadanePomiaru.dataPomiaru,
        liczba(p.obliczenia.sdr),
        `${liczba(p.obliczenia.szczytDobowy.wartosc)} poj./h o ${p.obliczenia.szczytDobowy.godzina}`,
      ]),
      [false, false, false, true, true],
      [10, 30, 20, 20, 20],
    ));
    dzieci.push(podpisKursywa("Tabela 4.1. Zestawienie zbiorcze punktów pomiarowych."));
    dzieci.push(akapit(
      "Powyższa tabela zestawia podstawowe parametry ruchu dla wszystkich punktów projektu. Rysunek 4.1 "
      + "przedstawia porównanie SDR w formie graficznej.",
    ));
    dzieci.push(obrazek(path.resolve(baseDir, "assets/r_zestawienie_sdr.png")));
    dzieci.push(podpisKursywa("Rysunek 4.1. Porównanie SDR punktów pomiarowych."));

    dzieci.push(naglowek("Struktura rodzajowa i szczyty godzinowe w skali projektu", HeadingLevel.HEADING_2));
    const kategorie = projekt.punkty[0].obliczenia.strukturaRodzajowa.map((k) => k.kategoria);
    dzieci.push(tabela(
      ["Kategoria", ...projekt.punkty.map((p) => p.id)],
      kategorie.map((kat, i) => [
        kat === "Piesi" ? "Środki transportu publicznego" : kat,
        ...projekt.punkty.map((p) => {
          const w = p.obliczenia.strukturaRodzajowa[i];
          return w.udzialCale === null ? "-" : `${w.udzialCale.toFixed(1).replace(".", ",")}%`;
        }),
      ]),
      [false, ...projekt.punkty.map(() => true)],
      [40, ...projekt.punkty.map(() => 60 / projekt.punkty.length)],
    ));
    dzieci.push(podpisKursywa("Tabela 4.2. Struktura rodzajowa ruchu w skali projektu [%]."));
    dzieci.push(akapit(
      "Wszystkie punkty projektu współdzielą te same, stałe okna szczytu (7:00-8:00 i 15:00-16:00), co "
      + "zapewnia ich porównywalność. Rysunek 4.2 przedstawia natężenie w tych oknach dla każdego punktu.",
    ));
    dzieci.push(obrazek(path.resolve(baseDir, "assets/r_szczyty_projektu.png")));
    dzieci.push(podpisKursywa("Rysunek 4.2. Natężenie ruchu w stałych oknach szczytu wg punktów pomiarowych."));
  } else {
    // --- Tryb zagregowany (N > próg) ---------------------------------
    // Tabela 1:1 na punkt i tabela 1 kolumna/punkt (jak w trybie pełnym)
    // przestają się mieścić na stronie i tracą czytelność przy dużym N —
    // zamiast tego: statystyki opisowe, ekstrema (Top/Dół), histogram
    // rozkładu SDR i segmentacja wg typu punktu pomiarowego.
    const stat = statystykiSdr(projekt.punkty);
    dzieci.push(akapit(
      `Ze względu na liczbę punktów pomiarowych (${N}), przekraczającą przyjęty próg analizy szczegółowej `
      + `(${prog}), poniższe zestawienie ma charakter zagregowany. Średni dobowy ruch (SDR) w projekcie `
      + `waha się od ${liczba(stat.min)} do ${liczba(stat.max)} poj./dobę, przy średniej ${liczba(stat.srednia)} `
      + `poj./dobę i medianie ${liczba(stat.mediana)} poj./dobę.`,
    ));

    const ile = Math.max(1, Math.min(10, Math.floor(N / 2)));
    const { top, dol } = podzialTopIDol(projekt.punkty, ile);
    const sl = odmianaPunktow(ile);
    dzieci.push(naglowek("Punkty o najwyższym i najniższym natężeniu ruchu", HeadingLevel.HEADING_2));
    dzieci.push(akapit(`Tabela 4.1 przedstawia ${ile} ${sl} o najwyższym SDR w projekcie.`));
    dzieci.push(tabela(
      ["ID", "Nazwa punktu", "SDR [poj./dobę]"],
      top.map((p) => [p.id, p.nazwa, liczba(p.obliczenia.sdr)]),
      [false, false, true],
      [15, 55, 30],
    ));
    dzieci.push(podpisKursywa(`Tabela 4.1. ${ile} ${sl} o najwyższym SDR w projekcie.`));
    dzieci.push(akapit(`Tabela 4.2 przedstawia ${ile} ${sl} o najniższym SDR w projekcie.`));
    dzieci.push(tabela(
      ["ID", "Nazwa punktu", "SDR [poj./dobę]"],
      dol.map((p) => [p.id, p.nazwa, liczba(p.obliczenia.sdr)]),
      [false, false, true],
      [15, 55, 30],
    ));
    dzieci.push(podpisKursywa(`Tabela 4.2. ${ile} ${sl} o najniższym SDR w projekcie.`));

    dzieci.push(akapit(`Rysunek 4.1 przedstawia rozkład SDR wszystkich ${N} punktów projektu.`));
    dzieci.push(obrazek(path.resolve(baseDir, "assets/r_histogram_sdr.png")));
    dzieci.push(podpisKursywa("Rysunek 4.1. Rozkład SDR punktów pomiarowych projektu."));

    const segmenty = segmentacjaWgTypu(projekt.punkty);
    if (segmenty.length > 1) {
      dzieci.push(naglowek("Segmentacja wg typu punktu pomiarowego", HeadingLevel.HEADING_2));
      dzieci.push(akapit("Tabela 4.3 przedstawia zestawienie natężenia ruchu w podziale na typ punktu pomiarowego."));
      dzieci.push(tabela(
        ["Typ punktu", "Liczba punktów", "Suma SDR [poj./dobę]", "Średni SDR [poj./dobę]"],
        segmenty.map((s) => [s.typ, String(s.liczba), liczba(s.sumaSdr), liczba(s.sredniSdr)]),
        [false, true, true, true],
        [40, 20, 20, 20],
      ));
      dzieci.push(podpisKursywa("Tabela 4.3. Zestawienie natężenia ruchu wg typu punktu pomiarowego."));
    }
  }

  const tekstWnioski = projekt.podsumowanie && projekt.podsumowanie.teksty && projekt.podsumowanie.teksty.tekstWnioski;
  dzieci.push(naglowek("Wnioski i rekomendacje", HeadingLevel.HEADING_2));
  dzieci.push(akapit(tekstWnioski || "[SZKIC — do zastąpienia tekstem z Etapu 4/AI] Wnioski i rekomendacje dla przyszłych pomiarów."));

  return dzieci;
}

// --- 5. Literatura i spis załączników --------------------------------------
function budujLiteratura(projekt) {
  const dzieci = [naglowek("Literatura i spis załączników", HeadingLevel.HEADING_1)];
  dzieci.push(akapit(
    "Pomiar i kategoryzację pojazdów wykonano zgodnie z wytycznymi GDDKiA dostępnymi pod adresem: "
    + `${projekt.metadaneProjektu.linkWytyczneGDDKiA}.`,
  ));
  dzieci.push(akapit(
    "Poniższe pliki .xlsx stanowią nieodłączną część niniejszego raportu i zawierają pełne dane "
    + "źródłowe (w tym godzinową strukturę rodzajową ruchu) dla każdego punktu pomiarowego:",
  ));
  for (const p of projekt.punkty) {
    dzieci.push(punktOwyBullet(`wynik_tabele_Punkt${p.numer}_${p.id}.xlsx`));
  }
  return dzieci;
}

/**
 * Buduje pełną treść dokumentu (bez Document/sections/headers/footers —
 * to zostaje w warstwie wywołującej, patrz test_budujRaport.js) na podstawie
 * całego `projekt.json` (metadaneProjektu + punkty[]).
 */
function budujPelnyDokument(projekt, logoSciezka, baseDir) {
  const dzieci = [];
  dzieci.push(...budujStronaTytulowa(projekt, logoSciezka));
  dzieci.push(...budujSpisTresci());
  dzieci.push(...budujCelIZakres(projekt));
  dzieci.push(...budujMetodologia(projekt));

  const liczbyPerPunkt = [];
  for (const punkt of projekt.punkty) {
    const wynik = budujPunkt(punkt, `3.${punkt.numer}`, baseDir);
    dzieci.push(...wynik.children);
    liczbyPerPunkt.push({
      id: punkt.id, liczbaTabel: wynik.liczbaTabel, liczbaRysunkow: wynik.liczbaRysunkow,
    });
  }

  dzieci.push(...budujPodsumowanie(projekt, baseDir));
  dzieci.push(...budujLiteratura(projekt));

  return { children: dzieci, liczbyPerPunkt };
}

module.exports = { budujPelnyDokument };
