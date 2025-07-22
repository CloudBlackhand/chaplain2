@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo =               CHAPLAIN - INSTALADOR                  =
echo =          Sistema de Mensagens WhatsApp               =
echo ========================================================
echo.

:: Verificar permissões de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Este script precisa ser executado como administrador.
    echo Por favor, clique com o botão direito e selecione "Executar como administrador".
    echo.
    echo Pressione qualquer tecla para sair...
    pause > nul
    exit /b 1
)

:: Verificar conectividade com a internet
ping -n 1 www.google.com >nul 2>&1
if %errorlevel% neq 0 (
    echo AVISO: Sem conexão com a internet. Algumas funcionalidades podem não funcionar corretamente.
    echo O script continuará, mas poderá falhar ao baixar dependências.
    echo.
    echo Pressione qualquer tecla para continuar mesmo assim ou feche esta janela para cancelar...
    pause > nul
)

:: Detectar versão do Windows
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
echo Versão do Windows detectada: %VERSION%
if "%version%" == "10.0" (
    set "IS_WIN10=true"
    echo Versão do Windows compatível: Windows 10 detectado.
) else if "%version%" == "6.3" (
    set "IS_WIN8_1=true"
    echo Versão do Windows compatível: Windows 8.1 detectado.
) else if "%version%" == "6.2" (
    set "IS_WIN8=true"
    echo Versão do Windows compatível: Windows 8 detectado.
) else if "%version%" == "6.1" (
    set "IS_WIN7=true"
    echo Versão do Windows compatível: Windows 7 detectado.
) else (
    echo AVISO: Sistema operacional não reconhecido. O script pode não funcionar corretamente.
    echo O script continuará, mas não há garantia de funcionamento adequado.
    echo.
    echo Pressione qualquer tecla para continuar mesmo assim ou feche esta janela para cancelar...
    pause > nul
)

:: Inicializar variáveis
set REINSTALAR_DEPS=false
set MODO_FOREGROUND=false
set DEBUG=true
set SYSTEM_PATH=%PATH%
set REQUIRES_REBOOT=false
set INSTALL_STATE=0

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

:: Verificar estado de reinicialização
if exist "%TEMP%\chaplain_install_state.txt" (
    for /f "tokens=1,2 delims==" %%a in (%TEMP%\chaplain_install_state.txt) do (
        if "%%a"=="STATE" set INSTALL_STATE=%%b
    )
    del "%TEMP%\chaplain_install_state.txt"
    echo Continuando instalação após reinicialização, estado: !INSTALL_STATE!
)

:: Diretório atual
set DIR=%~dp0
cd %DIR%

:: Criar diretórios necessários, se não existirem
if not exist logs mkdir logs
if not exist messages mkdir messages
if not exist storage mkdir storage
if not exist temp mkdir temp

:: Criar arquivo de log
set LOG_FILE=%DIR%\logs\chaplain_install_log.txt
echo Instalação iniciada em %date% %time% > %LOG_FILE%
echo Sistema: Windows %OS% >> %LOG_FILE%
echo Diretório de instalação: %DIR% >> %LOG_FILE%
echo Usuário: %USERNAME% >> %LOG_FILE%
echo Versão do Windows: %VERSION% >> %LOG_FILE%

:: Cores para mensagens
set "GREEN=92"
set "YELLOW=93"
set "RED=91"
set "BLUE=94"

:: Funções para mensagens coloridas
call :mostrar_titulo "Verificando dependências do sistema..."

:: Criar ponto de restauração do sistema
call :mostrar_progresso "Criando ponto de restauração do sistema..."
powershell -Command "Checkpoint-Computer -Description 'Antes da instalação do Chaplain' -RestorePointType 'APPLICATION_INSTALL'" >nul 2>&1
if %errorlevel% equ 0 (
    call :mostrar_sucesso "Ponto de restauração criado com sucesso"
) else (
    call :mostrar_aviso "Não foi possível criar ponto de restauração"
)

