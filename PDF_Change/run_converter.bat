@echo off
cd /d "%~dp0"
python pdf_portrait_converter.py %*
pause
