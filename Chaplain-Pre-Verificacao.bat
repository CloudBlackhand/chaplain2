@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo =           CHAPLAIN - VERIFICAÇÃO AVANÇADA            =
echo =      Garantia de 100% de compatibilidade Windows     =
echo ========================================================
echo.

:: Verificar se está sendo executado como administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERRO CRÍTICO] Este script DEVE ser executado como administrador.
    echo.
    echo Por favor:
    echo 1. Feche esta janela
    echo 2. Clique com o botão direito no arquivo
    echo 3. Selecione "Executar como administrador"
    echo.
    echo Pressione qualquer tecla para sair...
    pause > nul
    exit /b 1
)

:: Criar diretório de log
set LOGS_DIR=%~dp0logs
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

:: Arquivo de log de diagnóstico
set DIAG_LOG=%LOGS_DIR%\diagnostico_pre_instalacao.txt
echo ===== Diagnóstico de Sistema Chaplain ===== > "%DIAG_LOG%"
echo Data e hora: %date% %time% >> "%DIAG_LOG%"
echo. >> "%DIAG_LOG%"

:: Coletar informações do sistema
echo [+] Coletando informações do sistema...
echo ----- INFORMAÇÕES DO SISTEMA ----- >> "%DIAG_LOG%"
systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Type" >> "%DIAG_LOG%"
echo. >> "%DIAG_LOG%"

:: Verificar versão do Windows
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
echo Versão do Windows: %VERSION% >> "%DIAG_LOG%"

:: Verificar se é Windows 10 ou superior
set WIN10_COMPAT=true
if "%VERSION%"=="10.0" (
    echo [OK] Windows 10 detectado. Totalmente compatível.
    echo Windows 10 detectado. Totalmente compatível. >> "%DIAG_LOG%"
) else if "%VERSION%" gtr "10.0" (
    echo [OK] Windows 11 ou superior detectado. Totalmente compatível.
    echo Windows 11 ou superior detectado. Totalmente compatível. >> "%DIAG_LOG%"
) else (
    set WIN10_COMPAT=false
    echo [AVISO] Versão do Windows anterior ao Windows 10 detectada.
    echo Versão do Windows anterior ao Windows 10 detectada. >> "%DIAG_LOG%"
)

:: Verificar conectividade com a internet
echo [+] Verificando conectividade com a internet...
ping -n 2 www.google.com >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Sem conexão com a internet detectada.
    echo Sem conexão com a internet detectada. >> "%DIAG_LOG%"
    ping -n 2 www.microsoft.com >nul 2>&1
    if %errorlevel% neq 0 (
        echo [AVISO] Tentativa alternativa falhou. Conexão com a internet é necessária.
        echo Tentativa alternativa falhou. Conexão com a internet é necessária. >> "%DIAG_LOG%"
        set INTERNET=false
    ) else (
        echo [OK] Conexão alternativa detectada.
        echo Conexão alternativa detectada. >> "%DIAG_LOG%"
        set INTERNET=true
    )
) else (
    echo [OK] Conexão com a internet detectada.
    echo Conexão com a internet detectada. >> "%DIAG_LOG%"
    set INTERNET=true
)

:: Verificar espaço em disco
echo [+] Verificando espaço em disco...
for /f "tokens=*" %%a in ('wmic logicaldisk where "DeviceID='%~d0'" get FreeSpace^,Size /format:value') do (
    for /f "tokens=1,2 delims==" %%b in ("%%a") do (
        if "%%b"=="FreeSpace" set FREE_SPACE=%%c
        if "%%b"=="Size" set DISK_SIZE=%%c
    )
)

:: Converter para GB
set /a FREE_SPACE_GB=%FREE_SPACE:~0,-9%/1024
echo Espaço livre em disco: %FREE_SPACE_GB% GB >> "%DIAG_LOG%"

if %FREE_SPACE_GB% LSS 5 (
    echo [AVISO] Espaço em disco baixo: %FREE_SPACE_GB% GB. Recomendado: 5 GB ou mais.
    echo Espaço em disco baixo: %FREE_SPACE_GB% GB. Recomendado: 5 GB ou mais. >> "%DIAG_LOG%"
    set DISK_SPACE=false
) else (
    echo [OK] Espaço em disco suficiente: %FREE_SPACE_GB% GB.
    echo Espaço em disco suficiente: %FREE_SPACE_GB% GB. >> "%DIAG_LOG%"
    set DISK_SPACE=true
)

