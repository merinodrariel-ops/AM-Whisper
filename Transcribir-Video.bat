@echo off
chcp 65001 > nul
title AM VIDEO TRANSCRIPT — Dr. Ariel Merino
cd /d "%~dp0"

cls
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 🎬  AM VIDEO TRANSCRIPT — Dr. Ariel Merino (Windows)
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 💡 INSTRUCCIONES:
echo 1. Arrastrá el archivo de video a esta ventana.
echo 2. Presioná la tecla ENTER.
echo.
set /p inputPath="👇 Arrastrá el video aquí: "

rem Limpiar comillas si las hay
set "videoPath=%inputPath:"=%"

if "%videoPath%"=="" (
    echo ❌ No se ingresó ningún archivo.
    timeout /t 3 > nul
    exit /b 1
)

echo.
echo 🚀 Iniciando transcripción...
echo ------------------------------------------------------------

node video-transcript.mjs "%videoPath%"

echo ------------------------------------------------------------
echo 🏁 Proceso finalizado.
pause
exit /b 0
