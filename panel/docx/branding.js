"use strict";

/**
 * Nagłówek/stopka brandowane Orange — wspólne dla test_budujRaport.js i
 * generuj_docx.js (Etap 4 krok 11), żeby nie duplikować logiki w dwóch
 * miejscach.
 */

const { Header, Footer, Paragraph, TextRun, ImageRun, AlignmentType, PageNumber, BorderStyle } = require("docx");
const fs = require("fs");
const { FONT, GRAPHITE, ORANGE } = require("./style");
const sizeOf = require("./probaRozmiaru");

function budujHeader(logoSciezka, miasta) {
  const bufor = fs.readFileSync(logoSciezka);
  const { width, height } = sizeOf(logoSciezka);
  // Mniejsze niż poprzednio (60) — mniej wysokości nagłówka = więcej realnego
  // zapasu przed treścią strony (patrz margin.header w generuj_docx.js).
  const w = 42;
  const h = w * (height / width);
  return new Header({
    children: [new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: ORANGE } },
      children: [
        new ImageRun({ data: bufor, transformation: { width: w, height: h }, type: "png" }),
        new TextRun({ text: `   Raport z pomiaru ruchu drogowego — ${miasta}`, font: FONT, size: 18, color: GRAPHITE }),
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

function pustyHeader() {
  return new Header({ children: [new Paragraph({ children: [] })] });
}

function pustyFooter() {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Orange Restricted", font: FONT, size: 16, color: GRAPHITE })],
    })],
  });
}

module.exports = { budujHeader, budujFooter, pustyHeader, pustyFooter };
