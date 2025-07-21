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
    if [ ! -d "$DIR/src/whatsapp/node_modules" ]; then
        mostrar_progresso "Instalando dependências do WhatsApp Bot..."
        cd "$DIR/src/whatsapp"
        npm install
        
        if [ $? -eq 0 ]; then
            mostrar_sucesso "Dependências Node.js instaladas com sucesso!"
        else
            mostrar_erro "Falha ao instalar dependências Node.js."
            cd "$DIR"
            return 1
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
    
    # Iniciar o sistema em segundo plano
    mostrar_progresso "Iniciando aplicação principal..."
    nohup python3 src/main.py > "$DIR/logs/console_output.log" 2>&1 &
    PID=$!
    
    # Verificar se iniciou corretamente
    sleep 3
    if ps -p $PID > /dev/null; then
        mostrar_sucesso "Sistema iniciado com sucesso! (PID: $PID)"
        echo "Sistema Chaplain iniciado com PID: $PID" >> "$DIR/logs/inicializacao.log"
        return 0
    else
        mostrar_erro "Falha ao iniciar o sistema."
        return 1
    fi
}

# Menu principal
main() {
    clear
    echo "================================================================"
    echo "             INSTALAÇÃO E INICIALIZAÇÃO DO CHAPLAIN             "
    echo "================================================================"
    echo ""
    
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