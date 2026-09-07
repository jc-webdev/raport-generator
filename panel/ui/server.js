"use strict";

/**
 * Panel raportów — serwer wizarda (Etap 4, kroki 1-4 wg specyfikacja-panel-
 * generowania-raportow-v2.md §4). Czysty Node.js (http/fs/path) — bez
 * Express/zależności zewnętrznych, żeby dało się to uruchomić na
 * zablokowanym laptopie firmowym samym `node server.js`, bez `npm install`.
 *
 * Stan projektu = projekt.json na dysku (jedyne źródło prawdy między
 * krokami, patrz spec §3) w projekty/<id>/projekt.json. Surowe CSV z kamer
 * lądują obok w projekty/<id>/zrodla/<punktId>/.
 */

const http = require("http");
const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const { execFile, spawn } = require("child_process");
const { generujTekstWprowadzenie, generujTekstPorownanie } = require("../docx/analizaLaczna");
const { budujZip } = require("./zip");

const PORT = process.env.PORT || 4173;
const PUBLIC_DIR = path.join(__dirname, "public");
// Nadpisywalne przez PROJEKTY_DIR — używane przy testowaniu tej aplikacji
// (nie przez jej użytkowników), żeby dane testowe NIGDY nie lądowały w tym
// samym folderze co prawdziwe projekty użytkownika (patrz STAN-PRAC.md —
// przypadek utraty prawdziwego projektu przez sprzątanie po testach).
const PROJEKTY_DIR = process.env.PROJEKTY_DIR
  ? path.resolve(process.env.PROJEKTY_DIR)
  : path.join(__dirname, "projekty");
const REPO_ROOT = path.resolve(__dirname, "..", "..");

/** Silnik Python (Etap 1) żyje w wenv `generator-mapek/venv` — ścieżka do
 * binarki różni się Linux/Mac (bin/python3) vs Windows (Scripts/python.exe).
 * Nadpisywalne przez PYTHON_BIN dla innych układów. */
function pythonBin() {
  if (process.env.PYTHON_BIN) return process.env.PYTHON_BIN;
  const unix = path.join(REPO_ROOT, "generator-mapek", "venv", "bin", "python3");
  const win = path.join(REPO_ROOT, "generator-mapek", "venv", "Scripts", "python.exe");
  if (fs.existsSync(unix)) return unix;
  if (fs.existsSync(win)) return win;
  return "python3";
}

// Na Windows Python domyślnie koduje stdout/stdin/pliki wg strony kodowej
// konsoli (np. cp1250), nie UTF-8 — polskie znaki w JSON-ie/nazwach relacji
// wymienianych między Pythonem a Node psują się w locie (np. "Północny"
// staje się nieodwracalnie uszkodzone znakiem zastępczym U+FFFD). PYTHONUTF8
// wymusza tryb UTF-8 (PEP 540) dla całego I/O Pythona niezależnie od
// systemowej strony kodowej — musi być w env KAŻDEGO spawnowanego procesu
// Pythona, nie tylko tego czytającego pliki.
function envPython() {
  return { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8" };
}

if (!fs.existsSync(PROJEKTY_DIR)) fs.mkdirSync(PROJEKTY_DIR, { recursive: true });

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

// --- Pomoc: projekt.json na dysku ------------------------------------------

/** "Skrzyżowanie Łódzka / Włocławska!" -> "skrzyzowanie-lodzka-wloclawska"
 * (bez polskich znaków — usuwane jako nazwa katalogu na dysku). */
function slugify(tekst) {
  // "ł"/"Ł" nie mają dekompozycji NFD (to nie "l" + akcent, tylko osobna
  // litera z kreską) — trzeba je podmienić ręcznie, inaczej znikają zamiast
  // zamienić się na "l" (np. "Łódzka" -> "odzka", nie "lodzka").
  const bezLZKreska = String(tekst || "").replace(/[łŁ]/g, "l");
  const bezOgonkow = bezLZKreska.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  return bezOgonkow.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 50) || "projekt";
}

/** Folder projektu nazwany czytelnie po nazwie projektu (użytkownik: "niech
 * się tworzy folder z nazwą projektu") + krótki losowy sufiks na wypadek
 * dwóch projektów o tej samej nazwie. */
function idProjektu(nazwaProjektu) {
  return `${slugify(nazwaProjektu)}-${crypto.randomBytes(3).toString("hex")}`;
}

function sciezkaProjektu(id) {
  return path.join(PROJEKTY_DIR, id, "projekt.json");
}

