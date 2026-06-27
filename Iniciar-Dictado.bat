@echo off
chcp 65001 > nul
title AM VOICE DICTATION — Dr. Ariel Merino

:: Verificar privilegios de administrador
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run
) else (
    goto :elevate
)

:elevate
echo Requeriendo permisos de Administrador para simular teclado...
powershell -Command "Start-Process -FilePath '%0' -Verb RunAs"
exit /b

:run
cd /d "%~dp0"
cls
python am-whisper-dictado.py
pause
