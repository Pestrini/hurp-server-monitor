@echo off
title HURP Server Monitor
echo ==================================================
echo      Iniciando Monitoramento de Servidores
echo ==================================================
echo.

:: Vai para a pasta onde o .bat está sendo executado dinamicamente
cd /d "%~dp0"

echo Instalando dependencias caso falte alguma na maquina local...
pip install -r requirements.txt --quiet

echo.
echo Abrindo a interface no navegador...
python -m streamlit run app.py

pause