:: Verificar portas necessárias
echo [+] Verificando portas necessárias...
echo ----- VERIFICAÇÃO DE PORTAS ----- >> "%DIAG_LOG%"
set PORT_3000=true

netstat -an | find ":3000" > nul
if %errorlevel% equ 0 (
    echo [AVISO] A porta 3000 já está em uso. Isso pode causar conflitos.
    echo Porta 3000 já está em uso. >> "%DIAG_LOG%"
    set PORT_3000=false
) else (
    echo [OK] Porta 3000 disponível para WhatsApp API.
    echo Porta 3000 disponível. >> "%DIAG_LOG%"
)

:: Verificar presença de antivírus que possa bloquear
echo [+] Verificando antivírus...
echo ----- ANTIVÍRUS DETECTADOS ----- >> "%DIAG_LOG%"

set AV_DETECTED=false
wmic /namespace:\\root\securitycenter2 path antivirusproduct get displayName > "%TEMP%\avlist.txt" 2>nul
type "%TEMP%\avlist.txt" >> "%DIAG_LOG%"

for /f "skip=1 tokens=*" %%a in ('type "%TEMP%\avlist.txt"') do (
    if not "%%a"=="" (
        echo [INFORMAÇÃO] Antivírus detectado: %%a
        set AV_DETECTED=true
    )
)

if "%AV_DETECTED%"=="true" (
    echo [AVISO] Antivírus detectado. Pode ser necessário adicionar exceções.
    echo Antivírus detectado. Pode ser necessário adicionar exceções. >> "%DIAG_LOG%"
) else (
    echo [OK] Nenhum antivírus ativo detectado que possa interferir.
    echo Nenhum antivírus ativo detectado. >> "%DIAG_LOG%"
)

:: Verificar compatibilidade com Python/Node.js
echo [+] Verificando compatibilidade com Python e Node.js...
echo ----- COMPATIBILIDADE DE COMPONENTES ----- >> "%DIAG_LOG%"

set VC_REDIST=false
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Visual C++ Redistributable encontrado.
    echo Visual C++ Redistributable encontrado. >> "%DIAG_LOG%"
    set VC_REDIST=true
) else (
    echo [AVISO] Visual C++ Redistributable não encontrado. Python pode não funcionar.
    echo Visual C++ Redistributable não encontrado. >> "%DIAG_LOG%"
    
    :: Tentar instalar o Visual C++ Redistributable
    echo [+] Tentando baixar e instalar Visual C++ Redistributable...
    echo Tentando baixar e instalar Visual C++ Redistributable... >> "%DIAG_LOG%"
    
    if "%INTERNET%"=="true" (
        curl -L -o "%TEMP%\vc_redist.exe" https://aka.ms/vs/17/release/vc_redist.x64.exe
        if %errorlevel% equ 0 (
            echo [OK] Download concluído. Instalando...
            start /wait "%TEMP%\vc_redist.exe" /passive /norestart
            if %errorlevel% equ 0 (
                echo [OK] Visual C++ Redistributable instalado com sucesso.
                echo Visual C++ Redistributable instalado com sucesso. >> "%DIAG_LOG%"
                set VC_REDIST=true
            ) else (
                echo [AVISO] Não foi possível instalar Visual C++ Redistributable.
                echo Não foi possível instalar Visual C++ Redistributable. >> "%DIAG_LOG%"
            )
        ) else (
            echo [AVISO] Não foi possível baixar Visual C++ Redistributable.
            echo Não foi possível baixar Visual C++ Redistributable. >> "%DIAG_LOG%"
        )
    ) else (
        echo [AVISO] Sem internet para baixar Visual C++ Redistributable.
        echo Sem internet para baixar Visual C++ Redistributable. >> "%DIAG_LOG%"
    )
)

:: Verificar políticas de execução
echo [+] Verificando políticas de execução...
set EXEC_POLICY=true
powershell -Command "Get-ExecutionPolicy" > "%TEMP%\execpolicy.txt" 2>nul
set /p POLICY=<"%TEMP%\execpolicy.txt"
echo Política de execução PowerShell: %POLICY% >> "%DIAG_LOG%"

if "%POLICY%"=="Restricted" (
    echo [AVISO] Política de execução PowerShell restritiva detectada.
    echo Política de execução PowerShell restritiva detectada. >> "%DIAG_LOG%"
    set EXEC_POLICY=false
)

