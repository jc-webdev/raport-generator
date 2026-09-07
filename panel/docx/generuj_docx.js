"use strict";

/**
 * CLI: buduje finalny raport .docx z fixture (kształt gotowy do
 * budujRaport.js — patrz panel/ui/server.js::zbudujFixtureDlaDocx, Etap 4
 * krok 11). Odpowiednik test_budujRaport.js, ale bez asercji testowych —
 * do faktycznej generacji, nie do developmentu Etapu 3.
 *
 * Użycie: node generuj_docx.js <fixture.json> <output.docx> <logo.png> <baseDir>
 * `baseDir` — katalog względem którego rozwiązywane są ścieżki `assets.*.plik`
 * w fixture (NIE musi być katalogiem fixture — patrz budujPunkt.js `sciezka()`).
 */

const fs = require("fs");
const path = require("path");
const { Document, Packer } = require("docx");
const { budujPelnyDokument } = require("./budujRaport");
const { FONT, numeracjaRozdzialowConfig, styleNaglowkowDefault } = require("./style");
const { budujHeader, budujFooter, pustyHeader, pustyFooter } = require("./branding");

async function main() {
  const [, , sciezkaFixture, sciezkaWyjsciowa, sciezkaLogo, baseDirArg] = process.argv;
  if (!sciezkaFixture || !sciezkaWyjsciowa || !sciezkaLogo) {
    console.error("Użycie: node generuj_docx.js <fixture.json> <output.docx> <logo.png> [baseDir]");
    process.exit(1);
  }

  const projekt = JSON.parse(fs.readFileSync(sciezkaFixture, "utf-8"));
  const baseDir = baseDirArg || path.dirname(sciezkaFixture);
  const miasta = [...new Set(projekt.punkty.map((p) => p.miejscowosc))].join(", ");
  console.error("[generuj_docx] buduję drzewo dokumentu (czyta obrazki z dysku)...");
  const wynik = budujPelnyDokument(projekt, sciezkaLogo, baseDir);
  console.error("[generuj_docx] drzewo gotowe, pakuję do .docx (XML + zip)...");

  const doc = new Document({
    numbering: { config: numeracjaRozdzialowConfig },
    sections: [{
      properties: {
        titlePage: true,
        page: {
          size: { width: 11906, height: 16838 },
          // header: 150 (nie domyślne 708) — przy margin.top=1134 zostawia
          // realny odstęp między pomarańczową linią nagłówka a treścią strony.
          // WAŻNE: LibreOffice i MS Word różnie liczą pozycjonowanie treści
          // nagłówka względem tej wartości — w LibreOffice nawet 400 dawało
          // widoczny odstęp, w prawdziwym Wordzie było to nadal za mało.
          // Zejście niżej (150) + mniejsze logo w nagłówku (branding.js) to
          // bufor bezpieczeństwa na tę rozbieżność między silnikami.
          margin: { top: 1134, bottom: 1134, left: 1134, right: 1134, header: 150 },
        },
      },
      headers: { first: pustyHeader(), default: budujHeader(sciezkaLogo, miasta) },
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

  const buffer = await Packer.toBuffer(doc);
  console.error("[generuj_docx] spakowane, zapisuję na dysk...");
  fs.mkdirSync(path.dirname(sciezkaWyjsciowa), { recursive: true });
  fs.writeFileSync(sciezkaWyjsciowa, buffer);
  console.log(JSON.stringify({ ok: true, sciezka: sciezkaWyjsciowa, liczbaPunktow: wynik.liczbyPerPunkt.length }));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
