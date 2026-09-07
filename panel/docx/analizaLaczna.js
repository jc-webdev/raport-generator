"use strict";

/**
 * Statystyki porównawcze między punktami projektu (rozdział 4 "Podsumowanie")
 * + regułowe (bez AI) teksty krok 10 — współdzielone między budujRaport.js
 * (budowa docx) i server.js (przycisk "Wygeneruj" w kroku 10 UI, czysty JS,
 * bez potrzeby wołania Pythona jak w kroku 9).
 */

const { liczba } = require("./formatowanie");

const TYP_ETYKIETA = {
  skrzyzowanie: "Skrzyżowanie", rondo: "Rondo", tranzyt: "Tranzyt", rejestracja: "Rejestracja",
};

function odmianaPunktow(n) {
  if (n === 1) return "punkt";
  const ostatniaCyfra = n % 10;
  const ostatnieDwieCyfry = n % 100;
  if ([2, 3, 4].includes(ostatniaCyfra) && ![12, 13, 14].includes(ostatnieDwieCyfry)) return "punkty";
  return "punktów";
}

function statystykiSdr(punkty) {
  const wartosci = punkty.map((p) => p.obliczenia.sdr).sort((a, b) => a - b);
  const n = wartosci.length;
  const suma = wartosci.reduce((a, b) => a + b, 0);
  const mediana = n % 2 === 1 ? wartosci[(n - 1) / 2] : (wartosci[n / 2 - 1] + wartosci[n / 2]) / 2;
  return { min: wartosci[0], max: wartosci[n - 1], srednia: suma / n, mediana };
}

function podzialTopIDol(punkty, ile) {
  const posortowane = [...punkty].sort((a, b) => b.obliczenia.sdr - a.obliczenia.sdr);
  return { top: posortowane.slice(0, ile), dol: posortowane.slice(-ile).reverse() };
}

function segmentacjaWgTypu(punkty) {
  const mapa = new Map();
  for (const p of punkty) {
    const typ = p.typ || "nieokreślony";
    if (!mapa.has(typ)) mapa.set(typ, []);
    mapa.get(typ).push(p.obliczenia.sdr);
  }
  return [...mapa.entries()]
    .map(([typ, sdry]) => ({
      typ: TYP_ETYKIETA[typ] || typ,
      liczba: sdry.length,
      sumaSdr: sdry.reduce((a, b) => a + b, 0),
      sredniSdr: sdry.reduce((a, b) => a + b, 0) / sdry.length,
    }))
    .sort((a, b) => b.sumaSdr - a.sumaSdr);
}

function generujTekstWprowadzenie(projekt) {
  const m = projekt.metadaneProjektu;
  const N = projekt.punkty.length;
  const miasta = [...new Set(projekt.punkty.map((p) => p.miejscowosc).filter(Boolean))];
  const zakres = m.dataOd && m.dataDo
    ? (m.dataOd === m.dataDo ? m.dataOd : `${m.dataOd} - ${m.dataDo}`)
    : null;

  // "dla" wymusza dopełniacz niezależnie od liczby (w przeciwieństwie do
  // dopełnienia bez przyimka, gdzie 2-4 rządzi inną formą niż 5+) — pozwala
  // uniknąć odmiany rzeczownika+przymiotnika przez liczebnik w tym zdaniu.
  let tekst = `Poniższe zestawienie porównawcze obejmuje wyniki dla ${N} punktów pomiarowych `
    + `zrealizowanych na zlecenie ${m.zamawiajacy || "[NAZWA ZAMAWIAJĄCEGO]"}`;
  if (miasta.length > 0) tekst += `, zlokalizowanych w: ${miasta.join(", ")}`;
  if (zakres) tekst += `, w okresie ${zakres}`;
  tekst += ".";
  return tekst;
}

function generujTekstPorownanie(projekt) {
  const stat = statystykiSdr(projekt.punkty);
  const { top, dol } = podzialTopIDol(projekt.punkty, 1);
  const najwyzszy = top[0];
  const najnizszy = dol[0];
  const krotnosc = najnizszy.obliczenia.sdr ? najwyzszy.obliczenia.sdr / najnizszy.obliczenia.sdr : null;

  let tekst = `Najwyższe natężenie ruchu (SDR) odnotowano w punkcie ${najwyzszy.id} - ${najwyzszy.nazwa} `
    + `(${liczba(najwyzszy.obliczenia.sdr)} poj./dobę), a najniższe w punkcie ${najnizszy.id} - ${najnizszy.nazwa} `
    + `(${liczba(najnizszy.obliczenia.sdr)} poj./dobę)`
    + (krotnosc && krotnosc > 1.05 ? `, co stanowi różnicę ok. ${krotnosc.toFixed(1).replace(".", ",")}x` : "")
    + `. Średni SDR w projekcie wynosi ${liczba(stat.srednia)} poj./dobę, przy medianie ${liczba(stat.mediana)} poj./dobę.`;

  const segmenty = segmentacjaWgTypu(projekt.punkty);
  if (segmenty.length > 1) {
    const dominujacy = segmenty[0];
    tekst += ` Pod względem typu punktu pomiarowego dominują ${dominujacy.typ.toLowerCase()} `
      + `(${dominujacy.liczba} z ${projekt.punkty.length}), generujące łącznie ${liczba(dominujacy.sumaSdr)} poj./dobę.`;
  }
  return tekst;
}

module.exports = {
  odmianaPunktow, statystykiSdr, podzialTopIDol, segmentacjaWgTypu,
  generujTekstWprowadzenie, generujTekstPorownanie,
};
