"use strict";

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const JSZip = require("jszip");
const { Document, Packer } = require("docx");
const { budujPelnyDokument } = require("./budujRaport");
const { FONT, numeracjaRozdzialowConfig, styleNaglowkowDefault } = require("./style");
const { budujHeader, budujFooter, pustyHeader, pustyFooter } = require("./branding");

const DANE_DIR = path.join(__dirname, "dane_testowe");
const OUT_DIR = path.join(__dirname, "output");
const LOGO = path.join(__dirname, "assets", "logo.png");

function wczytajProjekt() {
  // Argument CLI opcjonalny: nazwa pliku fixture w dane_testowe/ (domyślnie
  // projekt_fixture.json, N=1 punkt) — np. `node test_budujRaport.js
  // projekt_fixture_3punkty.json` do testu pętli po wielu punktach.
  const nazwaPliku = process.argv[2] || "projekt_fixture.json";
  return JSON.parse(fs.readFileSync(path.join(DANE_DIR, nazwaPliku), "utf-8"));
}

/**
 * Rozpakowuje wygenerowany .docx i sprawdza, że numery "Tabela X.Y" /
 * "Rysunek X.Y" w podpisach (przechwycone wprost z finalnego XML, nie z
 * kodu JS) nigdzie się nie powtarzają w całym dokumencie.
 */
async function sprawdzUnikalnoscNumeracji(buffer) {
  const zip = await JSZip.loadAsync(buffer);
  const xml = await zip.file("word/document.xml").async("string");
  const tekst = xml.replace(/<[^>]+>/g, "");
  const dopasowania = [...tekst.matchAll(/(Tabela|Rysunek) (\d+(?:\.\d+){1,2})\.\s/g)];
  assert.ok(dopasowania.length > 0, "nie znaleziono żadnych podpisów Tabela/Rysunek w dokumencie");

  const widziane = new Map();
  for (const [, rodzaj, numer] of dopasowania) {
    const klucz = `${rodzaj} ${numer}`;
    widziane.set(klucz, (widziane.get(klucz) || 0) + 1);
  }
  const duplikaty = [...widziane.entries()].filter(([, n]) => n > 1);
  assert.strictEqual(duplikaty.length, 0, `zduplikowana numeracja: ${duplikaty.map(([k, n]) => `${k} (x${n})`).join(", ")}`);
  console.log(`OK: ${dopasowania.length} podpisów Tabela/Rysunek, wszystkie numery unikalne`);
}

async function main() {
  const projekt = wczytajProjekt();
  const miasta = [...new Set(projekt.punkty.map((p) => p.miejscowosc))].join(", ");
  const wynik = budujPelnyDokument(projekt, LOGO, __dirname);

  // --- Asercje strukturalne -------------------------------------------
  assert.strictEqual(wynik.liczbyPerPunkt.length, projekt.punkty.length, "liczba bloków punktów musi zgadzać się z projekt.punkty");
  for (const w of wynik.liczbyPerPunkt) {
    assert.strictEqual(w.liczbaTabel, 8, `Punkt ${w.id}: oczekiwano 8 tabel, jest ${w.liczbaTabel}`);
    assert.strictEqual(w.liczbaRysunkow, 12, `Punkt ${w.id}: oczekiwano 12 rysunków, jest ${w.liczbaRysunkow}`);
  }
  console.log(`OK: ${wynik.liczbyPerPunkt.length} punkt(y), każdy z 8 tabelami i 12 rysunkami`);

  const doc = new Document({
    numbering: { config: numeracjaRozdzialowConfig },
    sections: [{
      properties: {
        titlePage: true, // strona tytułowa bez brandowanego nagłówka/stopki
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1134, bottom: 1134, left: 1134, right: 1134, header: 150 },
        },
      },
      headers: { first: pustyHeader(), default: budujHeader(LOGO, miasta) },
      footers: { first: pustyFooter(), default: budujFooter() },
      children: wynik.children,
    }],
    styles: {
      default: {
        document: { run: { font: FONT, size: 22 } },
        ...styleNaglowkowDefault,
      },
    },
  });

  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
  const buffer = await Packer.toBuffer(doc);
  const znacznikCzasu = new Date().toISOString().replace(/[:.]/g, "-");
  const outPath = path.join(OUT_DIR, `raport_pelny_${znacznikCzasu}.docx`);
  fs.writeFileSync(path.join(OUT_DIR, "raport_pelny.docx"), buffer);
  fs.writeFileSync(outPath, buffer);
  console.log(`OK: zapisano ${outPath} (${(buffer.length / 1024).toFixed(0)} KB)`);

  await sprawdzUnikalnoscNumeracji(buffer);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
