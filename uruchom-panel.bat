@echo off
setlocal

cd /d "%~dp0"

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

if not exist "panel\docx\node_modules" (
  echo Brak paczek npm dla generatora dokumentow - instaluje teraz...
  pushd panel\docx
  call npm install
  if errorlevel 1 (
    popd
    echo BLAD: nie znaleziono komendy "npm". Zainstaluj Node.js ^(instaluje npm razem z nim^)
    echo i uruchom ten plik ponownie.
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
