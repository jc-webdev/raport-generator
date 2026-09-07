# Instalacja i uruchomienie panelu na Windows

Panel to zwykła aplikacja Node.js (serwer + strona w przeglądarce) plus
kilka skryptów Pythona do generowania map i wykresów. Nie wymaga Dockera,
instalacji z uprawnieniami administratora ani LibreOffice.

## Czego potrzebujesz z tego archiwum

Skopiuj na dysk trzy foldery **razem, jako rodzeństwo w jednym wspólnym
folderze** (np. `C:\Panel-raportow\`):

```
Panel-raportow\
├── panel\
├── generator-mapek\
└── Generaotr-mapy-skrzyzowania\
```

Reszta plików w archiwum (`drogi\`, `Sankey\`, `dane-do-raportu\`, luźne
`.docx`/`.png`/`.md`) to materiały historyczne — nie są potrzebne do
działania panelu, możesz je pominąć.

## Krok 1 — Node.js

1. Pobierz instalator LTS (wersja 18 lub nowsza) ze strony nodejs.org.
2. W instalatorze wybierz **"Install just for me"** — nie wymaga admina.
3. Sprawdź w `cmd`: `node --version` powinno wypisać numer wersji.

Jeśli instalator jest zablokowany przez politykę firmy: pobierz sekcję
"Other Downloads" → **Windows Binary (.zip)** ze strony nodejs.org.
**`uruchom-panel.bat` sam wykrywa taki "portable" Node** — wystarczy
wypakować całą zawartość pobranego .zip do nowego folderu **`node-portable`**
obok pliku `uruchom-panel.bat` (tak, żeby istniała ścieżka
`node-portable\node.exe`). Nie trzeba nic dodawać do PATH ręcznie.

## Krok 2 — Python

1. Pobierz instalator **Python 3.10, 3.11 lub 3.12** (nie 3.13+) ze strony
   python.org — ta wersja ma pewne gotowe pakiety binarne dla geopandas/osmnx
   na Windows, dzięki czemu instalacja obejdzie się bez kompilatora.
2. W instalatorze zaznacz **"Install for me only"** oraz **"Add python.exe
   to PATH"**.
3. Sprawdź w `cmd`: `python --version`.

## Krok 3 — pierwsze uruchomienie

W folderze `Panel-raportow\` kliknij dwukrotnie **`uruchom-panel.bat`**.

Skrypt przy pierwszym uruchomieniu:
- utworzy środowisko Python w `generator-mapek\venv\`,
- zainstaluje wszystkie potrzebne biblioteki (pandas, matplotlib, openpyxl,
  osmnx, geopandas...) — to może potrwać kilka minut,
- doinstaluje pakiet npm potrzebny do budowania plików .docx (`panel\docx\node_modules`),
- uruchomi serwer panelu.

Gdy w oknie konsoli pojawi się `Panel raportów: http://localhost:4173`,
otwórz tę stronę w przeglądarce.

Przy **kolejnych** uruchomieniach ten sam plik `.bat` już tylko odpala
serwer (widzi gotowe środowisko i pomija instalację) — normalnie powinno to
zająć góra kilka sekund.

Aby zatrzymać serwer: zamknij okno konsoli albo wciśnij `Ctrl+C`.

## Jeśli coś nie zadziała

**Instalacja `geopandas`/`osmnx` się wysypuje** — najczęściej to za nowa lub
za stara wersja Pythona. Odinstaluj i zainstaluj ponownie w wersji 3.10-3.12,
usuń folder `generator-mapek\venv` i uruchom `uruchom-panel.bat` od nowa.

**`python` albo `node` nie jest rozpoznawane jako polecenie** — instalator
nie dodał programu do PATH. Zainstaluj ponownie i koniecznie zaznacz opcję
"Add to PATH" (Python) / upewnij się, że zaznaczona jest ścieżka (Node —
domyślnie robi to sam instalator .msi).

**Port 4173 zajęty** — zamknij inny program, który go używa, albo zmień
port: w `cmd`, przed uruchomieniem, wpisz `set PORT=5000` i dopiero wtedy
odpal `uruchom-panel.bat` (panel wystartuje na porcie 5000).

**Środowisko Python jest w innym miejscu niż `generator-mapek\venv`** —
ustaw zmienną `PYTHON_BIN` na pełną ścieżkę do `python.exe` przed
uruchomieniem, np. `set PYTHON_BIN=D:\srodowiska\panel\Scripts\python.exe`.

## Ręczna instalacja (bez pliku .bat)

Jeśli wolisz zrobić to krok po kroku samodzielnie, w `cmd` w folderze
`Panel-raportow\`:

```
python -m venv generator-mapek\venv
generator-mapek\venv\Scripts\pip install -r generator-mapek\requirements.txt
generator-mapek\venv\Scripts\pip install -r panel\requirements.txt
cd panel\docx
npm install
cd ..\ui
node server.js
```

Potem otwórz http://localhost:4173 w przeglądarce.
