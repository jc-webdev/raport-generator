"use strict";

/**
 * Dwa niezależne liczniki (Rysunek / Tabela) startujące od 1, per punkt.
 * Numer = "{prefiks}.{n}" np. "3.1.4" — prefiks to numer rozdziału.punktu.
 * Nigdy nie powtarza numeru, nigdy nie zostawia luki — pominięty element
 * (np. brak T4) po prostu nie inkrementuje licznika tabel, więc kolejne
 * numery same się przesuwają.
 */
class Liczniki {
  constructor(prefiks) {
    this.prefiks = prefiks;
    this.r = 0;
    this.t = 0;
  }

  nastepnyRysunek() {
    this.r += 1;
    return `${this.prefiks}.${this.r}`;
  }

  nastepnaTabela() {
    this.t += 1;
    return `${this.prefiks}.${this.t}`;
  }
}

module.exports = { Liczniki };