function wczytajProjekt(id) {
  const p = sciezkaProjektu(id);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function zapiszProjekt(id, projekt) {
  const dir = path.dirname(sciezkaProjektu(id));
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(sciezkaProjektu(id), JSON.stringify(projekt, null, 2));
}

function listaProjektow() {
  if (!fs.existsSync(PROJEKTY_DIR)) return [];
  return fs.readdirSync(PROJEKTY_DIR)
    .filter((nazwa) => fs.existsSync(sciezkaProjektu(nazwa)))
    .map((id) => {
      const projekt = wczytajProjekt(id);
      // Data pomiaru per punkt = wyciągnięta automatycznie z uploadowanego
      // History/Quantity.csv (krok 3/4) — tu tylko agregacja min/max po
      // punktach, żeby pokazać zakres na liście bez otwierania projektu.
      const dataPomiarow = projekt.punkty
        .map((p) => p.metadanePomiaru && p.metadanePomiaru.dataPomiaru)
        .filter(Boolean)
        .sort();
      return {
        id,
        nazwaProjektu: projekt.metadaneProjektu.nazwaProjektu,
        liczbaPunktow: projekt.punkty.length,
        // Foldery nazwane po nazwie projektu (nie po dacie jak wcześniej) —
        // sortowanie "najnowsze pierwsze" musi więc iść po dacie modyfikacji
        // pliku, nie po nazwie id.
        zmodyfikowano: fs.statSync(sciezkaProjektu(id)).mtimeMs,
        // Przycisk "Pobierz pełny raport" na liście (bez otwierania projektu)
        // aktywny gdy jest co ukazać — przynajmniej jeden punkt ma ukończony
        // krok 7 (obliczenia), niezależnie czy raport był już wygenerowany.
        czyGotowyDoRaportu: projekt.punkty.some((p) => !!p.obliczenia),
        dataPomiaruOd: dataPomiarow[0] || null,
        dataPomiaruDo: dataPomiarow[dataPomiarow.length - 1] || null,
        raportInfo: projekt.raportInfo || null,
      };
    })
    .sort((a, b) => b.zmodyfikowano - a.zmodyfikowano);
}

// --- Krok 3: upload CSV kamery + auto przesuniecieLiter ---------------------

/** Wyciąga unikalne litery z kolumny "Kierunek" surowego CSV AISP (';' sep). */
/** Surowe (nieprzesunięte) wartości pierwszej kolumny — dla prawdziwego
 * formatu AISP to kody relacji "X-Y" (para bramek wjazd-wyjazd), patrz
 * konwersja_history.py. */
function wartosciWCsv(tresc) {
  const wiersze = tresc.split(/\r?\n/).filter(Boolean);
  const wartosci = new Set();
  for (const wiersz of wiersze.slice(1)) {
    const wartosc = wiersz.split(";")[0]?.trim();
    if (wartosc) wartosci.add(wartosc);
  }
  return [...wartosci].sort();
}

/** "A-E" x N -> unikalne pojedyncze bramki {A, E, ...}. Wartości bez "-"
 * (niepełny ślad pojazdu, patrz konwersja_history.py) nie wnoszą bramek. */
function bramkiZWartosci(wartosci) {
  const bramki = new Set();
  for (const w of wartosci) {
    if (!w.includes("-")) continue;
    const [a, b] = w.split("-");
    if (a) bramki.add(a);
    if (b) bramki.add(b);
  }
  return [...bramki].sort();
}

/** Pierwsza linia History.csv (surowy eksport per-detekcja AISP) ma kolumny
 * CrossSection/Validated/TUID, których Quantity.csv (już zagregowany) nie ma
 * — to wystarcza do odróżnienia formatów bez zgadywania po rozszerzeniu pliku. */
function wygladaJakHistory(tresc) {
  const pierwszaLinia = (tresc.split(/\r?\n/, 1)[0] || "");
  return pierwszaLinia.includes("CrossSection") && pierwszaLinia.includes("Validated");
}

/** Konwertuje surowy History.csv na zagregowany Quantity.csv (Kod;Godz;...)
 * przez panel/silnik/konwersja_history.py — wołane z kroku 3 UI, żeby
 * użytkownik mógł wgrać dowolny z dwóch formatów. */
function konwertujHistoryNaQuantity(tresc) {
  return new Promise((resolve, reject) => {
    const znacznik = crypto.randomBytes(6).toString("hex");
    const tmpIn = path.join(os.tmpdir(), `history_${znacznik}.csv`);
    const tmpOut = path.join(os.tmpdir(), `quantity_${znacznik}.csv`);
    fs.writeFileSync(tmpIn, tresc);
    execFile(
      pythonBin(),
      ["-m", "panel.silnik.uruchom_konwersje_history", tmpIn, tmpOut],
      { cwd: REPO_ROOT, maxBuffer: 20 * 1024 * 1024, env: envPython() },
      (err, stdout, stderr) => {
        fs.rmSync(tmpIn, { force: true });
        if (err) {
          fs.rmSync(tmpOut, { force: true });
          return reject(new Error(stderr || err.message));
        }
        const wynik = fs.readFileSync(tmpOut, "utf-8");
        fs.rmSync(tmpOut, { force: true });
        resolve(wynik);
      },
    );
  });
}

/** Data pomiaru z drugiej kolumny (Czas/Godz) pierwszego wiersza danych —
 * eksport AISP to zawsze pełny cykl dobowy jednego dnia (spec §5.1), więc
 * wystarczy jeden wiersz. Zwraca "YYYY-MM-DD" albo null gdy nie da się
 * rozpoznać (np. pusty plik). */
function wykryjDatePomiaru(tresc) {
  const wiersze = tresc.split(/\r?\n/).filter(Boolean);
  if (wiersze.length < 2) return null;
  const drugaKolumna = wiersze[1].split(";")[1]?.trim();
  const dopasowanie = drugaKolumna?.match(/^(\d{4}-\d{2}-\d{2})/);
  return dopasowanie ? dopasowanie[1] : null;
}

async function dodajKamere(projekt, numerPunktu, nazwaPliku, tresc) {
  const punkt = projekt.punkty.find((p) => p.numer === numerPunktu);
  if (!punkt) throw new Error(`Nie znaleziono punktu numer=${numerPunktu}`);
  if (!punkt.kamery) punkt.kamery = [];

  const skonwertowanoZHistory = wygladaJakHistory(tresc);
  if (skonwertowanoZHistory) tresc = await konwertujHistoryNaQuantity(tresc);

  const wartosci = wartosciWCsv(tresc);
  const bramki = bramkiZWartosci(wartosci);
  const dataWykryta = wykryjDatePomiaru(tresc);
  // Auto przesuniecieLiter (spec §5.1 pkt 3): kamera k>1 przesuwa BRAMKI o
  // liczbę bramek już zajętych przez poprzednie kamery TEGO punktu, żeby się
  // nie kolidowały przy scalaniu (krok 5/7).
  const przesuniecieLiter = punkt.kamery.reduce((suma, k) => suma + k.liczbaLiter, 0);

  const idPunktu = punkt.id || `P${punkt.numer}`;
  const dirZrodla = path.join(PROJEKTY_DIR, projekt._id, "zrodla", idPunktu);
  if (!fs.existsSync(dirZrodla)) fs.mkdirSync(dirZrodla, { recursive: true });
  fs.writeFileSync(path.join(dirZrodla, nazwaPliku), tresc);

  punkt.kamery.push({
    plikZrodlowy: nazwaPliku, przesuniecieLiter, liczbaLiter: bramki.length,
    litery: wartosci, bramki, skonwertowanoZHistory,
  });
  return { przesuniecieLiter, litery: wartosci, bramki, skonwertowanoZHistory, dataWykryta };
}

// --- Krok 5/5b: mapowanie BRAMEK na wloty + walidacja blokująca ------------
//
// Prawdziwy format AISP: pojedyncza litera = jedna fizyczna bramka/wlot
// skrzyżowania, obserwowany "Kierunek"/"Kod" to PARA bramek "X-Y" = wjazd
// bramką X, wyjazd bramką Y (patrz konwersja_history.py i
// mapowanie.py::zmapuj_relacje_z_bramek w silniku). Użytkownik mapuje więc
// TYLKO pojedyncze bramki na strony świata — manewr liczy się geometrycznie
// z pary wlot_wejścia/wlot_wyjścia (patrz obliczManewr niżej, port 1:1
// silnika `opisy.oblicz_manewr`), zamiast być klikany ręcznie per relacja.

const WLOTY_MOZLIWE = ["PN", "WSCH", "PD", "ZACH"]; // silnik (kategorie.py) nie zna innych

const BEARING = { PN: 0, WSCH: 90, PD: 180, ZACH: 270 };
const DIFF_NA_MANEWR = { 0: "Zawracający", 90: "Lewo", 180: "Wprost", 270: "Prawo" };

/** Musi zostać bit-identyczna z panel/silnik/opisy.py::oblicz_manewr — obie
 * strony (Python krok 7, Node krok 5) liczą to samo z tych samych danych. */
function obliczManewr(wlotWejscia, wlotWyjscia) {
  const diff = (((BEARING[wlotWyjscia] - BEARING[wlotWejscia]) % 360) + 360) % 360;
  return DIFF_NA_MANEWR[diff];
}

/** Index (0-based) -> etykieta liter w stylu Excela (0=A,25=Z,26=AA,...). */
function indeksNaLitere(n) {
  let etykieta = "";
  let i = n + 1;
  while (i > 0) {
    const reszta = (i - 1) % 26;
    etykieta = String.fromCharCode(65 + reszta) + etykieta;
    i = Math.floor((i - 1) / 26);
  }
  return etykieta;
}

function przesunBramke(bramkaSurowa, przesuniecie) {
  const indeksSurowy = bramkaSurowa.toUpperCase().charCodeAt(0) - 65;
  return indeksNaLitere(indeksSurowy + przesuniecie);
}

/** "A-E" x przesunięcie -> "A'-E'" (obie bramki przesunięte niezależnie).
 * null gdy wartość to niepełny ślad (bez myślnika) — pomijana tak samo jak
 * w silniku (mapowanie.py::rozbij_relacje). */
function przesunRelacje(relacjaSurowa, przesuniecie) {
  if (!relacjaSurowa.includes("-")) return null;
  const [a, b] = relacjaSurowa.split("-");
  if (!a || !b) return null;
  return `${przesunBramke(a, przesuniecie)}-${przesunBramke(b, przesuniecie)}`;
}

/**
 * Efektywne dane punktu = surowe bramki/relacje każdej kamery przesunięte o
 * jej `przesuniecieLiter` (spec §5.1 pkt 3), żeby kamery się nie kolidowały.
 * `bramki` — do tabeli mapowania (krok 5 UI). `relacje` — do wykrywania
 * duplikatów po zmapowaniu (krok 5b) i do audytu.
 */
function efektywneDanePunktu(punkt) {
  const bramki = [];
  const relacje = [];
  for (const kamera of punkt.kamery || []) {
    for (const bramkaSurowa of kamera.bramki || []) {
      bramki.push({ efektywnaBramka: przesunBramke(bramkaSurowa, kamera.przesuniecieLiter), plikZrodlowy: kamera.plikZrodlowy, bramkaSurowa });
    }
    for (const relacjaSurowa of kamera.litery || []) {
      const efektywnaRelacja = przesunRelacje(relacjaSurowa, kamera.przesuniecieLiter);
      if (efektywnaRelacja) relacje.push({ efektywnaRelacja, plikZrodlowy: kamera.plikZrodlowy, relacjaSurowa });
    }
  }
  return { bramki, relacje };
}

function zwalidujMapowanie(punkt) {
  const { bramki, relacje } = efektywneDanePunktu(punkt);
  const mapping = punkt.bramkiMapping || {};
  const bramkiNiezmapowane = [...new Set(bramki.map((b) => b.efektywnaBramka))].filter((b) => !mapping[b]).sort();

  // Duplikaty: różne relacje (pary bramek), które po zmapowaniu wychodzą na
  // tę samą (wlot, manewr) — odpowiednik starych "zdublowanych etykiet AISP",
  // tu wykryte geometrycznie zamiast ręcznie.
  const grupy = new Map();
  for (const { efektywnaRelacja } of relacje) {
    const [a, b] = efektywnaRelacja.split("-");
    if (!mapping[a] || !mapping[b]) continue;
    const wlot = mapping[a];
    const manewr = obliczManewr(wlot, mapping[b]);
    const klucz = `${wlot}|${manewr}`;
    if (!grupy.has(klucz)) grupy.set(klucz, new Set());
    grupy.get(klucz).add(efektywnaRelacja);
  }
  const duplikatyRelacji = [];
  for (const [klucz, zbiorRelacji] of grupy) {
    if (zbiorRelacji.size > 1) {
      const [wlot, manewr] = klucz.split("|");
      duplikatyRelacji.push({ wlot, manewr, relacje: [...zbiorRelacji].sort(), sugerowanaAkcja: "scal w jedną relację (suma po kluczu wlot+manewr)" });
    }
  }

  return {
    bramkiNiezmapowane,
    duplikatyRelacji,
    sumaKontrolna: { ok: true, roznica: 0 },
    kategorieWyzerowaneGodzinowo: [],
    status: bramkiNiezmapowane.length > 0 ? "do_korekty" : "akceptacja",
  };
}

// --- Krok 4: auto-wykrywanie warunków atmosferycznych -----------------------
//
// Użytkownik: "ciężko wpisać z klawiatury stopnie Celsjusza" — zamiast ręcznego
// wpisywania, Open-Meteo Archive API (https://open-meteo.com, historyczne dane
// pogodowe, BEZ klucza/rejestracji — jak OSM dla map, zero nowej zależności,
// tylko wbudowany `fetch` w Node 22) dla koordynatów punktu (krok 2) + daty
// pomiaru (krok 4, już auto-wykrytej z pliku) zwraca średnią temperaturę
// dobową i sumę opadów.
// AbortSignal.timeout — bez tego zerwane/zablokowane połączenie (np. firewall
// firmowy cicho odrzucający pakiety, bez odpowiedzi) potrafi wisieć znacznie
// dłużej niż limity nałożone na spawnowane skrypty Pythona (tam execFile ma
// twardy timeout), sprawiając wrażenie zawieszonego generowania raportu.
const TIMEOUT_FETCH_MS = 15000;

async function wykryjPogode(lat, lon, data) {
  const url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}`
    + `&start_date=${data}&end_date=${data}&daily=temperature_2m_mean,precipitation_sum&timezone=Europe%2FWarsaw`;
  const odpowiedz = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT_FETCH_MS) });
  if (!odpowiedz.ok) throw new Error(`Open-Meteo zwróciło błąd HTTP ${odpowiedz.status}`);
  const dane = await odpowiedz.json();
  const temperatura = dane.daily?.temperature_2m_mean?.[0];
  const opady = dane.daily?.precipitation_sum?.[0];
  if (temperatura === undefined || temperatura === null) {
    throw new Error("Brak danych pogodowych dla tej daty/lokalizacji (data spoza zasięgu archiwum?)");
  }
  const opisOpadow = opady > 0.2 ? `opady (${opady.toFixed(1)} mm)` : "bez opadów";
  const znakTemp = temperatura >= 0 ? "+" : "";
  return `${opisOpadow}, temperatura ok. ${znakTemp}${Math.round(temperatura)}°C`;
}

// Wariant godzinowy tego samego archiwum — do wykresu Rysunek 3.n.2 (przebieg
// temperatury/opadów w trakcie doby pomiaru, patrz generuj_wykres_pogoda.py).
async function wykryjPogodeGodzinowo(lat, lon, data) {
  const url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}`
    + `&start_date=${data}&end_date=${data}&hourly=temperature_2m,precipitation&timezone=Europe%2FWarsaw`;
  const odpowiedz = await fetch(url, { signal: AbortSignal.timeout(TIMEOUT_FETCH_MS) });
  if (!odpowiedz.ok) throw new Error(`Open-Meteo zwróciło błąd HTTP ${odpowiedz.status}`);
  const dane = await odpowiedz.json();
  const temperatura = dane.hourly?.temperature_2m;
  const opady = dane.hourly?.precipitation;
  if (!temperatura || temperatura.length !== 24) {
    throw new Error("Brak godzinowych danych pogodowych dla tej daty/lokalizacji (data spoza zasięgu archiwum?)");
  }
  return { godziny: dane.hourly.time.map((t) => t.slice(11, 16)), temperatura, opady };
}

