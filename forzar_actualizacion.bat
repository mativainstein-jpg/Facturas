@echo off
chcp 65001 >nul
title Procesador de Facturas
cd /d "%~dp0"

REM Para los dias que necesitas la ultima version YA (no esperar a manana).
REM Borra la marca de "ya chequee hoy" y abre normal: fuerza a buscar
REM actualizaciones aunque ya se haya abierto la app antes en el dia.

if exist "ultima_actualizacion.txt" del /q "ultima_actualizacion.txt"

call procesar.bat
