@echo off
chcp 65001 > nul
title CAPTURADOR DE TECLAS — AM-Whisper
cd /d "%~dp0"
cls
python detect_key.py