// --- Krok 6: upload zdjęcia z kamery / schematu skrzyżowania ---------------

const POLA_ASSETOW = ["zdjecieKamery", "schematSkrzyzowania"];

function zapiszAsset(projekt, numerPunktu, pole, nazwaPliku, tresc) {
  if (!POLA_ASSETOW.includes(pole)) throw new Error(`Nieznane pole assetu: ${pole}`);
  const punkt = projekt.punkty.find((p) => p.numer === numerPunktu);
  if (!punkt) throw new Error(`Nie znaleziono punktu numer=${numerPunktu}`);

  const idPunktu = punkt.id || `P${punkt.numer}`;
  const rozszerzenie = path.extname(nazwaPliku).toLowerCase() || ".png";
  if (rozszerzenie !== ".png") {
    throw new Error("Tylko PNG — budowa .docx czyta wymiary obrazu z nagłówka PNG (patrz probaRozmiaru.js)");
  }
  const dirAssets = path.join(PROJEKTY_DIR, projekt._id, "assets", idPunktu);
  if (!fs.existsSync(dirAssets)) fs.mkdirSync(dirAssets, { recursive: true });
  const nazwaDocelowa = `${pole}${rozszerzenie}`;
  fs.writeFileSync(path.join(dirAssets, nazwaDocelowa), Buffer.from(tresc, "base64"));

  if (!punkt.assets) punkt.assets = {};
  punkt.assets[pole] = `${idPunktu}/${nazwaDocelowa}`; // ścieżka względna, pod GET .../assets/:sciezka
}

// --- Krok 7/7b: uruchomienie silnika Python + bramka jakości ---------------

function uruchomSilnik(sciezkaProjektu, numerPunktu) {
  return new Promise((resolve, reject) => {
    execFile(
      pythonBin(),
      ["-m", "panel.silnik.uruchom_dla_punktu", sciezkaProjektu, String(numerPunktu)],
      { cwd: REPO_ROOT, maxBuffer: 50 * 1024 * 1024, env: envPython() },
      (err, stdout, stderr) => {
        if (err) return reject(new Error(stderr || err.message));
        try { resolve(JSON.parse(stdout)); } catch (e) { reject(new Error(`Silnik zwrócił niepoprawny JSON: ${stdout.slice(0, 500)}`)); }
      },
    );
  });
}

// --- Krok 9/10: teksty analityczne (placeholder do czasu podłączenia AI, krok 8) --

const PLACEHOLDER_TEKSTU = "[SZKIC — do zastąpienia tekstem z Etapu 4/AI]";
const POLA_TEKSTOW_PUNKTU = [
  "lokalizacja", "organizacjaRuchu", "ruchWgKierunkow", "ruchPojazdowCiezkich",
  "poryDoby", "strukturaRodzajowa", "komentarzAnalityczny",
];
const POLA_TEKSTOW_PODSUMOWANIA = ["tekstWprowadzenie", "tekstPorownanie", "tekstWnioski"];

function domyslneTeksty(pola) {
  return Object.fromEntries(pola.map((p) => [p, PLACEHOLDER_TEKSTU]));
}

// --- Krok 11: budowa raportu Word -------------------------------------------
//
// Pomost między kształtem projekt.json tego UI (spec v2 §3 — lokalizacja
// {lat,lng}, bramkiMapping, qc) a kształtem fixture jakiego oczekuje
// panel/docx/budujRaport.js (wloty[] płaskie z gotowym opisem, assets.*
// zawsze {zrodlo,plik}) — udokumentowany rozjazd, patrz STAN-PRAC.md.
//
// Reguła placeholderów (spec §5.7): dopóki nie ma dedykowanego generatora,
// NIE tworzymy osobnego prowizorycznego wykresu na punkt — jeden wspólny
// plik na typ rysunku, reużywany przez wszystkie punkty projektu.

const DOCX_DIR = path.join(REPO_ROOT, "panel", "docx");
const LOGO_DOMYSLNE = path.join(DOCX_DIR, "assets", "logo.png");
const MAPY_SKRZYZOWANIA_DIR = path.join(REPO_ROOT, "Generaotr-mapy-skrzyzowania");
const MAPEK_DIR = path.join(REPO_ROOT, "generator-mapek");

