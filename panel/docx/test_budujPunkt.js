"use strict";

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const {
  Document, Packer, Header, Footer, Paragraph, TextRun, ImageRun,
  AlignmentType, PageNumber, BorderStyle,
} = require("docx");
const { budujPunkt } = require("./budujPunkt");
const { FONT, GRAPHITE, ORANGE, numeracjaRozdzialowConfig } = require("./style");
const sizeOf = require("./probaRozmiaru");

const DANE_DIR = path.join(__dirname, "dane_testowe");
const OUT_DIR = path.join(__dirname, "output");

function wczytajFixture() {
  const surowe = fs.readFileSync(path.join(DANE_DIR, "punkt2_fixture.json"), "utf-8");
  return JSON.parse(surowe);
}

function budujHeader(logoSciezka) {
  const bufor = fs.readFileSync(logoSciezka);
  const { width, height } = sizeOf(logoSciezka);
  const w = 60; // px w nagłówku
  const h = w * (height / width);
  return new Header({
    children: [new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: ORANGE } },
      children: [
        new ImageRun({ data: bufor, transformation: { width: w, height: h }, type: "png" }),
        new TextRun({ text: "   Raport z pomiaru ruchu drogowego — Toruń", font: FONT, size: 18, color: GRAPHITE }),
      ],
    })],
  });
}

function budujFooter() {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({ text: "Orange Restricted   ", font: FONT, size: 16, color: GRAPHITE }),
        new TextRun({ text: "Strona ", font: FONT, size: 16 }),
        new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16 }),
        new TextRun({ text: " z ", font: FONT, size: 16 }),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 16 }),
      ],
    })],
  });
}

async function main() {
  const punkt = wczytajFixture();
  const wynik = budujPunkt(punkt, "3.1", __dirname);

  // --- Asercje strukturalne -------------------------------------------
  assert.strictEqual(wynik.liczbaPodrozdzialow, 8, `Oczekiwano 8 podrozdziałów (3.n.1-3.n.8), jest ${wynik.liczbaPodrozdzialow}`);
  assert.strictEqual(wynik.liczbaTabel, 8, `Oczekiwano 8 tabel (T1-T8), jest ${wynik.liczbaTabel}`);
  assert.strictEqual(wynik.liczbaRysunkow, 12, `Oczekiwano 12 rysunków (R1-R12), jest ${wynik.liczbaRysunkow}`);
  console.log(`OK: liczniki -> tabele=${wynik.liczbaTabel}, rysunki=${wynik.liczbaRysunkow}`);

  const relacje = punkt.obliczenia.relacjeSDR.length;
  assert.strictEqual(punkt.obliczenia.relacjeCiezkie.length, relacje, "relacjeCiezkie musi mieć tyle samo wierszy co relacjeSDR");
  console.log(`OK: liczba relacji = ${relacje} (relacjeSDR i relacjeCiezkie zgodne)`);

  // --- Budowa dokumentu -------------------------------------------------
  const doc = new Document({
    numbering: { config: numeracjaRozdzialowConfig },
    sections: [{
      properties: {
        page: {
          // A4 (twips: 1cm = 566.929) — bez tego docx domyślnie używa
          // krótszego US Letter, co psuje kalkulację ile obrazków zmieści
          // się na stronie i dawało wielkie puste odstępy.
          size: { width: 11906, height: 16838 },
          margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 }, // 2 cm
        },
      },
      headers: { default: budujHeader(path.join(DANE_DIR, "..", "assets", "logo.png")) },
      footers: { default: budujFooter() },
      children: wynik.children,
    }],
    styles: {
      default: {
        document: { run: { font: FONT, size: 22 } },
      },
    },
  });

  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
  const buffer = await Packer.toBuffer(doc);
  // Datownik w nazwie — żeby jednoznacznie odróżnić od poprzednich wersji
  // pliku (wykluczyć podgląd zbuforowanej starej kopii w Wordzie/Pages).
  const znacznikCzasu = new Date().toISOString().replace(/[:.]/g, "-");
  const outPath = path.join(OUT_DIR, `test_punkt2_${znacznikCzasu}.docx`);
  fs.writeFileSync(path.join(OUT_DIR, "test_punkt2.docx"), buffer);
  fs.writeFileSync(outPath, buffer);
  console.log(`OK: zapisano ${outPath} (${(buffer.length / 1024).toFixed(0)} KB)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
