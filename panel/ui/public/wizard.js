"use strict";

/**
 * Panel raportów — klient wizarda. Vanilla JS, bez frameworka/build stepu
 * (patrz server.js). Routing przez hash: #/ (lista projektów), #/projekt/ID.
 * Stan trzymany w pamięci (`stan.projekt`), zapisywany do projekt.json na
 * dysku po każdej zmianie sekcji (PUT /api/projekty/:id) — zgodnie ze
 * spec §2: możliwość przerwania i wznowienia pracy w dowolnym momencie.
 */

const app = document.getElementById("app");
const stan = { projekt: null, aktywnyPunkt: 1 };

// Musi odpowiadać POLA_TEKSTOW_PUNKTU / POLA_TEKSTOW_PODSUMOWANIA w server.js.
const POLA_TEKSTOW_PUNKTU = [
  ["lokalizacja", "Lokalizacja"],
  ["organizacjaRuchu", "Organizacja ruchu"],
  ["ruchWgKierunkow", "Ruch według kierunków"],
  ["ruchPojazdowCiezkich", "Ruch pojazdów ciężkich"],
  ["poryDoby", "Pory doby"],
  ["strukturaRodzajowa", "Struktura rodzajowa"],
  ["komentarzAnalityczny", "Komentarz analityczny"],
];
const POLA_TEKSTOW_PODSUMOWANIA = [
  ["tekstWprowadzenie", "Wprowadzenie"],
  ["tekstPorownanie", "Porównanie punktów"],
  ["tekstWnioski", "Wnioski i rekomendacje"],
];

function formatujDataCzas(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pl-PL", { dateStyle: "medium", timeStyle: "short" });
}

/** Blok "Pobierz raport" — z p.raportInfo (zapisanego w projekt.json), więc
 * przetrwa odświeżenie strony, nie tylko odpowiedź z ostatniego kliknięcia. */
function wyrenderujBlokPobierania(p) {
  const info = p.raportInfo;
  if (!info) return "";
  const linkiXlsx = (info.zalaczniki || [])
    .map((z) => `<li><a href="${z.url}" download>${escapeHtml(z.nazwa)}</a></li>`)
    .join("");
  return `
    <div class="blok-pobierania">
      <p class="znacznik-czasu">Wygenerowano: ${formatujDataCzas(info.wygenerowanoO)}</p>
      <a class="przycisk-link" href="${info.url}" download>Pobierz raport</a>
      <a class="przycisk-link wtorne" href="/api/projekty/${p._id}/pobierz-wszystko.zip" download>Pobierz wszystko (.zip)</a>
      ${linkiXlsx ? `<p class="podpowiedz" style="margin-top:10px">Załączniki (§5, pełne dane godzinowe):</p><ul class="lista-zalacznikow">${linkiXlsx}</ul>` : ""}
    </div>`;
}

// --- Pomoc: API ---------------------------------------------------------

async function api(sciezka, opcje) {
  const res = await fetch(sciezka, {
    ...opcje,
    headers: { "Content-Type": "application/json" },
  });
  const dane = await res.json();
  if (!res.ok) throw new Error(dane.blad || `Błąd HTTP ${res.status}`);
  return dane;
}

async function zapiszProjekt() {
  await api(`/api/projekty/${stan.projekt._id}`, { method: "PUT", body: JSON.stringify(stan.projekt) });
}

async function plikNaBase64(plik) {
  const bufor = await plik.arrayBuffer();
  const bajty = new Uint8Array(bufor);
  let binarnie = "";
  const kawalek = 0x8000;
  for (let i = 0; i < bajty.length; i += kawalek) binarnie += String.fromCharCode(...bajty.subarray(i, i + kawalek));
  return btoa(binarnie);
}

function pokazStatus(el, tekst, ok = true) {
  el.textContent = tekst;
  el.className = ok ? "status-zapisu" : "status-blad";
  setTimeout(() => { el.textContent = ""; }, 2500);
}

// --- Routing --------------------------------------------------------------

window.addEventListener("hashchange", wyrenderujTrase);
window.addEventListener("DOMContentLoaded", wyrenderujTrase);