:: Verificar e instalar dependências
echo Verificando dependências do sistema... >> %LOG_FILE%
call :verificar_deps_sistema
if %errorlevel% neq 0 (
    echo ERRO: Falha ao verificar dependências do sistema >> %LOG_FILE%
    
    if "%REQUIRES_REBOOT%"=="true" (
        call :configurar_reinicializacao
        exit /b 0
    ) else (
        goto :erro_final
    )
)

:: Verificar e configurar ambiente Python
echo Configurando ambiente Python... >> %LOG_FILE%
call :configurar_python
if %errorlevel% neq 0 (
    echo ERRO: Falha ao configurar ambiente Python >> %LOG_FILE%
    
    if "%REQUIRES_REBOOT%"=="true" (
        call :configurar_reinicializacao
        exit /b 0
    ) else (
        goto :erro_final
    )
)

:: Verificar e configurar Node.js
echo Configurando Node.js... >> %LOG_FILE%
call :configurar_nodejs
if %errorlevel% neq 0 (
    echo ERRO: Falha ao configurar Node.js >> %LOG_FILE%
    
    if "%REQUIRES_REBOOT%"=="true" (
        call :configurar_reinicializacao
        exit /b 0
    ) else (
        goto :erro_final
    )
)

:: Iniciar o sistema
echo Iniciando o sistema... >> %LOG_FILE%
call :iniciar_sistema
if %errorlevel% neq 0 (
    echo ERRO: Falha ao iniciar o sistema >> %LOG_FILE%
    goto :erro_final
)

:: Finalização bem-sucedida
echo Instalação e inicialização concluídas com sucesso em %date% %time% >> %LOG_FILE%
if "%DEBUG%"=="true" (
    echo.
    echo Pressione qualquer tecla para encerrar...
    pause > nul
)
exit /b 0

:erro_final
call :mostrar_erro "Ocorreram erros durante a instalação. Verifique o arquivo de log: %LOG_FILE%"
echo.
echo Pressione qualquer tecla para encerrar...
pause > nul
exit /b 1

:configurar_reinicializacao
:: Salvar estado da instalação para retomar após reinicialização
echo STATE=%INSTALL_STATE% > "%TEMP%\chaplain_install_state.txt"

:: Criar script de continuação
echo @echo off > "%TEMP%\chaplain_restart.bat"
echo echo Retomando a instalação do Chaplain... >> "%TEMP%\chaplain_restart.bat"
echo start "" "%~dpnx0" %* >> "%TEMP%\chaplain_restart.bat"

:: Adicionar ao registro para executar após reinicialização
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce" /v ChaplainInstaller /t REG_SZ /d "%TEMP%\chaplain_restart.bat" /f >nul 2>&1

call :mostrar_aviso "O sistema precisa ser reiniciado para continuar a instalação."
call :mostrar_aviso "A instalação será retomada automaticamente após a reinicialização."
echo.
echo O sistema será reiniciado em 30 segundos. Pressione qualquer tecla para reiniciar agora...
timeout /t 30 /nobreak > nul
shutdown /r /t 0
exit /b 0

