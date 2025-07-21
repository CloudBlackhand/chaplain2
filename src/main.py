import os
import sys
import tkinter as tk
from tkinter import messagebox
import threading
import subprocess
import time
import shutil
import json
import signal
import traceback
import requests
from datetime import datetime

# Adicionar diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar depois de adicionar o path
from interface.gui_app import WhatsAppGUI

# Configurações
WHATSAPP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whatsapp")
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
MESSAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "messages")
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")
API_URL = "http://localhost:3000"

# Variáveis globais
whatsapp_process = None
api_process = None
shutdown_flag = False
health_thread = None

def log_event(event_type, message):
    """Registra um evento no log"""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "type": event_type,
            "message": message
        }
        
        log_file = os.path.join(LOGS_DIR, f"system_{datetime.now().strftime('%Y-%m-%d')}.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        print(f"Erro ao registrar log: {str(e)}")

def check_folders():
    """Verifica e cria diretórios necessários"""
    try:
        dirs = [LOGS_DIR, MESSAGES_DIR, STORAGE_DIR]
        for directory in dirs:
            os.makedirs(directory, exist_ok=True)
            print(f"Diretório verificado: {directory}")
        log_event("system", "Diretórios do sistema verificados")
    except Exception as e:
        print(f"Erro ao verificar diretórios: {str(e)}")
        log_event("error", f"Erro ao verificar diretórios: {str(e)}")

def check_node_dependencies():
    """Verifica e instala dependências do Node.js se necessário"""
    try:
        node_modules = os.path.join(WHATSAPP_DIR, "node_modules")
        if not os.path.exists(node_modules) or not os.listdir(node_modules):
            print("Instalando dependências do WhatsApp bot...")
            log_event("system", "Instalando dependências do Node.js")
            
            # Executar npm install
            result = subprocess.run(
                ["npm", "install"],
                cwd=WHATSAPP_DIR,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                error_msg = f"Erro ao instalar dependências: {result.stderr}"
                print(error_msg)
                log_event("error", error_msg)
                return False
            
            print("Dependências instaladas com sucesso.")
            log_event("system", "Dependências do Node.js instaladas com sucesso")
        return True
    except Exception as e:
        error_msg = f"Erro ao verificar/instalar dependências do Node.js: {str(e)}"
        print(error_msg)
        log_event("error", error_msg)
        return False

def start_whatsapp_server():
    """Inicia o servidor WhatsApp em um processo separado"""
    global whatsapp_process
    
    try:
        # Verificar dependências primeiro
        if not check_node_dependencies():
            return False
        
        print("Iniciando servidor WhatsApp...")
        log_event("system", "Iniciando servidor WhatsApp")
        
        # Iniciar processo do Node.js
        whatsapp_process = subprocess.Popen(
            ["node", "whatsapp_bot.js"],
            cwd=WHATSAPP_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Iniciar threads para ler a saída do processo
        threading.Thread(target=read_process_output, 
                        args=(whatsapp_process.stdout, "[WhatsApp]"), 
                        daemon=True).start()
                        
        threading.Thread(target=read_process_output, 
                        args=(whatsapp_process.stderr, "[WhatsApp Error]"), 
                        daemon=True).start()
        
        # Esperar um pouco para garantir que o processo inicie
        time.sleep(2)
        
        # Verificar se o processo ainda está em execução
        if whatsapp_process.poll() is not None:
            print(f"Servidor WhatsApp falhou ao iniciar. Código de saída: {whatsapp_process.poll()}")
            log_event("error", f"Servidor WhatsApp falhou ao iniciar. Código de saída: {whatsapp_process.poll()}")
            return False
            
        return True
    except Exception as e:
        error_msg = f"Erro ao iniciar servidor WhatsApp: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        log_event("error", error_msg)
        return False

def read_process_output(pipe, prefix):
    """Lê a saída de um processo e imprime com prefixo"""
    try:
        for line in iter(pipe.readline, ''):
            if line:
                clean_line = line.strip()
                print(f"{prefix} {clean_line}")
                
                # Registrar erros importantes no log
                if "Error" in clean_line or "error" in clean_line or "Erro" in clean_line:
                    log_event("whatsapp_error", clean_line)
    except Exception as e:
        print(f"Erro ao ler saída do processo: {str(e)}")

def check_whatsapp_health():
    """Verifica a saúde do servidor WhatsApp"""
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        return response.status_code == 200 and response.json().get("status") == "up"
    except Exception:
        return False

def health_check_loop():
    """Loop para verificar a saúde dos processos periodicamente"""
    global shutdown_flag, whatsapp_process
    
    while not shutdown_flag:
        try:
            # Verificar o processo do WhatsApp
            if whatsapp_process and whatsapp_process.poll() is not None:
                print("Servidor WhatsApp parou de responder. Tentando reiniciar...")
                log_event("error", "Servidor WhatsApp parou de responder. Tentando reiniciar...")
                
                # Tentar finalizar o processo antigo se ainda estiver rodando
                try:
                    if whatsapp_process:
                        whatsapp_process.terminate()
                        time.sleep(1)
                        if whatsapp_process.poll() is None:
                            whatsapp_process.kill()
                except Exception as e:
                    print(f"Erro ao finalizar processo antigo: {str(e)}")
                
                # Reiniciar o servidor
                start_whatsapp_server()
            
            # Verificar a API HTTP
            if not check_whatsapp_health():
                print("API do WhatsApp não está respondendo corretamente")
                log_event("warning", "API do WhatsApp não está respondendo corretamente")
            
            # Verificar a cada 30 segundos
            time.sleep(30)
        
        except Exception as e:
            print(f"Erro na verificação de saúde: {str(e)}")
            log_event("error", f"Erro na verificação de saúde: {str(e)}")
            time.sleep(10)  # Esperar um pouco antes de tentar novamente

def cleanup():
    """Limpa recursos e finaliza processos"""
    global shutdown_flag, whatsapp_process
    
    shutdown_flag = True
    
    print("Finalizando processos...")
    log_event("system", "Sistema em processo de desligamento")
    
    # Finalizar processo do WhatsApp
    if whatsapp_process:
        try:
            whatsapp_process.terminate()
            whatsapp_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            whatsapp_process.kill()
        except Exception as e:
            print(f"Erro ao finalizar processo do WhatsApp: {str(e)}")
    
    log_event("system", "Sistema finalizado")
    print("Sistema finalizado com sucesso.")

def handle_sigterm(signum, frame):
    """Manipulador de sinal para encerramento limpo"""
    print("Recebido sinal de encerramento. Finalizando sistema...")
    cleanup()
    sys.exit(0)

def main():
    """Função principal para iniciar o sistema"""
    try:
        global health_thread, API_URL
        
        # Registrar manipuladores de sinal para encerramento limpo
        signal.signal(signal.SIGTERM, handle_sigterm)
        signal.signal(signal.SIGINT, handle_sigterm)
        
        # Registrar evento de inicialização
        log_event("system", "Sistema iniciando")
        print("Iniciando sistema de WhatsApp...")
        
        # Verificar diretórios
        check_folders()
        
        # Detectar porta do WhatsApp ANTES de iniciar qualquer serviço
        try:
            port_file_path = os.path.join(WHATSAPP_DIR, "whatsapp_session", "session", "DevToolsActivePort")
            if os.path.exists(port_file_path):
                with open(port_file_path, 'r') as file:
                    port = file.readline().strip()
                    if port and port.isdigit():
                        API_URL = f"http://localhost:{port}"
                        print(f"Detectada porta do WhatsApp: {port}")
                        log_event("system", f"WhatsApp detectado na porta {port}")
        except Exception as e:
            print(f"Não foi possível detectar a porta do WhatsApp: {str(e)}")
            log_event("warning", f"Falha ao detectar porta do WhatsApp: {str(e)}")
            print("Usando porta padrão 3000")
        
        # Iniciar servidor WhatsApp
        if not start_whatsapp_server():
            print("Falha ao iniciar servidor WhatsApp. O sistema pode não funcionar corretamente.")
        
        # Iniciar thread de verificação de saúde
        health_thread = threading.Thread(target=health_check_loop, daemon=True)
        health_thread.start()
        
        # Aguardar um pouco para o servidor inicializar
        time.sleep(2)
        
        # Iniciar interface gráfica
        root = tk.Tk()
        app = WhatsAppGUI(root)
        
        # Configurar evento de fechamento
        root.protocol("WM_DELETE_WINDOW", lambda: on_close(root))
        
        # Iniciar loop principal da interface
        root.mainloop()
        
    except Exception as e:
        error_msg = f"Erro ao iniciar sistema: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        log_event("error", error_msg)
    finally:
        cleanup()

def on_close(root):
    """Manipulador para o fechamento da janela"""
    if messagebox.askokcancel("Sair", "Deseja realmente sair do sistema?"):
        root.destroy()
        cleanup()

if __name__ == "__main__":
    main() 