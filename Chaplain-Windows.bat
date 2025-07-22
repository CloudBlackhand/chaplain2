@echo off
echo ========================================================
echo =               CHAPLAIN - WhatsApp                    =
echo =              Iniciando configuração...               =
echo ========================================================
echo.
echo Executando o instalador com modo QR Code...
echo Python e Node.js serão instalados automaticamente se necessário.
echo.

:: Executar o script de instalação com opção de QR code
call "%~dp0instalar_e_iniciar_chaplain_windows.bat" --foreground 