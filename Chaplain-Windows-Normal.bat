@echo off
echo ========================================================
echo =               CHAPLAIN - WhatsApp                    =
echo =            Iniciando em segundo plano...             =
echo ========================================================
echo.
echo Verificando garantia de 100%% de compatibilidade...
echo Python e Node.js serão instalados automaticamente se necessário.
echo.

:: Verificar se o script de pré-verificação existe
if exist "%~dp0Chaplain-Pre-Verificacao.bat" (
    :: Executar verificação prévia para garantir 100% de compatibilidade
    call "%~dp0Chaplain-Pre-Verificacao.bat"
    
    :: Se a verificação prévia falhar, não continuar
    if %errorlevel% neq 0 exit /b %errorlevel%
) else (
    :: Se o script de pré-verificação não existir, executar normalmente
    call "%~dp0instalar_e_iniciar_chaplain_windows.bat" 
)

:: Garantir que a janela não feche imediatamente
echo.
echo Instalação finalizada. Pressione qualquer tecla para encerrar...
pause > nul 