:mostrar_titulo
echo.
echo [%BLUE%m%~1[0m
echo.
echo %~1 >> %LOG_FILE%
goto :eof

:mostrar_sucesso
echo [%GREEN%m%~1[0m
echo %~1 >> %LOG_FILE%
goto :eof

:mostrar_aviso
echo [%YELLOW%m%~1[0m
echo AVISO: %~1 >> %LOG_FILE%
goto :eof

:mostrar_erro
echo [%RED%m%~1[0m
echo ERRO: %~1 >> %LOG_FILE%
goto :eof

:mostrar_progresso
echo [%BLUE%m%~1[0m
echo %~1 >> %LOG_FILE%
goto :eof

:verificar_deps_sistema
call :mostrar_titulo "Verificando dependências do sistema..."

:: Limpar arquivos temporários para garantir mais espaço
call :mostrar_progresso "Limpando arquivos temporários do sistema..."
rd /s /q "%TEMP%\Chaplain_Temp" 2>nul
mkdir "%TEMP%\Chaplain_Temp" 2>nul

:: Verificar se o Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :mostrar_aviso "Python não encontrado! Baixando e instalando Python 3.10..."
    
    :: Criar diretório temporário para downloads
    set "TEMP_DIR=%TEMP%\Chaplain_Temp"
    if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
    cd "%TEMP_DIR%"
    
    :: Baixar Python
    call :mostrar_progresso "Baixando Python 3.10..."
    curl -L -o python_installer.exe https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha ao baixar o Python. Verifique sua conexão com a internet."
        cd %DIR%
        exit /b 1
    )
    
    :: Instalar Python (silenciosamente, incluir no PATH, e pip)
    call :mostrar_progresso "Instalando Python 3.10..."
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_pip=1 CompileAll=1
    
    :: Limpar
    del python_installer.exe
    cd %DIR%
    
    :: Definir que precisamos reiniciar
    set REQUIRES_REBOOT=true
    set INSTALL_STATE=1
    
    :: Reiniciar o PATH para reconhecer o Python
    call :mostrar_progresso "Atualizando variáveis de ambiente para Python..."
    for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH') do set SYSTEM_PATH=%%B
    set PATH=%SYSTEM_PATH%
    
    :: Dar tempo para o sistema reconhecer o novo PATH
    timeout /t 5 /nobreak > nul
    
    :: Verificar se a instalação foi bem-sucedida
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha na instalação automática do Python. O sistema será reiniciado para concluir a instalação."
        exit /b 1
    ) else (
        call :mostrar_sucesso "Python instalado com sucesso!"
    )
)

:: Verificar versão do Python
for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python versão %PYTHON_VERSION% encontrado >> %LOG_FILE%
call :mostrar_sucesso "Python versão %PYTHON_VERSION% encontrado"

:: Verificar se o pip está instalado
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    call :mostrar_progresso "pip não encontrado! Instalando..."
    curl -L https://bootstrap.pypa.io/get-pip.py -o "%TEMP%\Chaplain_Temp\get-pip.py"
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha ao baixar o script do pip. Verifique sua conexão com a internet."
        exit /b 1
    )
    
    python "%TEMP%\Chaplain_Temp\get-pip.py" --no-warn-script-location
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha ao instalar o pip."
        exit /b 1
    )
    
    del "%TEMP%\Chaplain_Temp\get-pip.py"
)

:: Verificar se o Node.js está instalado
node --version >nul 2>&1
if %errorlevel% neq 0 (
    call :mostrar_aviso "Node.js não encontrado! Baixando e instalando Node.js 18.x LTS..."
    
    :: Criar diretório temporário para downloads
    set "TEMP_DIR=%TEMP%\Chaplain_Temp"
    if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
    cd "%TEMP_DIR%"
    
    :: Baixar Node.js
    call :mostrar_progresso "Baixando Node.js 18.x LTS..."
    curl -L -o node_installer.msi https://nodejs.org/dist/v18.18.2/node-v18.18.2-x64.msi
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha ao baixar o Node.js. Verifique sua conexão com a internet."
        cd %DIR%
        exit /b 1
    )
    
    :: Instalar Node.js silenciosamente
    call :mostrar_progresso "Instalando Node.js 18.x LTS..."
    start /wait msiexec /i node_installer.msi /quiet /qn /norestart
    
    :: Limpar
    del node_installer.msi
    cd %DIR%
    
    :: Definir que precisamos reiniciar
    set REQUIRES_REBOOT=true
    set INSTALL_STATE=2
    
    :: Reiniciar o PATH para reconhecer o Node.js
    call :mostrar_progresso "Atualizando variáveis de ambiente para Node.js..."
    for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH') do set SYSTEM_PATH=%%B
    set PATH=%SYSTEM_PATH%
    
    :: Dar tempo para o sistema reconhecer o novo PATH
    timeout /t 5 /nobreak > nul
    
    :: Verificar se a instalação foi bem-sucedida
    node --version >nul 2>&1
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha na instalação automática do Node.js. O sistema será reiniciado para concluir a instalação."
        exit /b 1
    ) else (
        call :mostrar_sucesso "Node.js instalado com sucesso!"
    )
)

:: Verificar versão do Node.js
for /f "tokens=1 delims=v" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
echo Node.js versão %NODE_VERSION% encontrado >> %LOG_FILE%
call :mostrar_sucesso "Node.js versão %NODE_VERSION% encontrado"

:: Verificar se a versão do Node.js é adequada
for /f "tokens=1 delims=." %%i in ("%NODE_VERSION%") do set NODE_MAJOR=%%i
if %NODE_MAJOR% LSS 14 (
    call :mostrar_aviso "Versão do Node.js muito antiga. Atualizando para a versão 18.x LTS..."
    
    :: Criar diretório temporário para downloads
    set "TEMP_DIR=%TEMP%\Chaplain_Temp"
    if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
    cd "%TEMP_DIR%"
    
    :: Baixar Node.js mais recente
    call :mostrar_progresso "Baixando Node.js 18.x LTS..."
    curl -L -o node_installer.msi https://nodejs.org/dist/v18.18.2/node-v18.18.2-x64.msi
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha ao baixar o Node.js. Verifique sua conexão com a internet."
        cd %DIR%
        exit /b 1
    )
    
    :: Instalar Node.js silenciosamente
    call :mostrar_progresso "Instalando Node.js 18.x LTS..."
    start /wait msiexec /i node_installer.msi /quiet /qn /norestart
    
    :: Limpar
    del node_installer.msi
    cd %DIR%
    
    :: Definir que precisamos reiniciar
    set REQUIRES_REBOOT=true
    set INSTALL_STATE=2
    
    :: Verificar se a instalação foi bem-sucedida
    node --version >nul 2>&1
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha na atualização do Node.js. Por favor, atualize manualmente."
        pause
        exit /b 1
    ) else (
        call :mostrar_sucesso "Node.js atualizado com sucesso!"
        
        :: Reiniciar o PATH para reconhecer Node.js
        call :mostrar_progresso "Atualizando variáveis de ambiente..."
        for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH') do set SYSTEM_PATH=%%B
        set PATH=%SYSTEM_PATH%
        
        :: Dar tempo para o sistema reconhecer as alterações
        timeout /t 5 /nobreak > nul
    )
)