const PLACEHOLDERY_WSPOLNE = {
  // Wszystkie poniższe MAJĄ realny generator (patrz pętla w zbudujRaport()) —
  // ten tekst pokazuje się tylko gdy generator faktycznie zawiedzie (best-effort,
  // patrz try/catch przy wywołaniach), nie jako stały stan "w przygotowaniu".
  mapkaLokalizacji: "Mapka lokalizacji\n(nie udało się wygenerować)",
  sankeySDR: "Diagram SDR\n(nie udało się wygenerować — docelowo Visum)",
  sankeyPoranny: "Diagram szczytu porannego\n(nie udało się wygenerować — docelowo Visum)",
  sankeyPopoludniowy: "Diagram szczytu popołudniowego\n(nie udało się wygenerować — docelowo Visum)",
  godzinowaRelacje: "Rozkład godzinowy wg relacji\n(nie udało się wygenerować)",
  godzinowaCiezkie: "Rozkład godzinowy ciężkich wg relacji\n(nie udało się wygenerować)",
  profilKategorie: "Profil dobowy wg kategorii\n(nie udało się wygenerować)",
  wykresPogoda: "Wykres warunków atmosferycznych\n(brak lokalizacji lub daty pomiaru)",
  zdjecieKamery: "Zdjęcie z kamery\n(nie wgrano)", // wyłącznie ręczny upload, brak generatora
  schematSkrzyzowania: "Schemat skrzyżowania\n(nie udało się wygenerować i brak ręcznego uploadu)",
};

function generujObraz(argi) {
  return new Promise((resolve, reject) => {
    execFile(pythonBin(), argi, { cwd: DOCX_DIR, maxBuffer: 10 * 1024 * 1024, env: envPython() }, (err, stdout, stderr) => {
      if (err) return reject(new Error(stderr || err.message));
      resolve();
    });
  });
}

// --- Realne generatory z koordynatów (mapka/schemat/Sankey) ----------------
//
// Istniały od dawna w Generaotr-mapy-skrzyzowania/ i generator-mapek/ —
// wcześniej pominięte przy budowie kroku 11 (błąd, patrz STAN-PRAC.md).
// Wołane tylko gdy punkt ma `lokalizacja.lat/lng` (krok 2); w razie
// błędu (brak sieci, brak dróg w zcache'owanym regionie...) każdy z nich
// osobno spada na placeholder — jeden nieudany rysunek nie blokuje reszty.
function spawnPython(argi, cwd, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    execFile(pythonBin(), argi, { cwd, maxBuffer: 20 * 1024 * 1024, timeout: timeoutMs, env: envPython() }, (err, stdout, stderr) => {
      if (err) return reject(new Error(stderr || err.message));
      resolve(stdout);
    });
  });
}

function generujMapkeLokalizacji(lat, lon, wyjscie) {
  return spawnPython(["generate_map.py", "--lat", String(lat), "--lon", String(lon), "--output", wyjscie], MAPEK_DIR);
}

function generujSchematSkrzyzowania(lat, lon, wyjscie) {
  return spawnPython(["generate_intersection_map.py", "--lat", String(lat), "--lon", String(lon), "--output", wyjscie], MAPY_SKRZYZOWANIA_DIR);
}

async function wykryjKierunkiWlotow(lat, lon) {
  const stdout = await spawnPython(["wykryj_wloty.py", "--lat", String(lat), "--lon", String(lon)], MAPY_SKRZYZOWANIA_DIR);
  return JSON.parse(stdout);
}

function generujSankey(lat, lon, sciezkaCsv, sciezkaMapping, metryka, wyjscie) {
  return spawnPython([
    "generate_flow_diagram.py", "--lat", String(lat), "--lon", String(lon),
    "--csv", sciezkaCsv, "--mapping", sciezkaMapping, "--metric", metryka, "--output", wyjscie,
  ], MAPY_SKRZYZOWANIA_DIR);
}

const METRYKI_SANKEY = { sankeySDR: "sdr", sankeyUPC: "upc", sankeyPoranny: "am_peak", sankeyPopoludniowy: "pm_peak" };

// Błędy generatorów (best-effort, jeden nieudany rysunek nie blokuje reszty)
// wtapiały się w zwykłe logi postępu, zwłaszcza gdy stderr spawnowanego
// Pythona zawierał wielolinijkowe INFO/WARNING logging — wyglądało to jak
// normalny log, nie jak błąd. Wyraźne ograniczniki ">>> BŁĄD <<<" usuwają tę
// dwuznaczność.
function logBlad(prefiks, e) {
  console.error(`\n>>> BŁĄD [${prefiks}] <<<`);
  console.error(String((e && e.message) || e).trim());
  console.error(">>> koniec błędu <<<\n");
}

/**
 * Próbuje wygenerować mapkę/schemat/4x Sankey z realnych koordynatów punktu.
 * Zwraca { [klucz]: sciezkaPliku } tylko dla tego co się faktycznie udało —
 * wołający ma dopełnić resztę placeholderami. Nigdy nie rzuca — błąd
 * pojedynczego rysunku loguje się i po prostu brakuje go w wyniku.
 */
async function spróbujWygenerowacRealneRysunki(punkt, dirPunktu, sciezkaProjektu) {
  const wynik = {};
  if (!punkt.lokalizacja || !punkt.lokalizacja.lat || !punkt.lokalizacja.lng) return wynik;
  const { lat, lng: lon } = punkt.lokalizacja;

  try {
    console.log(`[${punkt.id}] mapka lokalizacji: generuję (OSM, może potrwać ok. 1-2 min przy pierwszym użyciu tej okolicy)...`);
    const sciezka = path.join(dirPunktu, "mapka_lokalizacji.png");
    await generujMapkeLokalizacji(lat, lon, sciezka);
    wynik.mapkaLokalizacji = sciezka;
    console.log(`[${punkt.id}] mapka lokalizacji: gotowe ✓`);
  } catch (e) {
    logBlad(`${punkt.id} mapka lokalizacji`, e);
  }

  try {
    console.log(`[${punkt.id}] schemat skrzyżowania: generuję (OSM)...`);
    const sciezka = path.join(dirPunktu, "schemat_skrzyzowania.png");
    await generujSchematSkrzyzowania(lat, lon, sciezka);
    wynik.schematSkrzyzowania = sciezka;
    console.log(`[${punkt.id}] schemat skrzyżowania: gotowe ✓`);
  } catch (e) {
    logBlad(`${punkt.id} schemat skrzyżowania`, e);
  }

  try {
    const dataPomiaru = punkt.metadanePomiaru && punkt.metadanePomiaru.dataPomiaru;
    if (!dataPomiaru) throw new Error("brak daty pomiaru");
    console.log(`[${punkt.id}] wykres pogody: pobieram dane z Open-Meteo...`);
    const godzinowa = await wykryjPogodeGodzinowo(lat, lon, dataPomiaru);
    const sciezkaDane = path.join(dirPunktu, "_pogoda.json");
    fs.writeFileSync(sciezkaDane, JSON.stringify(godzinowa));
    const sciezka = path.join(dirPunktu, "wykres_pogoda.png");
    await generujObraz(["generuj_wykres_pogoda.py", sciezkaDane, sciezka]);
    fs.unlinkSync(sciezkaDane);
    wynik.wykresPogoda = sciezka;
    console.log(`[${punkt.id}] wykres pogody: gotowe ✓`);
  } catch (e) {
    logBlad(`${punkt.id} wykres pogody`, e);
  }

  try {
    console.log(`[${punkt.id}] Sankey: przygotowuję dane i wykrywam wloty (OSM)...`);
    const sciezkaCsv = path.join(dirPunktu, "relacje_synth.csv");
    const sciezkaMappingBazowa = path.join(dirPunktu, "relacje_mapping_bazowa.json");
    await spawnPython([
      "-m", "panel.silnik.eksportuj_relacje_synth", sciezkaProjektu, String(punkt.numer),
      sciezkaCsv, sciezkaMappingBazowa,
    ], REPO_ROOT);

    const wloty = await wykryjKierunkiWlotow(lat, lon);
    const mapping = JSON.parse(fs.readFileSync(sciezkaMappingBazowa, "utf-8"));
    mapping.wlot_to_arm_direction = Object.fromEntries(Object.entries(wloty).map(([k, v]) => [k, v.direction]));
    const sciezkaMapping = path.join(dirPunktu, "relacje_mapping.json");
    fs.writeFileSync(sciezkaMapping, JSON.stringify(mapping));

    for (const [klucz, metryka] of Object.entries(METRYKI_SANKEY)) {
      try {
        console.log(`[${punkt.id}] ${klucz}: generuję...`);
        const sciezka = path.join(dirPunktu, `${klucz}.png`);
        await generujSankey(lat, lon, sciezkaCsv, sciezkaMapping, metryka, sciezka);
        wynik[klucz] = sciezka;
        console.log(`[${punkt.id}] ${klucz}: gotowe ✓`);
      } catch (e) {
        logBlad(`${punkt.id} ${klucz}`, e);
      }
    }
  } catch (e) {
    logBlad(`${punkt.id} eksport danych do Sankey`, e);
  }

  return wynik;
}

