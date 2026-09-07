"use strict";

/**
 * Minimalny writer ZIP (metoda "stored", bez kompresji) — zero zależności
 * zewnętrznych, zgodnie z resztą server.js. Kompresja pominięta celowo:
 * pliki .docx/.xlsx to już skompresowane archiwa ZIP same w sobie, więc
 * dodatkowy deflate dałby znikome oszczędności kosztem złożoności (CRC32
 * liczone przez wbudowane w Node zlib.crc32, dostępne od Node 22).
 *
 * Użycie: budujZip([{ nazwa: "raport.docx", dane: Buffer }, ...]) -> Buffer
 */

const zlib = require("zlib");

function dosDataCzas(data) {
  const czas = ((data.getHours() & 0x1f) << 11) | ((data.getMinutes() & 0x3f) << 5) | ((data.getSeconds() >> 1) & 0x1f);
  const dzien = (((data.getFullYear() - 1980) & 0x7f) << 9) | (((data.getMonth() + 1) & 0xf) << 5) | (data.getDate() & 0x1f);
  return { czas, dzien };
}

function budujZip(pliki) {
  const { czas, dzien } = dosDataCzas(new Date());
  const lokalneWpisy = [];
  const centralneWpisy = [];
  let offset = 0;

  for (const { nazwa, dane } of pliki) {
    const nazwaBuf = Buffer.from(nazwa, "utf-8");
    const crc = zlib.crc32(dane);

    const lokalny = Buffer.alloc(30);
    lokalny.writeUInt32LE(0x04034b50, 0);
    lokalny.writeUInt16LE(20, 4); // wersja do rozpakowania
    lokalny.writeUInt16LE(0, 6); // flagi
    lokalny.writeUInt16LE(0, 8); // metoda: 0 = stored
    lokalny.writeUInt16LE(czas, 10);
    lokalny.writeUInt16LE(dzien, 12);
    lokalny.writeUInt32LE(crc, 14);
    lokalny.writeUInt32LE(dane.length, 18);
    lokalny.writeUInt32LE(dane.length, 22);
    lokalny.writeUInt16LE(nazwaBuf.length, 26);
    lokalny.writeUInt16LE(0, 28);

    lokalneWpisy.push(lokalny, nazwaBuf, dane);

    const centralny = Buffer.alloc(46);
    centralny.writeUInt32LE(0x02014b50, 0);
    centralny.writeUInt16LE(20, 4); // wersja utworzenia
    centralny.writeUInt16LE(20, 6); // wersja do rozpakowania
    centralny.writeUInt16LE(0, 8);
    centralny.writeUInt16LE(0, 10);
    centralny.writeUInt16LE(czas, 12);
    centralny.writeUInt16LE(dzien, 14);
    centralny.writeUInt32LE(crc, 16);
    centralny.writeUInt32LE(dane.length, 20);
    centralny.writeUInt32LE(dane.length, 24);
    centralny.writeUInt16LE(nazwaBuf.length, 28);
    centralny.writeUInt16LE(0, 30); // extra
    centralny.writeUInt16LE(0, 32); // komentarz
    centralny.writeUInt16LE(0, 34); // dysk startowy
    centralny.writeUInt16LE(0, 36); // atrybuty wewnętrzne
    centralny.writeUInt32LE(0, 38); // atrybuty zewnętrzne
    centralny.writeUInt32LE(offset, 42);

    centralneWpisy.push(centralny, nazwaBuf);

    offset += lokalny.length + nazwaBuf.length + dane.length;
  }

  const centralnyBufor = Buffer.concat(centralneWpisy);
  const koniec = Buffer.alloc(22);
  koniec.writeUInt32LE(0x06054b50, 0);
  koniec.writeUInt16LE(0, 4);
  koniec.writeUInt16LE(0, 6);
  koniec.writeUInt16LE(pliki.length, 8);
  koniec.writeUInt16LE(pliki.length, 10);
  koniec.writeUInt32LE(centralnyBufor.length, 12);
  koniec.writeUInt32LE(offset, 16);
  koniec.writeUInt16LE(0, 20);

  return Buffer.concat([...lokalneWpisy, centralnyBufor, koniec]);
}

module.exports = { budujZip };