:: Verificar se o npm está instalado
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    call :mostrar_erro "npm não encontrado! Tentando reinstalar o Node.js..."
    
    :: Criar diretório temporário para downloads
    set "TEMP_DIR=%TEMP%\Chaplain_Temp"
    if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
    cd "%TEMP_DIR%"
    
    :: Baixar Node.js
    call :mostrar_progresso "Baixando Node.js 18.x LTS..."
    curl -L -o node_installer.msi https://nodejs.org/dist/v18.18.2/node-v18.18.2-x64.msi
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha ao baixar o Node.js. Verifique sua conexão com a internet."
        cd %DIR%
        exit /b 1
    )
    
    :: Instalar Node.js silenciosamente
    call :mostrar_progresso "Reinstalando Node.js 18.x LTS..."
    start /wait msiexec /i node_installer.msi /quiet /qn /norestart
    
    :: Limpar
    del node_installer.msi
    cd %DIR%
    
    :: Definir que precisamos reiniciar
    set REQUIRES_REBOOT=true
    set INSTALL_STATE=2
    
    :: Verificar se a instalação foi bem-sucedida
    npm --version >nul 2>&1
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha na reinstalação do Node.js. O sistema será reiniciado para concluir a instalação."
        exit /b 1
    ) else (
        call :mostrar_sucesso "Node.js reinstalado com sucesso!"
        
        :: Dar tempo para o sistema reconhecer as alterações
        timeout /t 5 /nobreak > nul
    )
)

call :mostrar_sucesso "Todas as dependências do sistema estão instaladas!"
exit /b 0

:configurar_python
call :mostrar_titulo "Configurando ambiente Python..."

