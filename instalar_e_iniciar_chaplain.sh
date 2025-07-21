#!/bin/bash

# Cores para melhor visualização
VERDE="\033[0;32m"
AMARELO="\033[1;33m"
VERMELHO="\033[0;31m"
AZUL="\033[0;34m"
RESET="\033[0m"

# Diretório do projeto
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Variáveis globais
REINSTALAR_DEPS="false"
MODO_FOREGROUND="false"

# Processar parâmetros
for param in "$@"; do
    case $param in
        --reinstall)
        REINSTALAR_DEPS="true"
        ;;
        --foreground)
        MODO_FOREGROUND="true"
        ;;
        *)
        # parâmetro desconhecido
        ;;
    esac
done

# Função para mostrar progresso
mostrar_progresso() {
    echo -e "${AZUL}[INFO]${RESET} $1"
}

# Função para mostrar sucesso
mostrar_sucesso() {
    echo -e "${VERDE}[SUCESSO]${RESET} $1"
}

# Função para mostrar erro
mostrar_erro() {
    echo -e "${VERMELHO}[ERRO]${RESET} $1"
}

# Função para mostrar aviso
mostrar_aviso() {
    echo -e "${AMARELO}[AVISO]${RESET} $1"
}

# Detectar sistema operacional
detectar_sistema() {
    mostrar_progresso "Detectando sistema operacional..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        mostrar_sucesso "Sistema operacional detectado: $OS"
    elif command -v apt-get &> /dev/null; then
        OS="debian"
        mostrar_sucesso "Sistema baseado em Debian detectado"
    elif command -v yum &> /dev/null; then
        OS="fedora"
        mostrar_sucesso "Sistema baseado em RedHat/Fedora detectado"
    elif command -v pacman &> /dev/null; then
        OS="arch"
        mostrar_sucesso "Sistema baseado em Arch detectado"
    elif command -v brew &> /dev/null; then
        OS="macos"
        mostrar_sucesso "Sistema macOS detectado"
    else
        OS="desconhecido"
        mostrar_aviso "Sistema operacional não identificado, assumindo instalação manual"
    fi
}

# Instalar dependências do sistema
instalar_deps_sistema() {
    mostrar_progresso "Verificando dependências do sistema..."
    
    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        mostrar_progresso "Python 3 não encontrado. Instalando..."
        
        case $OS in
            "debian"|"ubuntu"|"raspbian"|"linuxmint")
                sudo apt-get update
                sudo apt-get install -y python3 python3-pip python3-venv
                ;;
            "fedora"|"rhel"|"centos")
                sudo yum install -y python3 python3-pip
                ;;
            "arch")
                sudo pacman -Sy python python-pip
                ;;
            "macos")
                brew install python3
                ;;
            *)
                mostrar_erro "Não foi possível instalar Python automaticamente. Por favor, instale Python 3.8+ manualmente."
                return 1
                ;;
        esac
    else
        PYTHON_VERSION=$(python3 --version)
        mostrar_sucesso "$PYTHON_VERSION encontrado"
    fi
    
    # Verificar Node.js
    if ! command -v node &> /dev/null; then
        mostrar_progresso "Node.js não encontrado. Instalando..."
        
        case $OS in
            "debian"|"ubuntu"|"raspbian"|"linuxmint")
                # Instalar Node.js via NodeSource
                curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
                sudo apt-get install -y nodejs
                ;;
            "fedora"|"rhel"|"centos")
                curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
                sudo yum install -y nodejs
                ;;
            "arch")
                sudo pacman -Sy nodejs npm
                ;;
            "macos")
                brew install node
                ;;
            *)
                mostrar_erro "Não foi possível instalar Node.js automaticamente. Por favor, instale Node.js 14+ manualmente."
                return 1
                ;;
        esac
    else
        NODE_VERSION=$(node --version | cut -d 'v' -f2 | cut -d '.' -f1)
        mostrar_sucesso "Node.js $(node --version) encontrado"
        
        # Se a versão for menor que 14, sugerir atualização
        if [ "$NODE_VERSION" -lt 14 ]; then
            mostrar_aviso "A versão do Node.js é muito antiga. Recomendamos Node.js 18.x ou superior."
            read -p "Deseja atualizar o Node.js? (S/n): " resposta
            
            if [ "$resposta" != "n" ] && [ "$resposta" != "N" ]; then
                mostrar_progresso "Atualizando Node.js..."
                
                case $OS in
                    "debian"|"ubuntu"|"raspbian"|"linuxmint")
                        # Instalar Node.js via NodeSource
                        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
                        sudo apt-get install -y nodejs
                        ;;
                    "fedora"|"rhel"|"centos")
                        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
                        sudo yum install -y nodejs
                        ;;
                    "arch")
                        sudo pacman -Sy nodejs npm
                        ;;
                    "macos")
                        brew upgrade node
                        ;;
                esac
                
                mostrar_sucesso "Node.js atualizado: $(node --version)"
            fi
        fi
    fi
    
    # Instalar outros pacotes necessários
    case $OS in
        "debian"|"ubuntu"|"raspbian"|"linuxmint")
            mostrar_progresso "Instalando dependências adicionais..."
            sudo apt-get install -y git curl wget xdg-utils
            ;;
        "fedora"|"rhel"|"centos")
            mostrar_progresso "Instalando dependências adicionais..."
            sudo yum install -y git curl wget xdg-utils
            ;;
        "arch")
            mostrar_progresso "Instalando dependências adicionais..."
            sudo pacman -Sy git curl wget xdg-utils
            ;;
        "macos")
            mostrar_progresso "Instalando dependências adicionais..."
            brew install git curl wget
            ;;
    esac
    
    return 0
}