function wyrenderujTrase() {
  const hash = window.location.hash;
  const dopasowanie = hash.match(/^#\/projekt\/(.+)$/);
  if (dopasowanie) {
    wczytajIWyrenderujProjekt(dopasowanie[1]);
  } else {
    wyrenderujLande();
  }
}

// --- Widok: lista projektów + nowy projekt ---------------------------------

async function wyrenderujLande() {
  const projekty = await api("/api/projekty");
  app.innerHTML = `
    <section class="karta">
      <h2>Projekty</h2>
      ${projekty.length === 0 ? "<p>Brak zapisanych projektów.</p>" : `
        <ul class="lista-projektow">
          ${projekty.map((p) => {
            const zakresDat = p.dataPomiaruOd
              ? (p.dataPomiaruOd === p.dataPomiaruDo ? p.dataPomiaruOd : `${p.dataPomiaruOd} – ${p.dataPomiaruDo}`)
              : "brak danych pomiaru";
            return `
            <li>
              <span class="info-projektu">
                <a href="#/projekt/${p.id}">${escapeHtml(p.nazwaProjektu || "(bez nazwy)")}</a>
                — ${p.liczbaPunktow} pkt. pomiarowych
                <span class="podpowiedz">Data pomiaru: ${escapeHtml(zakresDat)} • ${p.id}</span>
              </span>
              <span class="akcje-projektu">
                <button type="button" class="wtorne przycisk-pobierz-pelny"
                        data-id="${p.id}" ${p.czyGotowyDoRaportu ? "" : "disabled"}
                        title="${p.czyGotowyDoRaportu ? "" : "Wymaga ukończonych obliczeń (krok 7) przynajmniej dla jednego punktu"}">
                  Pobierz pełny raport
                </button>
                <span class="status-zapisu" data-status-id="${p.id}"></span>
              </span>
            </li>
          `;
          }).join("")}
        </ul>
      `}
    </section>

    <section class="karta">
      <h2>Nowy projekt</h2>
      <form id="formularz-nowy-projekt">
        <label>Nazwa projektu</label>
        <input type="text" name="nazwaProjektu" required placeholder="Pomiar ruchu drogowego - Toruń">

        <label>Zamawiający</label>
        <input type="text" name="zamawiajacy" placeholder="[NAZWA ZAMAWIAJĄCEGO]">

        <div class="wiersz-dwie-kolumny">
          <div>
            <label>Data od (opcjonalnie — zaciągnie się z wgranych plików)</label>
            <input type="date" name="dataOd">
          </div>
          <div>
            <label>Data do (opcjonalnie)</label>
            <input type="date" name="dataDo">
          </div>
        </div>

        <label>Link do wytycznych GDDKiA</label>
        <input type="url" name="linkWytyczneGDDKiA" placeholder="https://www.gov.pl/...">

        <button type="submit">Utwórz projekt</button>
      </form>
    </section>
  `;

  for (const przycisk of document.querySelectorAll(".przycisk-pobierz-pelny")) {
    przycisk.addEventListener("click", async () => {
      const id = przycisk.dataset.id;
      const statusEl = document.querySelector(`[data-status-id="${id}"]`);
      przycisk.disabled = true;
      statusEl.textContent = "Generowanie raportu (może potrwać kilka minut)...";
      try {
        const wynik = await api(`/api/projekty/${id}/generuj-raport`, { method: "POST" });
        pokazStatus(statusEl, "Gotowe — pobieranie ✓");
        // Content-Disposition: attachment — samo pobranie, bez opuszczania listy.
        window.location.href = wynik.url;
      } catch (err) {
        pokazStatus(statusEl, `Błąd: ${err.message}`, false);
      } finally {
        przycisk.disabled = false;
      }
    });
  }

  document.getElementById("formularz-nowy-projekt").addEventListener("submit", async (e) => {
    e.preventDefault();
    const dane = Object.fromEntries(new FormData(e.target));
    const { id } = await api("/api/projekty", { method: "POST", body: JSON.stringify(dane) });
    window.location.hash = `#/projekt/${id}`;
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

const DNI_TYGODNIA = ["Niedziela", "Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota"];

/** "2026-05-28" -> "Czwartek (dzień roboczy)" — dokładnie format widoczny w referencyjnym raporcie. */
function dzienTygodniaZDaty(dataStr) {
  const dzien = new Date(`${dataStr}T00:00:00`).getDay();
  const typ = dzien >= 1 && dzien <= 5 ? "dzień roboczy" : "weekend";
  return `${DNI_TYGODNIA[dzien]} (${typ})`;
}

/** Przelicza metadaneProjektu.dataOd/dataDo jako min/max dat pomiaru
 * wszystkich punktów, które już mają wypełnioną datę — użytkownik prosił
 * żeby to się "zaciągało" z danych zamiast wpisywać ręcznie z góry. */
function przeliczZakresDatProjektu(projekt) {
  const daty = projekt.punkty.map((p) => p.metadanePomiaru.dataPomiaru).filter(Boolean).sort();
  if (daty.length > 0) {
    projekt.metadaneProjektu.dataOd = daty[0];
    projekt.metadaneProjektu.dataDo = daty[daty.length - 1];
  }
}

// --- Widok: wizard projektu -------------------------------------------------

async function wczytajIWyrenderujProjekt(id) {
  try {
    stan.projekt = await api(`/api/projekty/${id}`);
    stan.projekt._id = id;
  } catch (e) {
    app.innerHTML = `<section class="karta"><p class="status-blad">${escapeHtml(e.message)}</p>
      <p><a class="link-powrot" href="#/">← Powrót do listy projektów</a></p></section>`;
    return;
  }
  stan.aktywnyPunkt = stan.projekt.punkty[0]?.numer || 1;
  await wyrenderujWizard();
}

async function wyrenderujWizard() {
  const p = stan.projekt;
  app.innerHTML = `
    <p><a class="link-powrot" href="#/">← Lista projektów</a></p>

    <section class="karta">
      <h2>Krok 1 — Metadane projektu</h2>
      <form id="formularz-metadane-projektu">
        <label>Nazwa projektu</label>
        <input type="text" name="nazwaProjektu" value="${escapeHtml(p.metadaneProjektu.nazwaProjektu)}" required>
        <div class="wiersz-dwie-kolumny">
          <div>
            <label>Zamawiający</label>
            <input type="text" name="zamawiajacy" value="${escapeHtml(p.metadaneProjektu.zamawiajacy)}">
          </div>
          <div>
            <label>Powyżej ilu punktów przełączyć na tryb zagregowany</label>
            <input type="number" name="progAnalizyLacznej" min="1" value="${p.metadaneProjektu.progAnalizyLacznej}">
          </div>
        </div>
        <div class="wiersz-dwie-kolumny">
          <div>
            <label>Data od (auto z dat pomiaru punktów, edytowalne)</label>
            <input type="date" name="dataOd" value="${p.metadaneProjektu.dataOd}">
          </div>
          <div>
            <label>Data do</label>
            <input type="date" name="dataDo" value="${p.metadaneProjektu.dataDo}">
          </div>
        </div>
        <label>Link do wytycznych GDDKiA</label>
        <input type="url" name="linkWytyczneGDDKiA" value="${escapeHtml(p.metadaneProjektu.linkWytyczneGDDKiA)}">
        <div class="wiersz-dwie-kolumny">
          <div>
            <label>Data sporządzenia raportu</label>
            <input type="date" name="dataSporzadzenia" value="${p.metadaneProjektu.dataSporzadzenia || ""}">
          </div>
          <div>
            <label>Sporządził (imię i nazwisko)</label>
            <input type="text" name="sporzadzil" value="${escapeHtml(p.metadaneProjektu.sporzadzil || "")}">
          </div>
        </div>
        <label>Email osoby odpowiedzialnej za raport</label>
        <input type="email" name="emailOdpowiedzialny" value="${escapeHtml(p.metadaneProjektu.emailOdpowiedzialny || "")}">
        <button type="submit">Zapisz</button>
        <span class="status-zapisu" id="status-metadane"></span>
      </form>
    </section>

    <section class="karta">
      <h2>Punkty pomiarowe</h2>
      <div class="karty-punktow">
        ${p.punkty.map((pkt) => `
          <button type="button" class="karta-punktu-przycisk ${pkt.numer === stan.aktywnyPunkt ? "aktywny" : ""} ${czyPunktUzupelniony(pkt) ? "uzupelniony" : ""}"
                  data-numer="${pkt.numer}">${escapeHtml(pkt.id)}</button>
        `).join("")}
        <button type="button" class="karta-punktu-przycisk karta-punktu-dodaj" id="przycisk-dodaj-punkt" style="border-style:dashed">+ Dodaj punkt</button>
      </div>
      <div id="panel-punktu"></div>
    </section>

    <section class="karta">
      <h2>Krok 10 — Podsumowanie</h2>
      ${(() => {
        const n = p.punkty.length;
        const prog = p.metadaneProjektu.progAnalizyLacznej;
        if (n === 1) {
          return `<p class="podpowiedz">Jeden punkt pomiarowy — analiza łączna (porównawcza) nie ma zastosowania,
            rozdział "Podsumowanie" nie wystąpi w raporcie (Literatura stanie się rozdziałem 4).
            Pola poniżej można pominąć.</p>`;
        }
        const tryb = n <= prog ? "pełny" : "zagregowany";
        return `<p class="podpowiedz">Tryb renderowania: <strong>${tryb}</strong> (${n} punktów, próg ${prog}).</p>`;
      })()}
      <form id="formularz-podsumowanie">
        ${POLA_TEKSTOW_PODSUMOWANIA.map(([pole, etykieta]) => `
          <label>${etykieta}</label>
          <textarea name="${pole}">${escapeHtml(p.podsumowanie.teksty[pole])}</textarea>
        `).join("")}
        <button type="submit">Zapisz podsumowanie</button>
        <span class="status-zapisu" id="status-podsumowanie"></span>
      </form>
      <button type="button" class="wtorne" id="przycisk-generuj-podsumowanie" ${p.punkty.length <= 1 || p.punkty.some((pkt) => !pkt.obliczenia) ? "disabled" : ""}>Wygeneruj Wprowadzenie i Porównanie punktów (reguły, bez AI)</button>
      <span class="status-zapisu" id="status-generuj-podsumowanie"></span>
      <button type="button" class="wtorne" id="przycisk-dodaj-punkt-dol">+ Dodaj punkt</button>
    </section>

    <section class="karta">
      <h2>Krok 11 — Budowa raportu Word</h2>
      ${(() => {
        const brakujace = p.punkty.filter((pkt) => !pkt.obliczenia).map((pkt) => pkt.id);
        if (brakujace.length > 0) {
          return `<p class="podpowiedz">Brakuje obliczeń (krok 7) dla: ${brakujace.join(", ")} — uzupełnij przed generowaniem raportu.</p>
            <button type="button" disabled>Generuj raport Word</button>`;
        }
        return `<p class="podpowiedz">Mapka lokalizacji, schemat skrzyżowania, 4 diagramy Sankey oraz wykresy
          godzinowe (wg relacji, pojazdów ciężkich, profil kategorii, warunki atmosferyczne) generują się
          automatycznie — jeśli punkt nie ma koordynatów/daty pomiaru, albo generator akurat zawiedzie
          (np. brak sieci), ten jeden rysunek dostanie placeholder zamiast blokować cały raport.
          Generowanie z realnymi mapami trwa dłużej niż mogłoby się wydawać — na wolniejszych sieciach
          nawet kilka minut na punkt przy pierwszym uruchomieniu dla danej okolicy, potem szybciej dzięki
          cache. Postęp krok po kroku widać w oknie konsoli serwera.</p>
          <button type="button" id="przycisk-generuj-raport">Generuj raport Word</button>
          <span class="status-zapisu" id="status-generuj-raport"></span>
          <div id="blok-pobierania">${wyrenderujBlokPobierania(p)}</div>`;
      })()}
    </section>
  `;

  document.getElementById("formularz-podsumowanie").addEventListener("submit", async (e) => {
    e.preventDefault();
    Object.assign(p.podsumowanie.teksty, Object.fromEntries(new FormData(e.target)));
    await zapiszProjekt();
    pokazStatus(document.getElementById("status-podsumowanie"), "Zapisano ✓");
  });

  const przyciskGenerujPodsumowanie = document.getElementById("przycisk-generuj-podsumowanie");
  if (przyciskGenerujPodsumowanie) {
    przyciskGenerujPodsumowanie.addEventListener("click", async () => {
      const statusEl = document.getElementById("status-generuj-podsumowanie");
      przyciskGenerujPodsumowanie.disabled = true;
      statusEl.textContent = "Generowanie...";
      try {
        const { tekstWprowadzenie, tekstPorownanie } = await api(
          `/api/projekty/${stan.projekt._id}/generuj-podsumowanie`, { method: "POST" },
        );
        p.podsumowanie.teksty.tekstWprowadzenie = tekstWprowadzenie;
        p.podsumowanie.teksty.tekstPorownanie = tekstPorownanie;
        const formularz = document.getElementById("formularz-podsumowanie");
        formularz.elements.namedItem("tekstWprowadzenie").value = tekstWprowadzenie;
        formularz.elements.namedItem("tekstPorownanie").value = tekstPorownanie;
        pokazStatus(statusEl, "Wygenerowano ✓ — sprawdź i zapisz");
      } catch (err) {
        pokazStatus(statusEl, `Błąd: ${err.message}`, false);
      } finally {
        przyciskGenerujPodsumowanie.disabled = false;
      }
    });
  }

  const przyciskGeneruj = document.getElementById("przycisk-generuj-raport");
  if (przyciskGeneruj) {
    przyciskGeneruj.addEventListener("click", async () => {
      const statusEl = document.getElementById("status-generuj-raport");
      przyciskGeneruj.disabled = true;
      statusEl.textContent = "Generowanie (kilkanaście sekund — placeholdery + docx)...";
      try {
        const wynik = await api(`/api/projekty/${stan.projekt._id}/generuj-raport`, { method: "POST" });
        pokazStatus(statusEl, "Gotowe ✓");
        p.raportInfo = { url: wynik.url, zalaczniki: wynik.zalaczniki, wygenerowanoO: wynik.wygenerowanoO };
        document.getElementById("blok-pobierania").innerHTML = wyrenderujBlokPobierania(p);
      } catch (err) {
        pokazStatus(statusEl, `Błąd: ${err.message}`, false);
      } finally {
        przyciskGeneruj.disabled = false;
      }
    });
  }

  document.getElementById("formularz-metadane-projektu").addEventListener("submit", async (e) => {
    e.preventDefault();
    Object.assign(p.metadaneProjektu, Object.fromEntries(new FormData(e.target)));
    p.metadaneProjektu.progAnalizyLacznej = Number(p.metadaneProjektu.progAnalizyLacznej);
    await zapiszProjekt();
    pokazStatus(document.getElementById("status-metadane"), "Zapisano ✓");
  });

  app.querySelectorAll(".karta-punktu-przycisk:not(.karta-punktu-dodaj)").forEach((btn) => {
    btn.addEventListener("click", () => {
      stan.aktywnyPunkt = Number(btn.dataset.numer);
      wyrenderujWizard();
    });
  });

  const dodajPunkt = async () => {
    const { punkt } = await api(`/api/projekty/${stan.projekt._id}/punkty`, { method: "POST" });
    p.punkty.push(punkt);
    stan.aktywnyPunkt = punkt.numer;
    await wyrenderujWizard();
  };
  document.getElementById("przycisk-dodaj-punkt").addEventListener("click", dodajPunkt);
  document.getElementById("przycisk-dodaj-punkt-dol").addEventListener("click", dodajPunkt);

  await wyrenderujPanelPunktu();
}

function czyPunktUzupelniony(pkt) {
  return Boolean(pkt.nazwa && pkt.kamery.length > 0 && pkt.metadanePomiaru.dataPomiaru);
}

async function wyrenderujPanelPunktu() {
  const pkt = stan.projekt.punkty.find((x) => x.numer === stan.aktywnyPunkt);
  const kontener = document.getElementById("panel-punktu");

  if (!pkt) {
    kontener.innerHTML = "<p class=\"podpowiedz\">Brak punktów w projekcie — kliknij \"+ Dodaj punkt\" powyżej.</p>";
    return;
  }

  const { bramki, wlotyMozliwe } = pkt.kamery.length > 0
    ? await api(`/api/projekty/${stan.projekt._id}/punkty/${pkt.numer}/dane-mapowania`)
    : { bramki: [], wlotyMozliwe: ["PN", "WSCH", "PD", "ZACH"] };

  kontener.innerHTML = `
    <h3>Krok 2 — Dane podstawowe (${escapeHtml(pkt.id)})
      <button type="button" class="niebezpieczne" id="przycisk-usun-punkt" style="font-size:12px;padding:4px 10px;margin-left:12px">Usuń ten punkt</button>
    </h3>
    <form id="formularz-dane-podstawowe">
      <div class="wiersz-dwie-kolumny">
        <div>
          <label>ID punktu</label>
          <input type="text" name="id" value="${escapeHtml(pkt.id)}" required>
        </div>
        <div>
          <label>Typ</label>
          <select name="typ">
            ${["skrzyzowanie", "rondo", "tranzyt", "rejestracja"].map((t) => `<option value="${t}" ${pkt.typ === t ? "selected" : ""}>${t}</option>`).join("")}
          </select>
        </div>
      </div>
      <label>Nazwa (np. Skrzyżowanie Łódzka / Włocławska)</label>
      <input type="text" name="nazwa" value="${escapeHtml(pkt.nazwa)}" required>
      <div class="wiersz-dwie-kolumny">
        <div>
          <label>Miejscowość</label>
          <input type="text" name="miejscowosc" value="${escapeHtml(pkt.miejscowosc)}" required>
        </div>
        <div>
          <label>Współrzędne (lat, lng)</label>
          <input type="text" name="wspolrzedne" value="${pkt.lokalizacja ? `${pkt.lokalizacja.lat}, ${pkt.lokalizacja.lng}` : ""}" placeholder="53.0138, 18.6039">
        </div>
      </div>
      <button type="submit">Zapisz dane podstawowe</button>
      <span class="status-zapisu" id="status-dane-podstawowe"></span>
    </form>

    <h3>Krok 3 — Dane źródłowe (kamery, eksport AISP)</h3>
    <p class="podpowiedz">Wgraj <strong>Quantity.csv</strong> (już zagregowany, kolumny "Kod"/"Godz") ALBO
      surowy <strong>History.csv</strong> (per-detekcja, kolumny "CrossSection"/"Validated"/...) — panel sam
      rozpozna format i w razie potrzeby przekonwertuje History→Quantity po stronie serwera (liczy tylko
      wiersze z Validated=1). Dla kamery 2+ przesunięcie bramek liczone jest automatycznie (żeby bramki
      różnych kamer się nie kolidowały).</p>
    <input type="file" id="input-plik-csv" accept=".csv" multiple>
    <div id="status-upload"></div>
    ${pkt.kamery.length > 0 ? `
      <table class="tabela-kamer">
        <thead><tr><th>Plik</th><th>Bramki w danych</th><th>Przesunięcie bramek</th><th></th></tr></thead>
        <tbody>
          ${pkt.kamery.map((k, i) => `
            <tr>
              <td>${escapeHtml(k.plikZrodlowy)}${k.skonwertowanoZHistory ? ' <span class="podpowiedz">(z History.csv)</span>' : ""}</td>
              <td>${k.bramki.join(", ")}</td>
              <td>${k.przesuniecieLiter}</td>
              <td><button type="button" class="wtorne usun-kamere" data-index="${i}">Usuń</button></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    ` : "<p class=\"podpowiedz\">Brak wgranych plików.</p>"}

    <h3>Krok 4 — Metadane pomiaru</h3>
    <form id="formularz-metadane-pomiaru">
      <div class="wiersz-dwie-kolumny">
        <div>
          <label>Data pomiaru</label>
          <input type="date" name="dataPomiaru" value="${pkt.metadanePomiaru.dataPomiaru}" required>
        </div>
        <div>
          <label>Dzień tygodnia</label>
          <input type="text" name="dzienTygodnia" value="${escapeHtml(pkt.metadanePomiaru.dzienTygodnia)}" placeholder="czwartek">
        </div>
      </div>
      <label>Warunki atmosferyczne</label>
      <div style="display:flex; gap:8px; align-items:flex-start">
        <input type="text" name="warunkiAtmosferyczne" style="flex:1" value="${escapeHtml(pkt.metadanePomiaru.warunkiAtmosferyczne)}" placeholder="bez opadów, +21°C" required>
        <button type="button" class="wtorne" id="przycisk-wykryj-pogode" style="margin-top:0; white-space:nowrap" ${!pkt.lokalizacja || !pkt.metadanePomiaru.dataPomiaru ? "disabled" : ""}>Wykryj automatycznie</button>
      </div>
      <span class="status-zapisu" id="status-pogoda"></span>
      <div class="wiersz-dwie-kolumny">
        <div>
          <label>Status przydatności</label>
          <select name="statusPrzydatnosci">
            ${["akceptowalne", "warunkowo_akceptowalne", "do_powtorzenia"].map((s) => `<option value="${s}" ${pkt.metadanePomiaru.statusPrzydatnosci === s ? "selected" : ""}>${s}</option>`).join("")}
          </select>
        </div>
        <div>
          <label>Zakłócenia (opcjonalnie)</label>
          <input type="text" name="zaklocenia" value="${escapeHtml(pkt.metadanePomiaru.zaklocenia || "")}">
        </div>
      </div>
      <button type="submit">Zapisz metadane pomiaru</button>
      <span class="status-zapisu" id="status-metadane-pomiaru"></span>
    </form>

    <h3>Krok 5 — Mapowanie kierunków</h3>
    ${pkt.kamery.length === 0 ? "<p class=\"podpowiedz\">Najpierw wgraj dane źródłowe (krok 3).</p>" : `
      <label><input type="checkbox" id="checkbox-geometria" ${pkt.geometriaRegularna ? "checked" : ""}>
        Geometria regularna (4 wloty, kąty ~90°) — odznacz dla skrzyżowań nietypowych (np. typu T)</label>
      <p class="podpowiedz">Jedna litera = jedna fizyczna bramka skrzyżowania. Przypisz stronę świata każdej
        bramce poniżej — manewr (prawo/wprost/lewo/zawracanie) dla każdej relacji (np. "A-E") jest liczony
        automatycznie z geometrii, nie trzeba go wybierać ręcznie. Jeśli jedna ulica ma osobne bramki na wjazd
        i wyjazd (np. szersza ulica z dwoma pasami) — przypisz obu tę samą stronę świata, to normalne.</p>

      <table class="tabela-kamer">
        <thead><tr><th>Bramka</th><th>Pochodzenie</th><th>Wlot</th></tr></thead>
        <tbody>
          ${bramki.map(({ efektywnaBramka, plikZrodlowy, bramkaSurowa }) => {
            const aktualny = pkt.bramkiMapping[efektywnaBramka];
            return `
              <tr>
                <td>${escapeHtml(efektywnaBramka)}</td>
                <td class="podpowiedz">${escapeHtml(plikZrodlowy)} (${escapeHtml(bramkaSurowa)})</td>
                <td><select class="sel-wlot" data-bramka="${escapeHtml(efektywnaBramka)}">
                  <option value="">— wybierz —</option>
                  ${wlotyMozliwe.map((w) => `<option value="${w}" ${aktualny === w ? "selected" : ""}>${w}</option>`).join("")}
                </select></td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>

      <p class="podpowiedz" style="margin-top:16px">Opis wlotów użytych powyżej (widoczny w tabeli 3.n.1 raportu):</p>
      <div class="wiersz-dwie-kolumny">
        ${wlotyMozliwe.map((kod) => {
          const istniejacy = pkt.wloty.find((w) => w.id === kod);
          return `
            <div>
              <label>${kod} — opis</label>
              <input type="text" class="opis-wlotu" data-kod="${kod}" value="${escapeHtml(istniejacy?.opis || "")}" placeholder="np. ul. Łódzka (od wschodu)">
            </div>
          `;
        }).join("")}
      </div>

      <button type="button" id="przycisk-zapisz-mapowanie">Zapisz i zwaliduj mapowanie</button>
      <span class="status-zapisu" id="status-mapowanie"></span>

      <div id="wynik-walidacji">${renderujWynikWalidacji(pkt.qc)}</div>
    `}

    <h3>Krok 6 — Zdjęcie z kamery i schemat skrzyżowania</h3>
    <p class="podpowiedz">Tylko PNG — budowa .docx (Etap 2/3) czyta wymiary obrazu z nagłówka PNG,
      inne formaty się wysypią przy generowaniu raportu (krok 11).</p>
    <div class="wiersz-dwie-kolumny">
      <div>
        <label>Zdjęcie z kamery (zawsze ręcznie — brak generatora)</label>
        ${pkt.assets.zdjecieKamery ? `<img src="${sciezkaAssetu(pkt.assets.zdjecieKamery)}" style="max-width:100%;border:1px solid var(--obramowanie);border-radius:4px">` : ""}
        <input type="file" id="input-zdjecie-kamery" accept="image/png">
      </div>
      <div>
        <label>Schemat skrzyżowania</label>
        <p class="podpowiedz" style="margin:2px 0 8px">${pkt.lokalizacja
          ? "Opcjonalne — bez uploadu wygeneruje się automatycznie z koordynatów (krok 2) przy budowie raportu (krok 11). Wgraj tylko żeby nadpisać własnym."
          : "Brak koordynatów w kroku 2 — bez nich nie da się wygenerować automatycznie, wgraj ręcznie albo uzupełnij współrzędne."}</p>
        ${pkt.assets.schematSkrzyzowania ? `<img src="${sciezkaAssetu(pkt.assets.schematSkrzyzowania)}" style="max-width:100%;border:1px solid var(--obramowanie);border-radius:4px">` : ""}
        <input type="file" id="input-schemat-skrzyzowania" accept="image/png">
      </div>
    </div>
    <div id="status-asset" class="status-zapisu"></div>

    <h3>Krok 7 — Obliczenia (silnik) i kontrola jakości</h3>
    <p class="podpowiedz">Uruchamia silnik obliczeniowy (Etap 1) na scalonych danych źródłowych tego
      punktu wg zapisanego mapowania. Wymaga ukończonego kroku 5 (brak niezmapowanych bramek).</p>
    <button type="button" id="przycisk-oblicz" ${!pkt.qc || pkt.qc.bramkiNiezmapowane.length > 0 ? "disabled" : ""}>Uruchom obliczenia</button>
    <span class="status-zapisu" id="status-oblicz"></span>
    <div id="wynik-obliczen">${renderujWynikObliczen(pkt.obliczenia, pkt.qc)}</div>

    <h3>Krok 9 — Teksty analityczne</h3>
    <p class="podpowiedz">Generowanie AI (Krok 8) jeszcze nie podłączone. Zamiast tego: przycisk niżej
      wypełnia wszystkie pola regułowym szkicem tekstu dobranym do wyliczonych danych (bez AI, bez sieci) —
      wymaga ukończonego kroku 7. Szkic zawsze można doprecyzować ręcznie przed zapisem.</p>
    <button type="button" class="wtorne" id="przycisk-generuj-teksty" ${!pkt.obliczenia ? "disabled" : ""}>Wygeneruj szkic tekstu (reguły, bez AI)</button>
    <span class="status-zapisu" id="status-generuj-teksty"></span>
    <form id="formularz-teksty-punktu">
      ${POLA_TEKSTOW_PUNKTU.map(([pole, etykieta]) => `
        <label>${etykieta}</label>
        <textarea name="${pole}">${escapeHtml(pkt.teksty[pole])}</textarea>
      `).join("")}
      <button type="submit">Zapisz teksty</button>
      <span class="status-zapisu" id="status-teksty-punktu"></span>
    </form>
  `;

  document.getElementById("formularz-dane-podstawowe").addEventListener("submit", async (e) => {
    e.preventDefault();
    const dane = Object.fromEntries(new FormData(e.target));
    pkt.id = dane.id;
    pkt.typ = dane.typ;
    pkt.nazwa = dane.nazwa;
    pkt.miejscowosc = dane.miejscowosc;
    if (dane.wspolrzedne.trim()) {
      const [lat, lng] = dane.wspolrzedne.split(",").map((n) => Number(n.trim()));
      pkt.lokalizacja = Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : null;
    } else {
      pkt.lokalizacja = null;
    }
    await zapiszProjekt();
    await wyrenderujWizard(); // odśwież etykietę P-karty i checkmark — PRZED pokazStatus, bo rerender tworzy nowy status-span
    pokazStatus(document.getElementById("status-dane-podstawowe"), "Zapisano ✓");
  });

  document.getElementById("formularz-metadane-pomiaru").addEventListener("submit", async (e) => {
    e.preventDefault();
    Object.assign(pkt.metadanePomiaru, Object.fromEntries(new FormData(e.target)));
    if (!pkt.metadanePomiaru.zaklocenia) pkt.metadanePomiaru.zaklocenia = null;
    await zapiszProjekt();
    await wyrenderujWizard(); // odśwież checkmark P-karty — PRZED pokazStatus, bo rerender tworzy nowy status-span
    pokazStatus(document.getElementById("status-metadane-pomiaru"), "Zapisano ✓");
  });

  const przyciskPogoda = document.getElementById("przycisk-wykryj-pogode");
  if (przyciskPogoda) {
    przyciskPogoda.addEventListener("click", async () => {
      const statusEl = document.getElementById("status-pogoda");
      przyciskPogoda.disabled = true;
      statusEl.textContent = "Sprawdzanie pogody (Open-Meteo)...";
      try {
        const { warunkiAtmosferyczne } = await api(`/api/projekty/${stan.projekt._id}/punkty/${pkt.numer}/wykryj-pogode`, { method: "POST" });
        pkt.metadanePomiaru.warunkiAtmosferyczne = warunkiAtmosferyczne;
        document.querySelector('#formularz-metadane-pomiaru input[name="warunkiAtmosferyczne"]').value = warunkiAtmosferyczne;
        pokazStatus(statusEl, "Wykryto ✓ — sprawdź i zapisz");
      } catch (err) {
        pokazStatus(statusEl, `Błąd: ${err.message}`, false);
      } finally {
        przyciskPogoda.disabled = false;
      }
    });
  }

  document.getElementById("input-plik-csv").addEventListener("change", async (e) => {
    const statusEl = document.getElementById("status-upload");
    let dataWykryta = null;
    for (const plik of e.target.files) {
      statusEl.textContent = `Wgrywanie ${plik.name}...`;
      try {
        const tresc = await plik.text();
        const odpowiedz = await api(`/api/projekty/${stan.projekt._id}/punkty/${pkt.numer}/kamery`, {
          method: "POST",
          body: JSON.stringify({ nazwaPliku: plik.name, tresc }),
        });
        if (odpowiedz.dataWykryta) dataWykryta = odpowiedz.dataWykryta;
      } catch (err) {
        pokazStatus(statusEl, `Błąd: ${err.message}`, false);
        return;
      }
    }
    stan.projekt = await api(`/api/projekty/${stan.projekt._id}`);
    // Data pomiaru "zaciągnięta" z pliku (krok 3) zamiast wpisywana ręcznie
    // (krok 4) — tylko jeśli jeszcze pusta, nie nadpisuje ręcznej korekty.
    const pktPoUploadzie = stan.projekt.punkty.find((p) => p.numer === pkt.numer);
    if (dataWykryta && pktPoUploadzie && !pktPoUploadzie.metadanePomiaru.dataPomiaru) {
      pktPoUploadzie.metadanePomiaru.dataPomiaru = dataWykryta;
      pktPoUploadzie.metadanePomiaru.dzienTygodnia = dzienTygodniaZDaty(dataWykryta);
      przeliczZakresDatProjektu(stan.projekt);
      await zapiszProjekt();
      // Współrzędne (krok 2) być może już są wpisane — spróbuj od razu
      // dociągnąć pogodę, żeby użytkownik nie musiał osobno klikać w kroku 4.
      // Best-effort: cichy brak sukcesu (np. brak współrzędnych) nie przerywa uploadu.
      if (pktPoUploadzie.lokalizacja && !pktPoUploadzie.metadanePomiaru.warunkiAtmosferyczne) {
        try {
          const { warunkiAtmosferyczne } = await api(`/api/projekty/${stan.projekt._id}/punkty/${pkt.numer}/wykryj-pogode`, { method: "POST" });
          pktPoUploadzie.metadanePomiaru.warunkiAtmosferyczne = warunkiAtmosferyczne;
        } catch (err) { /* ponytail: cichy brak — użytkownik i tak ma przycisk ręczny w kroku 4 */ }
      }
    }
    await wyrenderujWizard();
  });

  kontener.querySelectorAll(".usun-kamere").forEach((btn) => {
    btn.addEventListener("click", async () => {
      pkt.kamery.splice(Number(btn.dataset.index), 1);
      await zapiszProjekt();
      await wyrenderujWizard();
    });
  });

  const przyciskMapowanie = document.getElementById("przycisk-zapisz-mapowanie");
  if (przyciskMapowanie) {
    przyciskMapowanie.addEventListener("click", async () => {
      const bramkiMapping = {};
      kontener.querySelectorAll(".sel-wlot").forEach((selWlot) => {
        if (selWlot.value) bramkiMapping[selWlot.dataset.bramka] = selWlot.value;
      });
      const wlotyUzyte = new Set(Object.values(bramkiMapping));
      const wloty = [...kontener.querySelectorAll(".opis-wlotu")]
        .filter((input) => wlotyUzyte.has(input.dataset.kod))
        .map((input) => ({ id: input.dataset.kod, opis: input.value, uwagi: "" }));
      const geometriaRegularna = document.getElementById("checkbox-geometria").checked;

      const statusEl = document.getElementById("status-mapowanie");
      try {
        const { qc } = await api(`/api/projekty/${stan.projekt._id}/punkty/${pkt.numer}/mapowanie`, {
          method: "PUT",
          body: JSON.stringify({ bramkiMapping, geometriaRegularna, wloty }),
        });
        pkt.bramkiMapping = bramkiMapping;
        pkt.geometriaRegularna = geometriaRegularna;
        pkt.wloty = wloty;
        pkt.qc = qc;
        // Pełny rerender panelu (nie tylko #wynik-walidacji) — bo stan
        // `disabled` przycisku "Uruchom obliczenia" (krok 7) też zależy od qc.
        await wyrenderujPanelPunktu();
        pokazStatus(document.getElementById("status-mapowanie"), "Zapisano ✓");
      } catch (err) {
        pokazStatus(statusEl, `Błąd: ${err.message}`, false);
      }
    });
  }

  const mapowanieAssetow = { "input-zdjecie-kamery": "zdjecieKamery", "input-schemat-skrzyzowania": "schematSkrzyzowania" };
  for (const [idInputu, pole] of Object.entries(mapowanieAssetow)) {
    const input = document.getElementById(idInputu);
    if (!input) continue;
    input.addEventListener("change", async () => {
      const plik = input.files[0];
      if (!plik) return;
      const statusEl = document.getElementById("status-asset");
      statusEl.textContent = `Wgrywanie ${plik.name}...`;
      try {
        const tresc = await plikNaBase64(plik);
        const { assets } = await api(`/api/projekty/${stan.projekt._id}/punkty/${pkt.numer}/asset`, {
          method: "POST",
          body: JSON.stringify({ pole, nazwaPliku: plik.name, tresc }),
        });
        pkt.assets = assets;
        await wyrenderujWizard(); // rerender tworzy nowy status-span, więc pokazStatus musi być PO
        pokazStatus(document.getElementById("status-asset"), "Zapisano ✓");
      } catch (err) {
        pokazStatus(statusEl, `Błąd: ${err.message}`, false);
      }
    });
  }

  const przyciskOblicz = document.getElementById("przycisk-oblicz");
  if (przyciskOblicz) {
    przyciskOblicz.addEventListener("click", async () => {
      const statusEl = document.getElementById("status-oblicz");
      przyciskOblicz.disabled = true;
      statusEl.textContent = "Liczenie (może potrwać kilka sekund)...";
      try {
        const { obliczenia, przypisyJakosciDanych, qc } = await api(`/api/projekty/${stan.projekt._id}/punkty/${pkt.numer}/oblicz`, { method: "POST" });
        pkt.obliczenia = obliczenia;
        pkt.przypisyJakosciDanych = przypisyJakosciDanych;
        pkt.qc = qc;
        // Pełny rerender (nie tylko panel punktu) — krok 11 na poziomie
        // projektu pokazuje/blokuje przycisk generowania raportu w oparciu
        // o to, czy WSZYSTKIE punkty mają obliczenia.
        await wyrenderujWizard();
        pokazStatus(document.getElementById("status-oblicz"), "Zapisano ✓");
      } catch (err) {
        pokazStatus(statusEl, `Błąd: ${err.message}`, false);
        przyciskOblicz.disabled = false;
      }
    });
  }

  document.getElementById("formularz-teksty-punktu").addEventListener("submit", async (e) => {
    e.preventDefault();
    Object.assign(pkt.teksty, Object.fromEntries(new FormData(e.target)));
    await zapiszProjekt();
    pokazStatus(document.getElementById("status-teksty-punktu"), "Zapisano ✓");
  });

  const przyciskGenerujTeksty = document.getElementById("przycisk-generuj-teksty");
  if (przyciskGenerujTeksty) {
    przyciskGenerujTeksty.addEventListener("click", async () => {
      const statusEl = document.getElementById("status-generuj-teksty");
      przyciskGenerujTeksty.disabled = true;
      statusEl.textContent = "Generowanie...";
      try {
        const { teksty } = await api(`/api/projekty/${stan.projekt._id}/punkty/${pkt.numer}/generuj-teksty`, { method: "POST" });
        pkt.teksty = teksty;
        const formularz = document.getElementById("formularz-teksty-punktu");
        for (const [pole, wartosc] of Object.entries(teksty)) {
          const pole_el = formularz.elements.namedItem(pole);
          if (pole_el) pole_el.value = wartosc;
        }
        pokazStatus(statusEl, "Wygenerowano ✓ — sprawdź i zapisz");
      } catch (err) {
        pokazStatus(statusEl, `Błąd: ${err.message}`, false);
      } finally {
        przyciskGenerujTeksty.disabled = false;
      }
    });
  }

  document.getElementById("przycisk-usun-punkt").addEventListener("click", async () => {
    const potwierdzone = window.confirm(`Usunąć punkt ${pkt.id} (${pkt.nazwa || "bez nazwy"})? Tej operacji nie da się cofnąć — CSV, zdjęcia i wpisane dane tego punktu zostaną trwale usunięte.`);
    if (!potwierdzone) return;
    const { punkty } = await api(`/api/projekty/${stan.projekt._id}/punkty/${pkt.numer}`, { method: "DELETE" });
    stan.projekt.punkty = punkty;
    stan.aktywnyPunkt = punkty[0]?.numer ?? null;
    await wyrenderujWizard();
  });
}

function sciezkaAssetu(sciezkaWzgledna) {
  return `/api/projekty/${stan.projekt._id}/assets/${sciezkaWzgledna}`;
}

function renderujWynikObliczen(obliczenia, qc) {
  if (!obliczenia) return "";
  return `
    <div class="karta" style="border-color:var(--zielony); background:#E8F5E9; margin-top:12px">
      <strong style="color:var(--zielony)">Krok 7b — kontrola jakości: ${qc.status} ✓</strong><br>
      SDR: ${obliczenia.sdr.toLocaleString("pl-PL")} poj./dobę —
      szczyt dobowy ${obliczenia.szczytDobowy.wartosc.toLocaleString("pl-PL")} poj./h o ${obliczenia.szczytDobowy.godzina} —
      ${obliczenia.relacjeSDR.length} relacji
    </div>
  `;
}

function renderujWynikWalidacji(qc) {
  if (!qc) return "";
  const blokiDuplikatow = qc.duplikatyRelacji.length > 0 ? `
    <div class="karta" style="border-color:#FFB74D; background:#FFF8E1; margin-top:12px">
      <strong>Wykryto zdublowane relacje (zostaną automatycznie scalone, suma po wlot+manewr):</strong>
      <ul>
        ${qc.duplikatyRelacji.map((d) => `<li>${d.wlot} / ${d.manewr}: relacje ${d.relacje.join(", ")}</li>`).join("")}
      </ul>
    </div>
  ` : "";
  const blokNiezmapowanych = qc.bramkiNiezmapowane.length > 0 ? `
    <div class="karta" style="border-color:var(--czerwony); background:#FFEBEE; margin-top:12px">
      <strong class="status-blad">Niezmapowane bramki (uzupełnij przed przejściem dalej):</strong>
      ${qc.bramkiNiezmapowane.join(", ")}
    </div>
  ` : `
    <div class="karta" style="border-color:var(--zielony); background:#E8F5E9; margin-top:12px">
      <strong style="color:var(--zielony)">Wszystkie bramki zmapowane ✓</strong>
    </div>
  `;
  return blokNiezmapowanych + blokiDuplikatow;
}