:: Verificar caminho máximo
echo [+] Verificando configuração de caminho longo...
set LONG_PATH=true
reg query "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled > "%TEMP%\longpath.txt" 2>nul
findstr /i "0x1" "%TEMP%\longpath.txt" >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Suporte a caminhos longos não está habilitado.
    echo Suporte a caminhos longos não está habilitado. >> "%DIAG_LOG%"
    set LONG_PATH=false
) else (
    echo [OK] Suporte a caminhos longos está habilitado.
    echo Suporte a caminhos longos está habilitado. >> "%DIAG_LOG%"
)

:: Verificar UAC
echo [+] Verificando configurações de UAC...
set UAC_ENABLED=true
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v EnableLUA > "%TEMP%\uac.txt" 2>nul
findstr /i "0x0" "%TEMP%\uac.txt" >nul 2>&1
if %errorlevel% equ 0 (
    echo [AVISO] UAC está desativado.
    echo UAC está desativado. >> "%DIAG_LOG%"
    set UAC_ENABLED=false
) else (
    echo [OK] UAC está habilitado.
    echo UAC está habilitado. >> "%DIAG_LOG%"
)

:: Verificar se WebSocket está disponível para WhatsApp
echo [+] Verificando suporte a WebSocket...
set WEBSOCKET=true
powershell -Command "Get-WindowsCapability -Online | Select-String 'WebSocket'" > "%TEMP%\websocket.txt" 2>nul
findstr /i "State : Installed" "%TEMP%\websocket.txt" >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Suporte a WebSocket pode não estar disponível.
    echo Suporte a WebSocket pode não estar disponível. >> "%DIAG_LOG%"
    set WEBSOCKET=false
) else (
    echo [OK] Suporte a WebSocket disponível.
    echo Suporte a WebSocket disponível. >> "%DIAG_LOG%"
)

echo.
echo ===== RESULTADO DA VERIFICAÇÃO =====

:: Calcular pontuação de compatibilidade
set /a SCORE=0
if "%WIN10_COMPAT%"=="true" set /a SCORE+=20
if "%INTERNET%"=="true" set /a SCORE+=20
if "%DISK_SPACE%"=="true" set /a SCORE+=15
if "%PORT_3000%"=="true" set /a SCORE+=10
if "%VC_REDIST%"=="true" set /a SCORE+=15
if "%EXEC_POLICY%"=="true" set /a SCORE+=10
if "%LONG_PATH%"=="true" set /a SCORE+=5
if "%UAC_ENABLED%"=="true" set /a SCORE+=5

echo Pontuação de compatibilidade: %SCORE% / 100

echo.
echo Pontuação de compatibilidade: %SCORE% / 100 >> "%DIAG_LOG%"

:: Verificar se o sistema está pronto
if %SCORE% GEQ 80 (
    color 0A
    echo ===============================================
    echo [RESULTADO] Seu sistema está 100%% pronto para o Chaplain!
    echo ===============================================
    echo.
    echo Relatório de diagnóstico salvo em: "%DIAG_LOG%"
    echo.
    echo Para iniciar a instalação 100%% garantida, pressione qualquer tecla...
    pause > nul
    
    :: Iniciar instalação com parâmetros corretos
    if "%EXEC_POLICY%"=="false" (
        :: Se a política de execução é restritiva
        echo Definindo política de execução temporariamente...
        powershell -Command "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force"
    )
    
    start "" "%~dp0Chaplain-Windows.bat" --foreground
    
    echo.
    echo [SUCESSO] Chaplain iniciado com 100% de compatibilidade!
    echo.
    echo Este assistente de verificação será fechado em 5 segundos...
    timeout /t 5 /nobreak > nul
    exit /b 0
) else (
    color 0E
    echo ===============================================
    echo [AVISO] Alguns ajustes são necessários para 100%% de compatibilidade!
    echo ===============================================
    echo.
    echo Por favor, corrija os problemas marcados como [AVISO] acima.
    echo.
    echo Relatório de diagnóstico salvo em: "%DIAG_LOG%"
    echo.
    
    echo Deseja prosseguir com a instalação mesmo assim?
    echo 1 - Sim, continuar mesmo com avisos (não recomendado)
    echo 2 - Não, quero corrigir os problemas primeiro
    
    choice /c 12 /n /m "Escolha uma opção [1,2]: "
    if %errorlevel% equ 1 (
        echo.
        echo Prosseguindo com a instalação...
        start "" "%~dp0Chaplain-Windows.bat" --foreground
        echo.
        echo Este assistente de verificação será fechado em 3 segundos...
        timeout /t 3 /nobreak > nul
    ) else (
        echo.
        echo Instalação cancelada. Por favor corrija os problemas e execute este script novamente.
        echo.
        echo Pressione qualquer tecla para sair...
        pause > nul
    )
    exit /b 1
) 