# Criar diretórios necessários
criar_diretorios() {
    mostrar_progresso "Criando diretórios necessários..."
    mkdir -p "$DIR/logs"
    mkdir -p "$DIR/messages"
    mkdir -p "$DIR/storage"
}

# Verificar e instalar dependências Python
instalar_deps_python() {
    mostrar_progresso "Verificando ambiente Python..."
    
    # Verificar se já temos um ambiente virtual
    if [ ! -d "$DIR/venv" ]; then
        mostrar_progresso "Criando ambiente virtual Python..."
        python3 -m venv "$DIR/venv"
        if [ $? -ne 0 ]; then
            mostrar_erro "Falha ao criar ambiente virtual. Instalando python3-venv..."
            sudo apt-get update && sudo apt-get install -y python3-venv
            python3 -m venv "$DIR/venv"
        fi
    fi
    
    # Ativar ambiente virtual
    source "$DIR/venv/bin/activate"
    
    # Instalar dependências Python
    mostrar_progresso "Instalando dependências Python..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        mostrar_sucesso "Dependências Python instaladas com sucesso!"
    else
        mostrar_erro "Falha ao instalar dependências Python."
        return 1
    fi
    
    return 0
}

# Verificar e instalar dependências Node.js
instalar_deps_nodejs() {
    mostrar_progresso "Verificando dependências Node.js..."
    
    # Verificar se o diretório node_modules existe
    if [ ! -d "$DIR/src/whatsapp/node_modules" ] || [ "$REINSTALAR_DEPS" = "true" ]; then
        mostrar_progresso "Instalando dependências do WhatsApp Bot..."
        cd "$DIR/src/whatsapp"
        
        # Limpar qualquer cache ou instalação anterior com problemas
        if [ -d "node_modules" ]; then
            mostrar_progresso "Removendo instalação anterior..."
            rm -rf node_modules
            rm -f package-lock.json
        fi
        
        # Verificar a versão do npm
        NPM_VERSION=$(npm --version)
        mostrar_progresso "Usando npm versão $NPM_VERSION"
        
        # Atualizar npm para a última versão
        mostrar_progresso "Atualizando npm para a versão mais recente..."
        npm install -g npm@latest
        
        # Instalar dependências com opções para contornar problemas comuns
        mostrar_progresso "Instalando dependências do WhatsApp Bot..."
        npm install --no-fund --no-audit --legacy-peer-deps
        
        if [ $? -eq 0 ]; then
            mostrar_sucesso "Dependências Node.js instaladas com sucesso!"
        else
            mostrar_erro "Falha ao instalar dependências Node.js."
            mostrar_progresso "Tentando método alternativo..."
            
            # Tentar método alternativo com yarn se disponível
            if command -v yarn &> /dev/null; then
                mostrar_progresso "Tentando instalar com Yarn..."
                rm -f package-lock.json
                yarn install
                
                if [ $? -eq 0 ]; then
                    mostrar_sucesso "Dependências instaladas com sucesso usando Yarn!"
                else
                    cd "$DIR"
                    return 1
                fi
            else
                cd "$DIR"
                return 1
            fi
        fi
        cd "$DIR"
    else
        mostrar_sucesso "Dependências Node.js já estão instaladas."
    fi
    
    return 0
}

# Verificar se o sistema já está em execução
verificar_execucao() {
    if pgrep -f "python3 src/main.py" > /dev/null; then
        mostrar_aviso "O sistema Chaplain já está em execução!"
        return 1
    fi
    
    return 0
}

