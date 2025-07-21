@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo =               CHAPLAIN - INSTALADOR                  =
echo =          Sistema de Mensagens WhatsApp               =
echo ========================================================
echo.

set REINSTALAR_DEPS=false
set MODO_FOREGROUND=false

:: Verificar parâmetros
if "%1"=="--reinstall" (
    set REINSTALAR_DEPS=true
)
if "%1"=="--foreground" (
    set MODO_FOREGROUND=true
)
if "%2"=="--reinstall" (
    set REINSTALAR_DEPS=true
)
if "%2"=="--foreground" (
    set MODO_FOREGROUND=true
)

:: Diretório atual
set DIR=%~dp0
cd %DIR%

:: Cores para mensagens
set "GREEN=92"
set "YELLOW=93"
set "RED=91"
set "BLUE=94"

:: Funções para mensagens coloridas
call :mostrar_titulo "Verificando dependências do sistema..."

:: Verificar e instalar dependências
call :verificar_deps_sistema

:: Verificar e configurar ambiente Python
call :configurar_python

:: Verificar e configurar Node.js
call :configurar_nodejs

:: Iniciar o sistema
call :iniciar_sistema

goto :eof

:mostrar_titulo
echo.
echo [%BLUE%m%~1[0m
echo.
goto :eof

:mostrar_sucesso
echo [%GREEN%m%~1[0m
goto :eof

:mostrar_aviso
echo [%YELLOW%m%~1[0m
goto :eof

:mostrar_erro
echo [%RED%m%~1[0m
goto :eof

:mostrar_progresso
echo [%BLUE%m%~1[0m
goto :eof

:verificar_deps_sistema
call :mostrar_titulo "Verificando dependências do sistema..."

:: Verificar se o Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :mostrar_erro "Python não encontrado! Por favor, instale o Python 3.8 ou superior."
    echo Você pode baixar o Python em: https://www.python.org/downloads/windows/
    echo Certifique-se de marcar "Add Python to PATH" durante a instalação.
    pause
    exit /b 1
)

:: Verificar versão do Python
for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python versão %PYTHON_VERSION% encontrado

:: Verificar se o pip está instalado
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    call :mostrar_erro "pip não encontrado! Instalando..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py
    del get-pip.py
)

:: Verificar se o Node.js está instalado
node --version >nul 2>&1
if %errorlevel% neq 0 (
    call :mostrar_erro "Node.js não encontrado! Por favor, instale o Node.js 18.x (LTS)."
    echo Você pode baixar o Node.js em: https://nodejs.org/
    pause
    exit /b 1
)

:: Verificar versão do Node.js
for /f "tokens=1 delims=v" %%i in ('node --version') do set NODE_VERSION=%%i
echo Node.js versão %NODE_VERSION% encontrado

:: Verificar se a versão do Node.js é adequada
for /f "tokens=1 delims=." %%i in ("%NODE_VERSION%") do set NODE_MAJOR=%%i
if %NODE_MAJOR% LSS 14 (
    call :mostrar_erro "Versão do Node.js muito antiga. Recomendamos instalar a versão 18.x (LTS)."
    echo Você pode baixar o Node.js em: https://nodejs.org/
    pause
    exit /b 1
)

:: Verificar se o npm está instalado
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    call :mostrar_erro "npm não encontrado! Por favor, reinstale o Node.js."
    exit /b 1
)

call :mostrar_sucesso "Todas as dependências do sistema estão instaladas!"
goto :eof

:configurar_python
call :mostrar_titulo "Configurando ambiente Python..."

:: Verificar e criar ambiente virtual
if not exist venv (
    call :mostrar_progresso "Criando ambiente virtual Python..."
    python -m venv venv
) else (
    call :mostrar_progresso "Ambiente virtual já existe, usando existente..."
)

:: Ativar ambiente virtual
call venv\Scripts\activate.bat

:: Instalar dependências Python
call :mostrar_progresso "Instalando dependências Python..."
python -m pip install --upgrade pip
pip install -r requirements.txt

call :mostrar_sucesso "Ambiente Python configurado com sucesso!"
goto :eof

:configurar_nodejs
call :mostrar_titulo "Configurando Node.js..."

:: Navegar para o diretório do WhatsApp
cd %DIR%\src\whatsapp

if "%REINSTALAR_DEPS%"=="true" (
    call :mostrar_progresso "Removendo node_modules existentes..."
    if exist node_modules rmdir /s /q node_modules
    if exist package-lock.json del /f package-lock.json
)

:: Atualizar npm para a versão mais recente
call :mostrar_progresso "Atualizando npm para a versão mais recente..."
call npm install -g npm@latest

:: Instalar dependências do WhatsApp bot
call :mostrar_progresso "Instalando dependências do WhatsApp bot..."
call npm install --no-fund --no-audit --legacy-peer-deps

:: Verificar se a instalação do npm foi bem-sucedida
if %errorlevel% neq 0 (
    call :mostrar_aviso "npm install falhou. Tentando com yarn..."
    
    :: Verificar se o yarn está instalado
    yarn --version >nul 2>&1
    if %errorlevel% neq 0 (
        call :mostrar_progresso "Instalando yarn..."
        npm install -g yarn
    )
    
    :: Tentar instalação com yarn
    call yarn install
    
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha na instalação das dependências do WhatsApp bot!"
        exit /b 1
    )
)

:: Voltar ao diretório principal
cd %DIR%

call :mostrar_sucesso "Node.js configurado com sucesso!"
goto :eof

:iniciar_sistema
call :mostrar_titulo "Iniciando o sistema Chaplain..."

:: Verificar se o sistema já está em execução
tasklist /fi "imagename eq node.exe" /v | findstr /i "whatsapp_bot.js" >nul
if %errorlevel% equ 0 (
    call :mostrar_aviso "Detectado processo do WhatsApp Bot já em execução..."
    choice /c YN /m "Deseja encerrar o processo existente e iniciar novamente? (Y/N)"
    if errorlevel 2 (
        call :mostrar_aviso "Mantendo processo existente. Tentando conectar..."
    ) else (
        call :mostrar_progresso "Encerrando processo existente..."
        taskkill /f /fi "imagename eq node.exe" /v | findstr /i "whatsapp_bot.js" >nul
    )
)

tasklist /fi "imagename eq python.exe" /v | findstr /i "main.py" >nul
if %errorlevel% equ 0 (
    call :mostrar_aviso "Detectado processo do Chaplain já em execução..."
    choice /c YN /m "Deseja encerrar o processo existente e iniciar novamente? (Y/N)"
    if errorlevel 2 (
        call :mostrar_aviso "Mantendo processo existente. Você pode fechar esta janela."
        exit /b 0
    ) else (
        call :mostrar_progresso "Encerrando processo existente..."
        taskkill /f /fi "imagename eq python.exe" /v | findstr /i "main.py" >nul
    )
)

:: Criar diretórios necessários, se não existirem
if not exist logs mkdir logs
if not exist messages mkdir messages
if not exist storage mkdir storage

if "%MODO_FOREGROUND%"=="true" (
    call :mostrar_progresso "Etapa 1/2: Inicializando bot WhatsApp para configuração..."
    call :mostrar_aviso "AGUARDE o QR code aparecer abaixo para escanear com seu WhatsApp:"
    echo.
    echo ================================================================
    echo =                ESCANEIE O QR CODE COM SEU CELULAR            =
    echo =                                                              =
    echo =           APÓS ESCANEAR, AGUARDE A CONFIRMAÇÃO E             =
    echo =          PRESSIONE QUALQUER TECLA PARA CONTINUAR             =
    echo ================================================================
    echo.
    
    cd %DIR%\src\whatsapp
    start /b cmd /c node whatsapp_bot.js
    
    pause
    
    :: Verificar se a autenticação foi concluída
    curl -s http://localhost:3000/api/status | findstr "ready" >nul
    if %errorlevel% equ 0 (
        call :mostrar_sucesso "Autenticação WhatsApp concluída com sucesso!"
    ) else (
        call :mostrar_aviso "Não foi possível confirmar a autenticação. Continuando mesmo assim..."
    )
    
    call :mostrar_progresso "Etapa 2/2: Inicializando aplicação principal..."
    cd %DIR%
    call venv\Scripts\activate.bat
    python src\main.py
    
    :: Encerrar processo do WhatsApp bot
    taskkill /f /fi "imagename eq node.exe" /v | findstr /i "whatsapp_bot.js" >nul
) else (
    call :mostrar_progresso "Iniciando o sistema em segundo plano..."
    call :mostrar_aviso "NOTA: Se esta é a primeira vez que você executa o sistema,"
    call :mostrar_aviso "você precisa usar a opção --foreground para escanear o QR code!"
    
    cd %DIR%
    start cmd /c "call venv\Scripts\activate.bat && python src\main.py"
    
    call :mostrar_sucesso "Sistema Chaplain iniciado em segundo plano!"
    call :mostrar_aviso "Se este é o primeiro uso, feche esta janela e execute com --foreground para escanear o QR code."
)

goto :eof 