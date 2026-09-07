"use strict";

const {
  Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  ShadingType, HeadingLevel, ImageRun, LevelFormat, LevelSuffix, BorderStyle,
} = require("docx");
const fs = require("fs");
const sizeOf = require("./probaRozmiaru");

const FONT = "Calibri"; // Carlito jako metryczny zamiennik w wykresach PNG (matplotlib)
const ORANGE = "FF7900";
const GRAPHITE = "4A4A4A";

// A4 (11906 dxa) minus marginesy 2 cm z każdej strony (1134 dxa) — patrz
// test_budujPunkt.js properties.page. Tabele używają DXA (twipy), nie
// PERCENTAGE: docx.js zapisuje procent jako "100%" (z literalnym znakiem
// %), co jest niezgodne z OOXML (w:type="pct" wymaga liczby w
// pięćdziesiątych procenta, bez znaku %) — LibreOffice to toleruje, ale
// prawdziwy Word/Pages ignoruje taką wartość i zwija tabelę do wąskiej,
// domyślnej szerokości. DXA nie ma tej dwuznaczności.
const SZEROKOSC_TRESCI_DXA = 9638;
// 1 cm = 566,93 dxa (1440 dxa/cal, 2,54 cm/cal) — do wywołań obrazek() na
// pełną szerokość treści strony (np. wykres pogody, Rysunek 3.n.2).
const SZEROKOSC_TRESCI_CM = SZEROKOSC_TRESCI_DXA / 566.93;

// Numeracja rozdziałów jako prawdziwy multi-level list Worda (spięty ze
// stylami Heading1/2/3), a nie ręcznie wpisywany tekst — patrz naglowek()
// niżej. Word sam liczy "3.1", "3.2"... resetując poziom przy każdym nowym
// nadrzędnym numerze, więc kolejność rozdziałów/punktów można zmieniać bez
// przeliczania numerów w kodzie.
const NUMERACJA_REF = "naglowki-rozdzialow";
const POZIOM_NUMERACJI = {
  [HeadingLevel.HEADING_1]: 0,
  [HeadingLevel.HEADING_2]: 1,
  [HeadingLevel.HEADING_3]: 2,
};
const numeracjaRozdzialowConfig = [
  {
    reference: NUMERACJA_REF,
    levels: [
      { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.START, suffix: LevelSuffix.TAB },
      { level: 1, format: LevelFormat.DECIMAL, text: "%1.%2.", alignment: AlignmentType.START, suffix: LevelSuffix.TAB },
      { level: 2, format: LevelFormat.DECIMAL, text: "%1.%2.%3.", alignment: AlignmentType.START, suffix: LevelSuffix.TAB },
    ],
  },
];

function akapit(tekst, opcje = {}) {
  return new Paragraph({
    children: [new TextRun({ text: tekst, font: FONT, italics: opcje.italic, bold: opcje.bold })],
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 200 },
    ...opcje.paragraphProps,
  });
}

/**
 * Nagłówek rozdziału. Numerowany automatycznie przez Word (multi-level list
 * `numeracjaRozdzialowConfig`) domyślnie — przekaż `{ numerowany: false }`
 * dla nagłówków spoza numeracji (np. "Spis treści").
 */
function naglowek(tekst, poziom, opcje = {}) {
  return new Paragraph({
    text: tekst,
    heading: poziom,
    numbering: opcje.numerowany === false ? undefined : { reference: NUMERACJA_REF, level: POZIOM_NUMERACJI[poziom] },
    pageBreakBefore: opcje.pageBreakBefore,
  });
}

// Styl wg wytycznej: pomarańczowy, pogrubiony, 15pt, podkreślenie linią na
// całą szerokość treści strony (border paragrafu, nie text-underline —
// zakres wizualny musi sięgać marginesu, nie tylko końca tekstu).
// Ten sam rozmiar/kolor dla WSZYSTKICH poziomów (1., 1.1, 1.1.1) — bez
// tradycyjnej hierarchii malejących rozmiarów, zgodnie ze screenem wzorca.
function stylNaglowka() {
  return {
    run: { bold: true, color: ORANGE, size: 30, font: FONT },
    paragraph: {
      spacing: { before: 240, after: 160 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ORANGE, space: 4 } },
    },
  };
}

// docx.js dodaje wbudowane Heading1/2/3 zawsze przy `heading: HeadingLevel.X`
// — nadpisanie ich przez `styles.paragraphStyles` z tym samym id tworzy
// DRUGI wpis o tym samym styleId w styles.xml (nieprawidłowy OOXML, Word/
// LibreOffice bierze pierwszy = wbudowany niebieski). Właściwe miejsce na
// override to `styles.default.heading1/2/3`.
const styleNaglowkowDefault = {
  heading1: stylNaglowka(),
  heading2: stylNaglowka(),
  heading3: stylNaglowka(),
};