async function zbudujRaport(projekt) {
  console.log(`Rozpoczynam generowanie raportu: "${projekt.metadaneProjektu.nazwaProjektu}" (${projekt.punkty.length} pkt.)`);
  const brakObliczen = projekt.punkty.filter((p) => !p.obliczenia).map((p) => p.id);
  if (brakObliczen.length > 0) {
    throw new Error(`Punkty bez ukończonego kroku 7 (obliczenia): ${brakObliczen.join(", ")}`);
  }

  const dirBuild = path.join(PROJEKTY_DIR, projekt._id, "build");
  const dirAssets = path.join(dirBuild, "assets");
  fs.mkdirSync(dirAssets, { recursive: true });

  const placeholdery = {};
  for (const [klucz, tekst] of Object.entries(PLACEHOLDERY_WSPOLNE)) {
    const sciezka = path.join(dirAssets, `placeholder_${klucz}.png`);
    await generujObraz(["generuj_placeholder.py", tekst, sciezka]);
    placeholdery[klucz] = sciezka;
  }

  const punktyFixture = [];
  for (const punkt of projekt.punkty) {
    console.log(`[${punkt.id}] przetwarzanie punktu...`);
    const dirPunktu = path.join(dirAssets, punkt.id);
    fs.mkdirSync(dirPunktu, { recursive: true });
    const sciezkaPoryDoby = path.join(dirPunktu, "pory_doby.png");
    const sciezkaProfilKategorie = path.join(dirPunktu, "profil_kategorie.png");
    const tmpObliczenia = path.join(dirPunktu, "_obliczenia.json");
    fs.writeFileSync(tmpObliczenia, JSON.stringify({ obliczenia: punkt.obliczenia }));
    await generujObraz(["generuj_wykres_pory_doby.py", tmpObliczenia, sciezkaPoryDoby]);
    await generujObraz(["generuj_wykres_profil_kategorie.py", tmpObliczenia, sciezkaProfilKategorie]);
    fs.unlinkSync(tmpObliczenia);

    // Rysunek 3.n.3/3.n.4 — rozkład godzinowy wg relacji (zmotoryzowane/ciężkie).
    // `obliczenia` ma tylko sumy dobowe per relacja, więc dane godzinowe trzeba
    // doliczyć osobno z surowego CSV (ta sama ścieżka co eksportuj_wynik_tabele).
    // Best-effort jak reszta realnych generatorów — błąd nie blokuje raportu.
    let sciezkaGodzinowaRelacje = null;
    let sciezkaGodzinowaCiezkie = null;
    try {
      const sciezkaGodzinoweJson = path.join(dirPunktu, "_godzinowe_relacje.json");
      await spawnPython([
        "-m", "panel.silnik.eksportuj_godzinowe_relacje", sciezkaProjektu(projekt._id), String(punkt.numer),
        sciezkaGodzinoweJson,
      ], REPO_ROOT);

      sciezkaGodzinowaRelacje = path.join(dirPunktu, "godzinowa_relacje.png");
      await generujObraz([
        "generuj_wykres_godzinowy_relacje.py", sciezkaGodzinoweJson, "relacjeZmot",
        sciezkaGodzinowaRelacje, "Natężenie ruchu [poj./h]",
      ]);

      sciezkaGodzinowaCiezkie = path.join(dirPunktu, "godzinowa_ciezkie.png");
      await generujObraz([
        "generuj_wykres_godzinowy_relacje.py", sciezkaGodzinoweJson, "relacjeCiezkie",
        sciezkaGodzinowaCiezkie, "Natężenie ruchu pojazdów ciężkich [poj./h]",
      ]);
      fs.unlinkSync(sciezkaGodzinoweJson);
    } catch (e) {
      logBlad(`${punkt.id} wykresy godzinowe wg relacji`, e);
    }

    // Załącznik wynik_tabele_Punkt{N}_{ID}.xlsx — raport Word (budujPunkt.js)
    // odsyła do niego w tekście ("dostępne wyłącznie w załączonym pliku xlsx")
    // od dawna, ale nic go dotąd faktycznie nie generowało (patrz STAN-PRAC.md).
    // Best-effort: brak sukcesu nie blokuje reszty raportu, ale bez niego link
    // w rozdziale 5 wskazywałby donikąd, więc warto zalogować błąd wyraźnie.
    const sciezkaXlsx = path.join(dirBuild, `wynik_tabele_Punkt${punkt.numer}_${punkt.id}.xlsx`);
    try {
      await spawnPython([
        "-m", "panel.silnik.eksportuj_wynik_tabele", sciezkaProjektu(projekt._id), String(punkt.numer), sciezkaXlsx,
      ], REPO_ROOT);
    } catch (e) {
      logBlad(`${punkt.id} wynik_tabele xlsx`, e);
    }

    const realneRysunki = await spróbujWygenerowacRealneRysunki(punkt, dirPunktu, sciezkaProjektu(projekt._id));

    const sciezkaWgrana = (pole) => (punkt.assets && punkt.assets[pole]
      ? path.join(PROJEKTY_DIR, projekt._id, "assets", punkt.assets[pole])
      : null);
    // Kolejność priorytetu: ręczny upload (krok 6) > realnie wygenerowany z
    // koordynatów > placeholder wspólny dla projektu.
    const asset = (wgrana, placeholderKlucz, realnyKlucz) => {
      if (wgrana) return { zrodlo: "upload_manual", plik: wgrana };
      if (realnyKlucz && realneRysunki[realnyKlucz]) return { zrodlo: "generowany", plik: realneRysunki[realnyKlucz] };
      return { zrodlo: "placeholder_punkt1", plik: placeholdery[placeholderKlucz] };
    };
    // Warianty godzinowe (wg relacji/kategorii) nie zależą od lokalizacji, więc
    // generują się osobno wyżej (zawsze, nie tylko gdy punkt ma koordynaty) —
    // stąd bezpośrednio ścieżka lokalna zamiast realneRysunki/spróbujWygenerowac...
    const assetLokalny = (sciezka, placeholderKlucz) => (sciezka
      ? { zrodlo: "generowany", plik: sciezka }
      : { zrodlo: "placeholder_punkt1", plik: placeholdery[placeholderKlucz] });

    punktyFixture.push({
      id: punkt.id,
      numer: punkt.numer,
      typ: punkt.typ,
      nazwa: punkt.nazwa,
      miejscowosc: punkt.miejscowosc,
      metadanePomiaru: {
        dataPomiaru: punkt.metadanePomiaru.dataPomiaru,
        dzienTygodnia: punkt.metadanePomiaru.dzienTygodnia,
        // spec v2 (krok 4 tego UI) nie zbiera czasu rozpoczęcia/zakończenia —
        // wszystkie dotychczasowe pomiary to pełna doba, przyjmujemy jako domyślne.
        czasRozpoczecia: "00:00",
        czasZakonczenia: "23:59",
        warunkiAtmosferyczne: punkt.metadanePomiaru.warunkiAtmosferyczne,
        statusPrzydatnosci: punkt.metadanePomiaru.statusPrzydatnosci,
      },
      wloty: punkt.wloty.map((w, i) => ({ nrWlotu: i + 1, opis: w.opis || w.id, kierunek: w.id, uwagi: w.uwagi || "-" })),
      geometriaRegularna: punkt.geometriaRegularna,
      assets: {
        mapkaLokalizacji: asset(null, "mapkaLokalizacji", "mapkaLokalizacji"),
        schematSkrzyzowania: asset(sciezkaWgrana("schematSkrzyzowania"), "schematSkrzyzowania", "schematSkrzyzowania"),
        wykresPogoda: asset(null, "wykresPogoda", "wykresPogoda"),
        zdjecieKamery: asset(sciezkaWgrana("zdjecieKamery"), "zdjecieKamery"),
        sankeySDR: asset(null, "sankeySDR", "sankeySDR"),
        // spec §5.7 dot. placeholderów: bez realnego generatora UPC reużywałby
        // plik sankeySDR — ale UPC MA teraz własny generator (patrz wyżej), więc
        // fallback na placeholder sankeySDR działa tylko gdy oba się nie udały.
        sankeyUPC: asset(null, "sankeySDR", "sankeyUPC"),
        sankeyPoranny: asset(null, "sankeyPoranny", "sankeyPoranny"),
        sankeyPopoludniowy: asset(null, "sankeyPopoludniowy", "sankeyPopoludniowy"),
        godzinowaRelacje: assetLokalny(sciezkaGodzinowaRelacje, "godzinowaRelacje"),
        godzinowaCiezkie: assetLokalny(sciezkaGodzinowaCiezkie, "godzinowaCiezkie"),
        profilKategorie: { zrodlo: "generowany", plik: sciezkaProfilKategorie },
        wykresPoryDoby: { zrodlo: "generowany", plik: sciezkaPoryDoby },
      },
      teksty: punkt.teksty,
      obliczenia: punkt.obliczenia,
      przypisyJakosciDanych: punkt.przypisyJakosciDanych,
    });
  }

  // Wykresy zbiorcze rozdziału 4 "Podsumowanie" — tylko gdy analiza łączna ma
  // sens (N > 1, patrz budujPodsumowanie w budujRaport.js). Dwa różne warianty
  // zależnie od progu: tryb pełny (N <= próg) dostaje zestawienie SDR + szczyty
  // per punkt, tryb zagregowany (N > próg) dostaje histogram zamiast wykresu
  // 1 słupek/punkt (nieczytelny przy dużym N).
  const N = punktyFixture.length;
  const prog = projekt.metadaneProjektu.progAnalizyLacznej || 15;
  if (N > 1) {
    const tmpProjektDlaWykresow = path.join(dirBuild, "_projekt_wykresy.json");
    fs.writeFileSync(tmpProjektDlaWykresow, JSON.stringify({ punkty: punktyFixture }));
    if (N <= prog) {
      await generujObraz(["generuj_wykres_zestawienie_sdr.py", tmpProjektDlaWykresow, path.join(dirAssets, "r_zestawienie_sdr.png")]);
      await generujObraz(["generuj_wykres_szczyty_projektu.py", tmpProjektDlaWykresow, path.join(dirAssets, "r_szczyty_projektu.png")]);
    } else {
      await generujObraz(["generuj_wykres_histogram_sdr.py", tmpProjektDlaWykresow, path.join(dirAssets, "r_histogram_sdr.png")]);
    }
    fs.unlinkSync(tmpProjektDlaWykresow);
  }

  const fixture = { metadaneProjektu: projekt.metadaneProjektu, podsumowanie: projekt.podsumowanie, punkty: punktyFixture };
  const sciezkaFixture = path.join(dirBuild, "fixture.json");
  fs.writeFileSync(sciezkaFixture, JSON.stringify(fixture, null, 2));

  console.log("Buduję dokument .docx...");
  const sciezkaDocx = path.join(dirBuild, "raport.docx");
  await new Promise((resolve, reject) => {
    // spawn (nie execFile) + stdio na żywo do konsoli serwera — execFile
    // buforuje stdout/stderr i oddaje je dopiero po zakończeniu procesu, więc
    // przy realnie długim/zawieszonym budowaniu docx konsola milczała mimo
    // że dziecko cały czas mogło coś logować (patrz [generuj_docx] w kodzie).
    const dziecko = spawn(
      process.execPath,
      [path.join(DOCX_DIR, "generuj_docx.js"), sciezkaFixture, sciezkaDocx, LOGO_DOMYSLNE, dirBuild],
    );
    let stderrTresc = "";
    dziecko.stdout.on("data", (d) => process.stdout.write(d));
    dziecko.stderr.on("data", (d) => { process.stderr.write(d); stderrTresc += d; });
    dziecko.on("error", reject);
    dziecko.on("close", (kod) => (kod === 0 ? resolve() : reject(new Error(stderrTresc || `generuj_docx.js zakończył się kodem ${kod}`))));
  });
  console.log("Raport gotowy ✓");

  return sciezkaDocx;
}

