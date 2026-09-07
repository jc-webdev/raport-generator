"use strict";

// raport-reguly-obliczen-i-danych.md §7: separator tysięcy = spacja,
// procenty z przecinkiem dziesiętnym, zawsze 1 miejsce po przecinku.

function liczba(n) {
  if (n === null || n === undefined) return "-";
  return Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

function procent(p) {
  if (p === null || p === undefined) return "-";
  return p.toFixed(1).replace(".", ",") + "%";
}

module.exports = { liczba, procent };
