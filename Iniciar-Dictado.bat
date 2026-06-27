@echo off
chcp 65001 > nul
title AM VOICE DICTATION — Dr. Ariel Merino
cd /d "%~dp0"

cls
python am-whisper-dictado.py
pause