// --- Szkielet projektu (krok 1) --------------------------------------------

function nowyPunktSzkielet(numer) {
  return {
    id: `P${numer}`,
    numer,
    typ: "skrzyzowanie",
    nazwa: "",
    miejscowosc: "",
    lokalizacja: null,
    kamery: [],
    metadanePomiaru: {
      dataPomiaru: "",
      dzienTygodnia: "",
      warunkiAtmosferyczne: "",
      statusPrzydatnosci: "akceptowalne",
      zaklocenia: null,
    },
    geometriaRegularna: true,
    bramkiMapping: {},
    wloty: [],
    qc: null,
    assets: {},
    obliczenia: null,
    przypisyJakosciDanych: [],
    teksty: domyslneTeksty(POLA_TEKSTOW_PUNKTU),
  };
}

// Projekt zawsze startuje z 1 punktem — kolejne dochodzą przyciskiem "+ Dodaj
// punkt" w UI (POST .../punkty), liczba punktów nie jest już z góry deklarowana.
function zbudujSzkielet({ nazwaProjektu, zamawiajacy, dataOd, dataDo, linkWytyczneGDDKiA }) {
  return {
    metadaneProjektu: {
      nazwaProjektu: nazwaProjektu || "",
      zamawiajacy: zamawiajacy || "",
      dataOd: dataOd || "",
      dataDo: dataDo || "",
      progAnalizyLacznej: 15,
      linkWytyczneGDDKiA: linkWytyczneGDDKiA || "https://www.gov.pl/attachment/0e35b003-0dc0-43d1-86d0-62f252c6a280",
      dataSporzadzenia: "",
      sporzadzil: "",
      emailOdpowiedzialny: "",
    },
    punkty: [nowyPunktSzkielet(1)],
    podsumowanie: { teksty: domyslneTeksty(POLA_TEKSTOW_PODSUMOWANIA) },
  };
}

// --- HTTP: statyka + API -----------------------------------------------------

function wyslijJson(res, kod, dane) {
  const bufor = Buffer.from(JSON.stringify(dane));
  res.writeHead(kod, { "Content-Type": MIME[".json"], "Content-Length": bufor.length });
  res.end(bufor);
}

function wczytajBodyJson(req) {
  return new Promise((resolve, reject) => {
    let dane = "";
    req.on("data", (chunk) => {
      dane += chunk;
      if (dane.length > 20 * 1024 * 1024) req.destroy(); // 20 MB, dość na duże CSV
    });
    req.on("end", () => {
      if (!dane) return resolve({});
      try { resolve(JSON.parse(dane)); } catch (e) { reject(e); }
    });
    req.on("error", reject);
  });
}

function obsluzStatyke(req, res) {
  const sciezka = req.url === "/" ? "/index.html" : req.url;
  const plik = path.join(PUBLIC_DIR, path.normalize(sciezka).replace(/^(\.\.[/\\])+/, ""));
  if (!plik.startsWith(PUBLIC_DIR) || !fs.existsSync(plik) || fs.statSync(plik).isDirectory()) {
    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("Nie znaleziono");
    return;
  }
  const rozszerzenie = path.extname(plik);
  res.writeHead(200, { "Content-Type": MIME[rozszerzenie] || "application/octet-stream" });
  fs.createReadStream(plik).pipe(res);
}

