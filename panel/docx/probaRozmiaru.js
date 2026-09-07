"use strict";

const fs = require("fs");

// Minimalny odczyt szerokości/wysokości z nagłówka IHDR pliku PNG — bez
// dokładania zależności npm dla czegoś, co to 8 linii (bajty 16-24 pliku PNG).
function rozmiarPng(sciezka) {
  const bufor = Buffer.alloc(24);
  const fd = fs.openSync(sciezka, "r");
  fs.readSync(fd, bufor, 0, 24, 0);
  fs.closeSync(fd);

  if (bufor.toString("ascii", 12, 16) !== "IHDR") {
    throw new Error(`Nie-PNG lub uszkodzony plik: ${sciezka}`);
  }
  return { width: bufor.readUInt32BE(16), height: bufor.readUInt32BE(20) };
}

module.exports = rozmiarPng;