function komorkaNaglowkowa(tekst, szerokoscDxa) {
  return new TableCell({
    width: { size: szerokoscDxa, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, color: "auto", fill: ORANGE },
    children: [new Paragraph({
      children: [new TextRun({ text: tekst, font: FONT, bold: true, color: "FFFFFF" })],
    })],
  });
}

function komorka(tekst, wyrownanieDoPrawej, szerokoscDxa) {
  return new TableCell({
    width: { size: szerokoscDxa, type: WidthType.DXA },
    children: [new Paragraph({
      alignment: wyrownanieDoPrawej ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: [new TextRun({ text: String(tekst), font: FONT })],
    })],
  });
}

/**
 * Buduje tabelę o pełnej szerokości treści strony.
 * naglowki = string[], wiersze = string[][],
 * wyrownanieDoPrawej = bool[] (jeden na kolumnę, kolumny liczbowe = true),
 * szerokosciProcent = number[] (jeden na kolumnę, sumujące się do 100) —
 * domyślnie równy podział, gdy nie podano.
 * wierszDodatkowy = opcjonalny TableRow doklejany na końcu (np. wiersz ze
 * scalonymi kolumnami i rysunkiem — patrz wierszZObrazkiem()).
 */
function tabela(naglowki, wiersze, wyrownanieDoPrawej, szerokosciProcent, wierszDodatkowy) {
  const procenty = szerokosciProcent || naglowki.map(() => 100 / naglowki.length);
  const szerokosciDxa = procenty.map((p) => Math.round((SZEROKOSC_TRESCI_DXA * p) / 100));

  const wierszNaglowkowy = new TableRow({
    tableHeader: true,
    children: naglowki.map((n, i) => komorkaNaglowkowa(n, szerokosciDxa[i])),
  });
  const wierszeDanych = wiersze.map(
    (wiersz) => new TableRow({
      children: wiersz.map((wartosc, i) => komorka(wartosc, wyrownanieDoPrawej[i], szerokosciDxa[i])),
    }),
  );
  const wszystkieWiersze = [wierszNaglowkowy, ...wierszeDanych];
  if (wierszDodatkowy) wszystkieWiersze.push(wierszDodatkowy);

  return new Table({
    width: { size: SZEROKOSC_TRESCI_DXA, type: WidthType.DXA },
    columnWidths: szerokosciDxa,
    rows: wszystkieWiersze,
  });
}

/**
 * Wiersz tabeli z JEDNĄ komórką o scalonych kolumnach (columnSpan), zawierającą
 * wycentrowany rysunek i (opcjonalnie) jego podpis kursywą pod spodem, w TEJ
 * SAMEJ komórce — np. mapka lokalizacji jako ostatni wiersz Tabeli 3.n.1,
 * tak jak w referencyjnym raporcie.
 */
function wierszZObrazkiem(sciezkaPliku, liczbaKolumn, podpis, szerokoscCm = 15) {
  const dzieciKomorki = [obrazek(sciezkaPliku, szerokoscCm)];
  if (podpis) {
    dzieciKomorki.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: podpis, font: FONT, italics: true, size: 18, color: GRAPHITE })],
    }));
  }
  return new TableRow({
    children: [new TableCell({
      columnSpan: liczbaKolumn,
      width: { size: SZEROKOSC_TRESCI_DXA, type: WidthType.DXA },
      children: dzieciKomorki,
    })],
  });
}

function podpisKursywa(tekst) {
  return new Paragraph({
    children: [new TextRun({ text: tekst, font: FONT, italics: true, size: 18, color: GRAPHITE })],
    spacing: { after: 300 },
  });
}

function obrazek(sciezkaPliku, szerokoscCm = 13) {
  const bufor = fs.readFileSync(sciezkaPliku);
  const { width, height } = sizeOf(sciezkaPliku);
  const szerokoscEmu = szerokoscCm * 360000;
  const wysokoscEmu = szerokoscEmu * (height / width);
  return new Paragraph({
    children: [new ImageRun({
      data: bufor,
      transformation: { width: szerokoscEmu / 9525, height: wysokoscEmu / 9525 },
      type: "png",
    })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 100 },
  });
}

module.exports = {
  FONT, ORANGE, GRAPHITE, SZEROKOSC_TRESCI_DXA, SZEROKOSC_TRESCI_CM, numeracjaRozdzialowConfig, styleNaglowkowDefault,
  akapit, naglowek, tabela, podpisKursywa, obrazek, wierszZObrazkiem, HeadingLevel,
};