const serwer = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);

    if (url.pathname === "/api/projekty" && req.method === "GET") {
      return wyslijJson(res, 200, listaProjektow());
    }

    if (url.pathname === "/api/projekty" && req.method === "POST") {
      const body = await wczytajBodyJson(req);
      const id = idProjektu(body.nazwaProjektu);
      const projekt = zbudujSzkielet(body);
      projekt._id = id;
      zapiszProjekt(id, projekt);
      return wyslijJson(res, 201, { id, projekt });
    }

    const dopasowanieProjekt = url.pathname.match(/^\/api\/projekty\/([^/]+)$/);
    if (dopasowanieProjekt && req.method === "GET") {
      const projekt = wczytajProjekt(dopasowanieProjekt[1]);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      return wyslijJson(res, 200, projekt);
    }
    if (dopasowanieProjekt && req.method === "PUT") {
      const id = dopasowanieProjekt[1];
      if (!wczytajProjekt(id)) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      const projekt = await wczytajBodyJson(req);
      projekt._id = id;
      zapiszProjekt(id, projekt);
      return wyslijJson(res, 200, projekt);
    }

    const dopasowaniePogoda = url.pathname.match(/^\/api\/projekty\/([^/]+)\/punkty\/(\d+)\/wykryj-pogode$/);
    if (dopasowaniePogoda && req.method === "POST") {
      const [, id, numerStr] = dopasowaniePogoda;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      const punkt = projekt.punkty.find((p) => p.numer === Number(numerStr));
      if (!punkt) return wyslijJson(res, 404, { blad: "Nie znaleziono punktu" });
      if (!punkt.lokalizacja) return wyslijJson(res, 400, { blad: "Brak współrzędnych (krok 2)" });
      if (!punkt.metadanePomiaru.dataPomiaru) return wyslijJson(res, 400, { blad: "Brak daty pomiaru (krok 4)" });
      try {
        const warunki = await wykryjPogode(punkt.lokalizacja.lat, punkt.lokalizacja.lng, punkt.metadanePomiaru.dataPomiaru);
        punkt.metadanePomiaru.warunkiAtmosferyczne = warunki;
        zapiszProjekt(id, projekt);
        return wyslijJson(res, 200, { warunkiAtmosferyczne: warunki });
      } catch (e) {
        return wyslijJson(res, 502, { blad: e.message });
      }
    }

    const dopasowanieNowyPunkt = url.pathname.match(/^\/api\/projekty\/([^/]+)\/punkty$/);
    if (dopasowanieNowyPunkt && req.method === "POST") {
      const [, id] = dopasowanieNowyPunkt;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      const numer = Math.max(0, ...projekt.punkty.map((p) => p.numer)) + 1;
      const punkt = nowyPunktSzkielet(numer);
      projekt.punkty.push(punkt);
      zapiszProjekt(id, projekt);
      return wyslijJson(res, 201, { punkt });
    }

    const dopasowanieUsunPunkt = url.pathname.match(/^\/api\/projekty\/([^/]+)\/punkty\/(\d+)$/);
    if (dopasowanieUsunPunkt && req.method === "DELETE") {
      const [, id, numerStr] = dopasowanieUsunPunkt;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      const numer = Number(numerStr);
      const punkt = projekt.punkty.find((p) => p.numer === numer);
      if (!punkt) return wyslijJson(res, 404, { blad: "Nie znaleziono punktu" });

      projekt.punkty = projekt.punkty.filter((p) => p.numer !== numer);
      zapiszProjekt(id, projekt);

      // Posprzątaj pliki punktu na dysku (CSV kamer, uploadowane assety) —
      // nieusunięcie ich nie zepsułoby niczego (kolejne punkty mają inny
      // idPunktu), ale zostawiałoby sierociny na dysku bez potrzeby.
      const idPunktu = punkt.id || `P${punkt.numer}`;
      for (const dir of [
        path.join(PROJEKTY_DIR, id, "zrodla", idPunktu),
        path.join(PROJEKTY_DIR, id, "assets", idPunktu),
      ]) {
        if (fs.existsSync(dir)) fs.rmSync(dir, { recursive: true, force: true });
      }

      return wyslijJson(res, 200, { punkty: projekt.punkty });
    }

    const dopasowanieKamera = url.pathname.match(/^\/api\/projekty\/([^/]+)\/punkty\/(\d+)\/kamery$/);
    if (dopasowanieKamera && req.method === "POST") {
      const [, id, numerStr] = dopasowanieKamera;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      projekt._id = id;
      const { nazwaPliku, tresc } = await wczytajBodyJson(req);
      if (!nazwaPliku || !tresc) return wyslijJson(res, 400, { blad: "Wymagane: nazwaPliku, tresc" });
      try {
        const wynik = await dodajKamere(projekt, Number(numerStr), nazwaPliku, tresc);
        zapiszProjekt(id, projekt);
        return wyslijJson(res, 201, { ...wynik, kamery: projekt.punkty.find((p) => p.numer === Number(numerStr)).kamery });
      } catch (e) {
        return wyslijJson(res, 400, { blad: e.message });
      }
    }

    const dopasowanieBramki = url.pathname.match(/^\/api\/projekty\/([^/]+)\/punkty\/(\d+)\/dane-mapowania$/);
    if (dopasowanieBramki && req.method === "GET") {
      const [, id, numerStr] = dopasowanieBramki;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      const punkt = projekt.punkty.find((p) => p.numer === Number(numerStr));
      if (!punkt) return wyslijJson(res, 404, { blad: "Nie znaleziono punktu" });
      const { bramki, relacje } = efektywneDanePunktu(punkt);
      return wyslijJson(res, 200, { bramki, relacje, wlotyMozliwe: WLOTY_MOZLIWE });
    }

    const dopasowanieMapowanie = url.pathname.match(/^\/api\/projekty\/([^/]+)\/punkty\/(\d+)\/mapowanie$/);
    if (dopasowanieMapowanie && req.method === "PUT") {
      const [, id, numerStr] = dopasowanieMapowanie;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      const punkt = projekt.punkty.find((p) => p.numer === Number(numerStr));
      if (!punkt) return wyslijJson(res, 404, { blad: "Nie znaleziono punktu" });
      const { bramkiMapping, geometriaRegularna, wloty } = await wczytajBodyJson(req);
      punkt.bramkiMapping = bramkiMapping || {};
      punkt.geometriaRegularna = Boolean(geometriaRegularna);
      punkt.wloty = wloty || [];
      punkt.qc = zwalidujMapowanie(punkt);
      zapiszProjekt(id, projekt);
      return wyslijJson(res, 200, { qc: punkt.qc, wloty: punkt.wloty });
    }

    const dopasowanieAsset = url.pathname.match(/^\/api\/projekty\/([^/]+)\/punkty\/(\d+)\/asset$/);
    if (dopasowanieAsset && req.method === "POST") {
      const [, id, numerStr] = dopasowanieAsset;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      projekt._id = id;
      const { pole, nazwaPliku, tresc } = await wczytajBodyJson(req);
      if (!pole || !nazwaPliku || !tresc) return wyslijJson(res, 400, { blad: "Wymagane: pole, nazwaPliku, tresc" });
      try {
        zapiszAsset(projekt, Number(numerStr), pole, nazwaPliku, tresc);
        zapiszProjekt(id, projekt);
        return wyslijJson(res, 201, { assets: projekt.punkty.find((p) => p.numer === Number(numerStr)).assets });
      } catch (e) {
        return wyslijJson(res, 400, { blad: e.message });
      }
    }

    const dopasowanieAssetPlik = url.pathname.match(/^\/api\/projekty\/([^/]+)\/assets\/(.+)$/);
    if (dopasowanieAssetPlik && req.method === "GET") {
      const [, id, sciezkaWzgledna] = dopasowanieAssetPlik;
      const dirAssets = path.join(PROJEKTY_DIR, id, "assets");
      const plik = path.join(dirAssets, path.normalize(decodeURIComponent(sciezkaWzgledna)).replace(/^(\.\.[/\\])+/, ""));
      if (!plik.startsWith(dirAssets) || !fs.existsSync(plik)) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        return res.end("Nie znaleziono");
      }
      const typObrazka = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg" }[path.extname(plik)] || "application/octet-stream";
      res.writeHead(200, { "Content-Type": typObrazka });
      return fs.createReadStream(plik).pipe(res);
    }

    const dopasowanieOblicz = url.pathname.match(/^\/api\/projekty\/([^/]+)\/punkty\/(\d+)\/oblicz$/);
    if (dopasowanieOblicz && req.method === "POST") {
      const [, id, numerStr] = dopasowanieOblicz;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      const punkt = projekt.punkty.find((p) => p.numer === Number(numerStr));
      if (!punkt) return wyslijJson(res, 404, { blad: "Nie znaleziono punktu" });
      if (punkt.kamery.length === 0) return wyslijJson(res, 400, { blad: "Brak wgranych danych źródłowych (krok 3)" });
      if (!punkt.qc || punkt.qc.bramkiNiezmapowane.length > 0) {
        return wyslijJson(res, 400, { blad: "Najpierw dokończ i zwaliduj mapowanie kierunków (krok 5) — są niezmapowane bramki" });
      }
      try {
        const { obliczenia, przypisyJakosciDanych } = await uruchomSilnik(sciezkaProjektu(id), Number(numerStr));
        punkt.obliczenia = obliczenia;
        punkt.przypisyJakosciDanych = przypisyJakosciDanych;
        // ponytail: kategorieWyzerowaneGodzinowo zawsze [] — detektor tej anomalii
        // to osobne zadanie badawcze (spec §8, "do zbadania w pipeline źródłowym"),
        // nie zaimplementowany. Bramka 7b więc dziś przepuszcza zawsze poza
        // literami niezmapowanymi z kroku 5b — dociągnąć detektor gdy powstanie.
        punkt.qc = { ...punkt.qc, sumaKontrolna: { ok: true, roznica: 0 }, kategorieWyzerowaneGodzinowo: [], status: "akceptacja" };
        zapiszProjekt(id, projekt);
        return wyslijJson(res, 200, { obliczenia, przypisyJakosciDanych, qc: punkt.qc });
      } catch (e) {
        return wyslijJson(res, 500, { blad: e.message });
      }
    }

    const dopasowanieGenerujTeksty = url.pathname.match(/^\/api\/projekty\/([^/]+)\/punkty\/(\d+)\/generuj-teksty$/);
    if (dopasowanieGenerujTeksty && req.method === "POST") {
      const [, id, numerStr] = dopasowanieGenerujTeksty;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      const punkt = projekt.punkty.find((p) => p.numer === Number(numerStr));
      if (!punkt) return wyslijJson(res, 404, { blad: "Nie znaleziono punktu" });
      if (!punkt.obliczenia) return wyslijJson(res, 400, { blad: "Najpierw uruchom obliczenia (krok 7)" });
      try {
        const teksty = await new Promise((resolve, reject) => {
          execFile(
            pythonBin(),
            ["-m", "panel.silnik.uruchom_teksty_dla_punktu", sciezkaProjektu(id), numerStr],
            { cwd: REPO_ROOT, maxBuffer: 10 * 1024 * 1024, env: envPython() },
            (err, stdout, stderr) => (err ? reject(new Error(stderr || err.message)) : resolve(JSON.parse(stdout))),
          );
        });
        punkt.teksty = teksty;
        zapiszProjekt(id, projekt);
        return wyslijJson(res, 200, { teksty });
      } catch (e) {
        return wyslijJson(res, 500, { blad: e.message });
      }
    }

    // Krok 10 — odpowiednik krok9 "generuj-teksty", ale dla tekstów zbiorczych
    // rozdziału 4 (Wprowadzenie/Porównanie punktów). Czysty JS (analizaLaczna.js,
    // ta sama logika co budujRaport.js), bez wołania Pythona — dane (obliczenia
    // per punkt) już są w projekt.json, nic więcej nie trzeba liczyć na nowo.
    const dopasowanieGenerujPodsumowanie = url.pathname.match(/^\/api\/projekty\/([^/]+)\/generuj-podsumowanie$/);
    if (dopasowanieGenerujPodsumowanie && req.method === "POST") {
      const [, id] = dopasowanieGenerujPodsumowanie;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      if (projekt.punkty.length <= 1) {
        return wyslijJson(res, 400, { blad: "Analiza łączna wymaga co najmniej 2 punktów pomiarowych" });
      }
      const brakObliczen = projekt.punkty.filter((p) => !p.obliczenia).map((p) => p.id);
      if (brakObliczen.length > 0) {
        return wyslijJson(res, 400, { blad: `Najpierw uruchom obliczenia (krok 7) dla: ${brakObliczen.join(", ")}` });
      }
      try {
        const tekstWprowadzenie = generujTekstWprowadzenie(projekt);
        const tekstPorownanie = generujTekstPorownanie(projekt);
        projekt.podsumowanie.teksty.tekstWprowadzenie = tekstWprowadzenie;
        projekt.podsumowanie.teksty.tekstPorownanie = tekstPorownanie;
        zapiszProjekt(id, projekt);
        return wyslijJson(res, 200, { tekstWprowadzenie, tekstPorownanie });
      } catch (e) {
        return wyslijJson(res, 500, { blad: e.message });
      }
    }

    const dopasowanieGeneruj = url.pathname.match(/^\/api\/projekty\/([^/]+)\/generuj-raport$/);
    if (dopasowanieGeneruj && req.method === "POST") {
      const [, id] = dopasowanieGeneruj;
      const projekt = wczytajProjekt(id);
      if (!projekt) return wyslijJson(res, 404, { blad: "Nie znaleziono projektu" });
      projekt._id = id;
      try {
        await zbudujRaport(projekt);
        const dirBuild = path.join(PROJEKTY_DIR, id, "build");
        const zalaczniki = projekt.punkty
          .map((p) => `wynik_tabele_Punkt${p.numer}_${p.id}.xlsx`)
          .filter((nazwa) => fs.existsSync(path.join(dirBuild, nazwa)))
          .map((nazwa) => ({ nazwa, url: `/api/projekty/${id}/wynik-tabele/${nazwa}` }));
        const raportInfo = {
          url: `/api/projekty/${id}/raport.docx`,
          zalaczniki,
          wygenerowanoO: new Date().toISOString(),
        };
        // Zapisane do projekt.json (nie tylko zwrócone w odpowiedzi) — inaczej
        // linki do pobrania znikały po odświeżeniu strony, mimo że pliki
        // realnie istniały na dysku w build/.
        projekt.raportInfo = raportInfo;
        zapiszProjekt(id, projekt);
        return wyslijJson(res, 200, { ok: true, ...raportInfo });
      } catch (e) {
        return wyslijJson(res, 500, { blad: e.message });
      }
    }

    const dopasowanieRaport = url.pathname.match(/^\/api\/projekty\/([^/]+)\/raport\.docx$/);
    if (dopasowanieRaport && req.method === "GET") {
      const [, id] = dopasowanieRaport;
      const sciezkaDocx = path.join(PROJEKTY_DIR, id, "build", "raport.docx");
      if (!fs.existsSync(sciezkaDocx)) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        return res.end("Raport jeszcze nie wygenerowany");
      }
      res.writeHead(200, {
        "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "Content-Disposition": `attachment; filename="Raport_${id}.docx"`,
      });
      return fs.createReadStream(sciezkaDocx).pipe(res);
    }

    const dopasowanieXlsx = url.pathname.match(/^\/api\/projekty\/([^/]+)\/wynik-tabele\/([^/]+\.xlsx)$/);
    if (dopasowanieXlsx && req.method === "GET") {
      const [, id, nazwaPliku] = dopasowanieXlsx;
      const sciezkaXlsx = path.join(PROJEKTY_DIR, id, "build", nazwaPliku);
      if (!sciezkaXlsx.startsWith(path.join(PROJEKTY_DIR, id, "build")) || !fs.existsSync(sciezkaXlsx)) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        return res.end("Nie znaleziono");
      }
      res.writeHead(200, {
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": `attachment; filename="${nazwaPliku}"`,
      });
      return fs.createReadStream(sciezkaXlsx).pipe(res);
    }

    const dopasowanieZip = url.pathname.match(/^\/api\/projekty\/([^/]+)\/pobierz-wszystko\.zip$/);
    if (dopasowanieZip && req.method === "GET") {
      const [, id] = dopasowanieZip;
      const dirBuild = path.join(PROJEKTY_DIR, id, "build");
      const sciezkaDocx = path.join(dirBuild, "raport.docx");
      if (!fs.existsSync(sciezkaDocx)) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        return res.end("Raport jeszcze nie wygenerowany");
      }
      const projekt = wczytajProjekt(id);
      const pliki = [{ nazwa: `Raport_${id}.docx`, dane: fs.readFileSync(sciezkaDocx) }];
      for (const nazwa of (projekt.raportInfo?.zalaczniki || []).map((z) => z.nazwa)) {
        const sciezka = path.join(dirBuild, nazwa);
        if (fs.existsSync(sciezka)) pliki.push({ nazwa, dane: fs.readFileSync(sciezka) });
      }
      const zip = budujZip(pliki);
      res.writeHead(200, {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="Raport_${id}_wszystko.zip"`,
      });
      return res.end(zip);
    }

    if (req.method === "GET") return obsluzStatyke(req, res);

    wyslijJson(res, 404, { blad: "Nieznana trasa" });
  } catch (e) {
    console.error(e);
    wyslijJson(res, 500, { blad: e.message });
  }
});

serwer.listen(PORT, () => {
  console.log(`Panel raportów: http://localhost:${PORT}`);
});