:: Verificar módulo venv
python -c "import venv" >nul 2>&1
if %errorlevel% neq 0 (
    call :mostrar_progresso "Instalando módulo venv..."
    python -m pip install virtualenv
)

:: Verificar e criar ambiente virtual
if not exist venv (
    call :mostrar_progresso "Criando ambiente virtual Python..."
    python -m venv venv
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha ao criar ambiente virtual Python. Tentando com virtualenv..."
        python -m pip install virtualenv
        python -m virtualenv venv
        if %errorlevel% neq 0 (
            call :mostrar_erro "Falha ao criar ambiente virtual Python."
            exit /b 1
        )
    )
) else (
    call :mostrar_progresso "Ambiente virtual já existe, usando existente..."
)

:: Ativar ambiente virtual
call :mostrar_progresso "Ativando ambiente virtual..."
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    call :mostrar_erro "Falha ao ativar o ambiente virtual Python."
    exit /b 1
)

:: Instalar dependências Python
call :mostrar_progresso "Instalando dependências Python..."
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    call :mostrar_erro "Falha ao atualizar o pip."
    exit /b 1
)

call :mostrar_progresso "Instalando pacotes Python necessários..."
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    call :mostrar_erro "Falha ao instalar dependências Python. Tentando com --no-cache-dir..."
    python -m pip install -r requirements.txt --no-cache-dir
    if %errorlevel% neq 0 (
        call :mostrar_erro "Falha ao instalar dependências Python. Detalhes no log de erro."
        exit /b 1
    )
)

call :mostrar_sucesso "Ambiente Python configurado com sucesso!"
exit /b 0

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
if %errorlevel% neq 0 (
    call :mostrar_aviso "Falha ao atualizar o npm. Continuando com a versão atual..."
)

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
        if %errorlevel% neq 0 (
            call :mostrar_erro "Falha ao instalar o yarn."
            exit /b 1
        )
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
exit /b 0

:iniciar_sistema
call :mostrar_titulo "Iniciando o sistema Chaplain..."

