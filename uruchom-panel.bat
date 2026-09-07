@echo off
setlocal

cd /d "%~dp0"

rem Node.exe "portable" (pobrany jako .zip, nie instalator) nie trafia do
rem PATH systemowego, wiec zwykle "node" nie jest rozpoznawane w tym oknie.
rem Jesli node nie jest widoczny globalnie, szukamy go w folderze
rem node-portable\ obok tego pliku .bat (tam wypakuj zawartosc pobranego
rem .zip z nodejs.org - powinien tam byc plik node.exe) i dodajemy go do
rem PATH tylko na czas dzialania tego okna.
where node >nul 2>nul
if errorlevel 1 (
  if exist "node-portable\node.exe" (
    echo Uzywam Node.js z folderu node-portable\
    set "PATH=%~dp0node-portable;%PATH%"
  ) else (
    echo BLAD: nie znaleziono polecenia "node".
    echo.
    echo Jesli masz Node.js pobrany jako .zip ^(portable, nie instalator^):
    echo   1. Wypakuj cala zawartosc tego .zip do nowego folderu
    echo      "node-portable" obok tego pliku .bat, tak zeby istnialo:
    echo      %~dp0node-portable\node.exe
    echo   2. Uruchom ten plik ponownie.
    echo.
    echo Albo zainstaluj Node.js instalatorem ^(zaznacz dodanie do PATH^)
    echo ze strony nodejs.org.
    pause
    exit /b 1
  )
)

if not exist "generator-mapek\venv\Scripts\python.exe" (
  echo Brak srodowiska Python - tworze je teraz w generator-mapek\venv ...
  python -m venv generator-mapek\venv
  if errorlevel 1 (
    echo BLAD: nie znaleziono komendy "python". Zainstaluj Python 3.10-3.12
    echo ^(zaznacz "Add to PATH" w instalatorze^) i uruchom ten plik ponownie.
    pause
    exit /b 1
  )

  echo Instaluje zaleznosci Python - to moze potrwac kilka minut...
  call generator-mapek\venv\Scripts\pip install -r generator-mapek\requirements.txt
  call generator-mapek\venv\Scripts\pip install -r panel\requirements.txt
)

rem Sprawdzamy konkretnie folder pakietu "docx", nie samo istnienie
rem node_modules - jesli poprzednia instalacja padla w polowie (np. przez
rem siec/proxy), node_modules mogl zostac utworzony pusty/niepelny i bylby
rem cicho pomijany przy kolejnych uruchomieniach.
if not exist "panel\docx\node_modules\docx" (
  echo Brak paczek npm dla generatora dokumentow - instaluje teraz...
  pushd panel\docx
  call npm install
  if errorlevel 1 (
    popd
    echo BLAD: instalacja paczek npm nie powiodla sie ^(patrz komunikat powyzej^).
    echo Najczestsza przyczyna: brak dostepu do rejestru npm przez firmowa
    echo siec/proxy - npm ma WLASNA konfiguracje proxy, niezalezna od zmiennych
    echo HTTP_PROXY/HTTPS_PROXY. Sprawdz: npm config get proxy
    echo Po naprawieniu przyczyny uruchom ten plik ponownie.
    pause
    exit /b 1
  )
  popd
)

echo.
echo Uruchamiam serwer panelu...
echo Otworz w przegladarce:  http://localhost:4173
echo Aby zatrzymac serwer: zamknij to okno albo wcisnij Ctrl+C
echo.

cd panel\ui
node server.js

pause
