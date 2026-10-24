@echo off
rem batch.bat - zelfde als batch.ps1, voor cmd.exe.
rem > ⚠️ Niet uitgevoerd: geen Windows/AutoCAD op deze Mac
rem Gebruik: batch.bat C:\tekeningen
setlocal enabledelayedexpansion
set "ACCORE=C:\Program Files\Autodesk\AutoCAD 2025\accoreconsole.exe"
set "SCR=%~dp0rcs-batch.scr"
set "LOGS=%~dp0logs"
if "%~1"=="" (echo Gebruik: %~nx0 ^<map met dwg^> & exit /b 2)
if not exist "%LOGS%" mkdir "%LOGS%"
set FOUTEN=0
for %%F in ("%~f1\*.dwg") do (
    "%ACCORE%" /i "%%~fF" /s "%SCR%" /l en-US > "%LOGS%\%%~nF.log" 2>&1
    set CODE=!errorlevel!
    echo %date% %time%	!CODE!	%%~fF>> "%LOGS%\batch.tsv"
    if not "!CODE!"=="0" set /a FOUTEN+=1
)
exit /b %FOUTEN%
