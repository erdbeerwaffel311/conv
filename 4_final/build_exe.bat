@echo off
setlocal enabledelayedexpansion
title Universal Media Converter - Windows Build

echo ========================================================
echo   Universal Media Converter - Windows EXE Builder
echo ========================================================
echo.

cd /d "%~dp0\.."

REM Suche nach Python-Befehl (python, py oder python3)
set "PY_CMD="

where python >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=python"
)

if "%PY_CMD%"=="" (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=py -3"
    )
)

if "%PY_CMD%"=="" (
    where python3 >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=python3"
    )
)

REM Falls im PATH nicht gefunden, in typischen Installationsordnern suchen
if "%PY_CMD%"=="" (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        if exist "%%D\python.exe" (
            set "PY_CMD=%%D\python.exe"
        )
    )
)

if "%PY_CMD%"=="" (
    echo [FEHLER] Python wurde auf diesem Computer nicht gefunden!
    echo.
    echo Bitte installiere Python:
    echo 1. Oeffne im Browser: https://www.python.org/downloads/
    echo 2. Lade den Windows-Installer herunter.
    echo 3. WICHTIG: Setze beim Starten des Installers das Haekchen bei:
    echo    "Add python.exe to PATH"
    echo.
    echo Druecke eine beliebige Taste zum Beenden...
    pause >nul
    exit /b 1
)

echo Python gefunden: %PY_CMD%
echo Starte Build-Skript...
echo.

%PY_CMD% 4_final\build_windows_exe.py

if errorlevel 1 (
    echo.
    echo ========================================================
    echo [FEHLER] Der Build-Prozess wurde mit einem Fehler beendet.
    echo Bitte lies die Fehlermeldung oben.
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo   Build erfolgreich abgeschlossen!
    echo   App-Ordner: 4_final\dist_windows\UniversalMediaConverter\
    echo   Setup-Datei: 4_final\UniversalMediaConverter_Setup.exe
    echo ========================================================
)

echo.
echo Druecke eine beliebige Taste, um dieses Fenster zu schliessen...
pause >nul