# Iniciar o sistema
iniciar_sistema() {
    mostrar_progresso "Iniciando sistema Chaplain..."
    
    # Ativar ambiente virtual se existir
    if [ -d "$DIR/venv" ]; then
        source "$DIR/venv/bin/activate"
    fi
    
    # Detectar porta WhatsApp
    PORT=3000
    DEVTOOLS_PORT_FILE="$DIR/src/whatsapp/whatsapp_session/session/DevToolsActivePort"
    if [ -f "$DEVTOOLS_PORT_FILE" ]; then
        DETECTED_PORT=$(head -n 1 "$DEVTOOLS_PORT_FILE")
        if [[ "$DETECTED_PORT" =~ ^[0-9]+$ ]]; then
            mostrar_sucesso "Porta WhatsApp detectada: $DETECTED_PORT"
            PORT=$DETECTED_PORT
        fi
    fi
    
    # Registrar inicialização
    echo "Iniciando sistema Chaplain em $(date) - Porta: $PORT" >> "$DIR/logs/inicializacao.log"
    
    # Iniciar o sistema
    if [ "$MODO_FOREGROUND" = "true" ]; then
        mostrar_progresso "Iniciando em modo foreground para mostrar o QR code..."
        mostrar_aviso "AGUARDE o QR code aparecer abaixo para escanear com seu WhatsApp:"
        echo ""
        echo "================================================================"
        echo "=                ESCANEIE O QR CODE COM SEU CELULAR            ="
        echo "================================================================"
        echo ""
        
        # Iniciar em primeiro plano para mostrar o QR code
        cd "$DIR/src/whatsapp"
        node whatsapp_bot.js &
        NODE_PID=$!
        
        # Esperar 5 segundos para dar tempo do QR code aparecer
        sleep 5
        
        # Iniciar a aplicação principal
        cd "$DIR"
        python3 src/main.py
        
        # Fechar processo do node quando a aplicação principal fechar
        kill $NODE_PID 2>/dev/null
    else
        # Iniciar em segundo plano
        mostrar_progresso "Iniciando aplicação principal em segundo plano..."
        nohup python3 src/main.py > "$DIR/logs/console_output.log" 2>&1 &
        PID=$!
        
        # Verificar se iniciou corretamente
        sleep 3
        if ps -p $PID > /dev/null; then
            mostrar_sucesso "Sistema iniciado com sucesso! (PID: $PID)"
            echo "Sistema Chaplain iniciado com PID: $PID" >> "$DIR/logs/inicializacao.log"
            
            mostrar_aviso "IMPORTANTE: Para ver o QR code, execute:"
            echo "./instalar_e_iniciar_chaplain.sh --foreground"
            
            return 0
        else
            mostrar_erro "Falha ao iniciar o sistema."
            return 1
        fi
    fi
}

# Menu principal
main() {
    clear
    echo "================================================================"
    echo "             INSTALAÇÃO E INICIALIZAÇÃO DO CHAPLAIN             "
    echo "================================================================"
    echo ""
    
    # Detectar sistema
    detectar_sistema
    
    # Instalar dependências do sistema (Python, Node.js, etc)
    instalar_deps_sistema
    if [ $? -ne 0 ]; then
        mostrar_erro "Falha na instalação das dependências do sistema."
        read -p "Pressione Enter para continuar com a instalação mesmo assim..."
    fi
    
    # Criar diretórios
    criar_diretorios
    
    # Verificar se já está em execução
    verificar_execucao
    if [ $? -ne 0 ]; then
        read -p "Pressione Enter para continuar..."
        exit 1
    fi
    
    # Instalar dependências Python
    instalar_deps_python
    if [ $? -ne 0 ]; then
        mostrar_erro "Falha na instalação das dependências Python."
        read -p "Pressione Enter para continuar..."
        exit 1
    fi
    
    # Instalar dependências Node.js
    instalar_deps_nodejs
    if [ $? -ne 0 ]; then
        mostrar_erro "Falha na instalação das dependências Node.js."
        read -p "Pressione Enter para continuar..."
        exit 1
    fi
    
    # Iniciar o sistema
    iniciar_sistema
    if [ $? -ne 0 ]; then
        mostrar_erro "Falha ao iniciar o sistema."
        read -p "Pressione Enter para continuar..."
        exit 1
    fi
    
    echo ""
    echo "================================================================"
    echo "                 CHAPLAIN INICIADO COM SUCESSO!                 "
    echo "================================================================"
    
    # Exibir instruções
    echo ""
    echo "Para acessar a interface gráfica, abra seu navegador e acesse:"
    echo "http://localhost:5000"
    echo ""
    echo "Para parar o sistema, execute:"
    echo "pkill -f \"python3 src/main.py\""
    echo ""
    echo "Para exibir o QR code no terminal (primeira autenticação), execute:"
    echo "./instalar_e_iniciar_chaplain.sh --foreground"
    echo ""
    echo "Se encontrar problemas com o Node.js, execute:"
    echo "./instalar_e_iniciar_chaplain.sh --reinstall"
    echo ""
    
    # Em ambiente gráfico, mostrar notificação
    if command -v zenity &> /dev/null; then
        zenity --info --title="Chaplain" --text="Sistema iniciado com sucesso!" --width=300 2>/dev/null
    elif command -v notify-send &> /dev/null; then
        notify-send "Chaplain" "Sistema iniciado com sucesso!"
    fi
    
    read -p "Pressione Enter para fechar esta janela..."
}

# Executar o programa principal
main 