:: Encerrar processos ativos se existentes
call :encerrar_processos_existentes

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
    
    :: Iniciar o bot do WhatsApp em uma nova janela permanente
    start "Chaplain - WhatsApp Bot" /min cmd /k "title Chaplain - WhatsApp Bot && node whatsapp_bot.js"
    
    :: Aguardar o serviço iniciar
    call :mostrar_progresso "Aguardando o serviço WhatsApp iniciar..."
    set /a MAX_TRIES=12
    set /a CURRENT_TRY=0
    
    :check_whatsapp_loop
    timeout /t 5 /nobreak > nul
    set /a CURRENT_TRY+=1
    
    :: Verificar se o bot está em execução
    tasklist /fi "imagename eq node.exe" /v | findstr /i "whatsapp_bot.js" >nul
    if %errorlevel% neq 0 (
        if !CURRENT_TRY! lss !MAX_TRIES! (
            call :mostrar_aviso "Aguardando WhatsApp iniciar (tentativa !CURRENT_TRY!/!MAX_TRIES!)..."
            goto check_whatsapp_loop
        ) else (
            call :mostrar_erro "O bot WhatsApp não foi iniciado após várias tentativas."
            exit /b 1
        )
    )
    
    echo Aguardando QR Code e autenticação...
    echo Escaneie o QR Code na janela minimizada do WhatsApp Bot (verifique na barra de tarefas)
    echo Clique na janela do WhatsApp Bot se necessário para visualizar o QR code.
    echo Após escanear, pressione qualquer tecla para continuar...
    pause > nul
    
    :: Criar script para verificar se a autenticação foi concluída
    call :mostrar_progresso "Verificando autenticação..."
    set /a MAX_AUTH_TRIES=6
    set /a AUTH_TRY=0
    
    :check_auth_loop
    curl -s http://localhost:3000/api/status 2>nul | findstr "ready" >nul
    if %errorlevel% equ 0 (
        call :mostrar_sucesso "Autenticação WhatsApp concluída com sucesso!"
    ) else (
        set /a AUTH_TRY+=1
        if !AUTH_TRY! lss !MAX_AUTH_TRIES! (
            call :mostrar_aviso "Aguardando autenticação (tentativa !AUTH_TRY!/!MAX_AUTH_TRIES!)..."
            timeout /t 10 /nobreak > nul
            goto check_auth_loop
        ) else (
            call :mostrar_aviso "Não foi possível confirmar a autenticação. Continuando mesmo assim..."
        )
    )
    
    call :mostrar_progresso "Etapa 2/2: Inicializando aplicação principal..."
    cd %DIR%
    
    :: Iniciar a aplicação principal em uma nova janela permanente
    start "Chaplain - Aplicação Principal" cmd /k "title Chaplain - Aplicação Principal && call venv\Scripts\activate.bat && python src\main.py"
    
    :: Aguardar um pouco para garantir que o processo inicie
    timeout /t 5 /nobreak > nul
    
    :: Verificar se o processo está em execução
    tasklist /fi "imagename eq python.exe" /v | findstr /i "main.py" >nul
    if %errorlevel% neq 0 (
        call :mostrar_erro "A aplicação principal não foi iniciada corretamente."
        exit /b 1
    ) else (
        call :mostrar_sucesso "Aplicação principal iniciada com sucesso!"
    )
    
) else (
    call :mostrar_progresso "Iniciando o sistema em segundo plano..."
    call :mostrar_aviso "NOTA: Se esta é a primeira vez que você executa o sistema,"
    call :mostrar_aviso "você precisa usar a opção --foreground para escanear o QR code!"
    
    :: Iniciar o bot do WhatsApp em uma nova janela permanente
    cd %DIR%\src\whatsapp
    start "Chaplain - WhatsApp Bot" /min cmd /k "title Chaplain - WhatsApp Bot && node whatsapp_bot.js"
    
    :: Aguardar o serviço iniciar
    call :mostrar_progresso "Aguardando o serviço WhatsApp iniciar..."
    timeout /t 15 /nobreak > nul
    
    :: Verificar se o bot está em execução
    tasklist /fi "imagename eq node.exe" /v | findstr /i "whatsapp_bot.js" >nul
    if %errorlevel% neq 0 (
        call :mostrar_aviso "O bot WhatsApp não parece estar em execução."
    )
    
    :: Iniciar a aplicação principal em uma nova janela permanente
    cd %DIR%
    start "Chaplain - Aplicação Principal" cmd /k "call venv\Scripts\activate.bat && python src\main.py"
    
    :: Aguardar um pouco para garantir que o processo inicie
    timeout /t 5 /nobreak > nul
    
    :: Verificar se os processos estão em execução
    tasklist /fi "imagename eq node.exe" /v | findstr /i "whatsapp_bot.js" >nul
    if %errorlevel% neq 0 (
        call :mostrar_aviso "O serviço WhatsApp não parece estar em execução."
    )
    
    tasklist /fi "imagename eq python.exe" /v | findstr /i "main.py" >nul
    if %errorlevel% neq 0 (
        call :mostrar_aviso "A aplicação principal não parece estar em execução."
    ) else (
        call :mostrar_sucesso "Sistema Chaplain iniciado em segundo plano!"
    )
    
    call :mostrar_aviso "Se este é o primeiro uso, feche esta janela e execute com --foreground para escanear o QR code."
)

:: Criar tarefa agendada para iniciar com o Windows
if "%MODO_FOREGROUND%"=="true" (
    call :mostrar_progresso "Configurando inicialização automática com o Windows..."
    schtasks /create /tn "ChaplainStart" /tr "%DIR%\Chaplain-Windows-Normal.bat" /sc onlogon /ru "%USERNAME%" /f >nul 2>&1
    if %errorlevel% equ 0 (
        call :mostrar_sucesso "Chaplain configurado para iniciar automaticamente ao fazer login"
    ) else (
        call :mostrar_aviso "Não foi possível configurar inicialização automática"
    )
)

exit /b 0

:encerrar_processos_existentes
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

goto :eof 