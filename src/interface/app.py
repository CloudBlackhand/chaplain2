import os
import sys
import json
from typing import List, Dict, Any
from flask import Flask, render_template, request, jsonify, redirect, url_for
import traceback
import requests
from datetime import datetime

# Adicionar diretório pai ao path para importação
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from excel_reader.excel_handler import ExcelHandler
from storage.message_storage import MessageStorage
from whatsapp_manager import WhatsAppManager

app = Flask(__name__)

# Configuração
EXCEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                         "excel", "Rota LAS.xlsx")
WHATSAPP_API_URL = "http://localhost:3000"
WEBHOOK_ENDPOINT = "/webhook/whatsapp"
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")

# Garantir que diretórios existam
os.makedirs(LOG_DIR, exist_ok=True)

# Status do sistema
system_status = {
    "started_at": datetime.now().isoformat(),
    "last_whatsapp_status_check": None,
    "whatsapp_connected": False,
    "messages_received": 0,
    "messages_processed": 0,
    "errors": []
}

# Inicializar gerenciador de WhatsApp
manager = WhatsAppManager(EXCEL_PATH, WHATSAPP_API_URL)

def log_event(event_type, message):
    """Registra um evento de log"""
    try:
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "type": event_type,
            "message": message
        }
        
        # Salvar em arquivo de log
        log_file = os.path.join(LOG_DIR, f"api_{datetime.now().strftime('%Y-%m-%d')}.log")
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Armazenar erros para monitoramento
        if event_type == "error":
            system_status["errors"].append(log_entry)
            if len(system_status["errors"]) > 10:
                system_status["errors"] = system_status["errors"][-10:]
    except Exception as e:
        print(f"Erro ao registrar log: {str(e)}")

@app.route('/')
def index():
    """Página inicial"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Verificação de saúde do sistema"""
    try:
        # Verificar status do WhatsApp
        whatsapp_status = manager.check_whatsapp_status()
        system_status["last_whatsapp_status_check"] = datetime.now().isoformat()
        system_status["whatsapp_connected"] = whatsapp_status.get("ready", False)
        
        # Informações sobre o sistema
        health_data = {
            "status": "up",
            "whatsapp_connected": system_status["whatsapp_connected"],
            "started_at": system_status["started_at"],
            "uptime_seconds": (datetime.now() - datetime.fromisoformat(system_status["started_at"])).total_seconds(),
            "stats": {
                "messages_received": system_status["messages_received"],
                "messages_processed": system_status["messages_processed"],
            },
            "last_errors": system_status["errors"][-3:] if system_status["errors"] else []
        }
        
        return jsonify(health_data)
    except Exception as e:
        traceback.print_exc()
        log_event("error", f"Erro no health check: {str(e)}")
        return jsonify({
            "status": "down",
            "error": str(e)
        }), 500

@app.route('/status')
def status():
    """Verifica status do WhatsApp"""
    try:
        whatsapp_status = manager.check_whatsapp_status()
        system_status["last_whatsapp_status_check"] = datetime.now().isoformat()
        system_status["whatsapp_connected"] = whatsapp_status.get("ready", False)
        return jsonify(whatsapp_status)
    except Exception as e:
        traceback.print_exc()
        log_event("error", f"Erro ao verificar status do WhatsApp: {str(e)}")
        return jsonify({
            "ready": False,
            "error": str(e)
        })

@app.route('/webhook/setup', methods=['POST'])
def setup_webhook():
    """Configura o webhook no serviço WhatsApp"""
    try:
        # Obter URL base da requisição atual
        host_url = request.host_url.rstrip('/')
        webhook_url = f"{host_url}{WEBHOOK_ENDPOINT}"
        
        # Configurar webhook no serviço WhatsApp
        response = requests.post(
            f"{WHATSAPP_API_URL}/api/set-webhook",
            json={"url": webhook_url}
        )
        
        log_event("webhook_setup", f"Webhook configurado para {webhook_url}")
        return jsonify(response.json())
    except Exception as e:
        traceback.print_exc()
        log_event("error", f"Erro ao configurar webhook: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erro ao configurar webhook: {str(e)}"
        }), 500

@app.route(WEBHOOK_ENDPOINT, methods=['POST'])
def webhook_handler():
    """Manipulador de webhook para receber eventos do WhatsApp"""
    try:
        data = request.json
        system_status["messages_received"] += 1
        
        # Verificar se é uma mensagem recebida
        if data and 'from' in data and 'body' in data:
            phone = data.get('contactNumber', '')  # Valor padrão vazio para evitar None
            if not phone:  # Se for None ou string vazia
                log_event("webhook_error", "Número de telefone não fornecido no webhook")
                return jsonify({"success": False, "error": "Número de telefone não fornecido"}), 400
                
            message = data.get('body', '')  # Valor padrão vazio para evitar None
            if not message:  # Se for None ou string vazia
                log_event("webhook_warning", f"Mensagem vazia recebida de {phone}")
            
            # Processar mensagem
            sa = manager._find_sa_by_phone(phone)
            
            if sa:
                # Salvar mensagem no armazenamento
                manager.storage.save_received_message(
                    sa=sa,
                    phone=phone,
                    message=message,
                    received_timestamp=data.get('timestamp', datetime.now().isoformat())
                )
                
                system_status["messages_processed"] += 1
                log_event("webhook_message_processed", f"Mensagem de {phone} processada para SA {sa}")
            else:
                log_event("webhook_message_unmatched", f"SA não encontrada para número {phone}")
        
        return jsonify({"success": True})
    except Exception as e:
        traceback.print_exc()
        log_event("error", f"Erro ao processar webhook: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/clients')
def clients():
    """Lista de clientes"""
    try:
        # Obter lista de SAs
        sa_list = manager.excel_handler.get_all_sa_numbers()
        
        # Obter informações de cada cliente
        clients_data = []
        for sa in sa_list:
            client_info = manager.excel_handler.get_client_info_by_sa(sa)
            if client_info:
                # Adicionar informações sobre mensagens
                messages = manager.storage.get_client_messages(sa)
                client_info['mensagens_enviadas'] = sum(1 for m in messages if m.get('type', '') == 'sent')
                client_info['mensagens_recebidas'] = sum(1 for m in messages if m.get('type', '') == 'received')
                clients_data.append(client_info)
        
        return jsonify({
            "success": True,
            "clients": clients_data
        })
    except Exception as e:
        traceback.print_exc()
        log_event("error", f"Erro ao listar clientes: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/client/<sa>')
def client_detail(sa):
    """Detalhes de um cliente específico"""
    try:
        client_info = manager.excel_handler.get_client_info_by_sa(sa)
        messages = manager.storage.get_client_messages(sa)
        
        return jsonify({
            "success": True,
            "client": client_info,
            "messages": messages
        })
    except Exception as e:
        log_event("error", f"Erro ao buscar detalhes do cliente {sa}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/send-message', methods=['POST'])
def send_message():
    """Enviar mensagem individual"""
    try:
        data = request.json
        sa = data.get('sa')
        message = data.get('message')
        
        if not sa or not message:
            return jsonify({
                "success": False,
                "message": "SA e mensagem são obrigatórios"
            })
        
        # Obter telefone do cliente
        client_info = manager.excel_handler.get_client_info_by_sa(sa)
        phone = client_info.get('Telefone') if client_info else None
        
        if not phone:
            return jsonify({
                "success": False,
                "message": f"Cliente com SA {sa} não possui número de telefone"
            })
        
        # Enviar mensagem
        result = manager.send_message(
            phone=str(phone),
            message=message,
            sa=sa
        )
        
        if result.get("success", False):
            log_event("message_sent", f"Mensagem enviada para SA {sa}")
        else:
            log_event("message_error", f"Erro ao enviar mensagem para SA {sa}: {result.get('message', 'Erro desconhecido')}")
        
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        log_event("error", f"Erro ao enviar mensagem: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/send-bulk', methods=['POST'])
def send_bulk():
    """Enviar mensagens em massa"""
    try:
        data = request.json
        sa_list = data.get('sa_list', [])
        message_template = data.get('message_template', '')
        
        if not message_template:
            return jsonify({
                "success": False,
                "message": "Template de mensagem é obrigatório"
            })
        
        # Enviar mensagens em massa
        result = manager.send_bulk_messages(sa_list, message_template)
        
        if result.get("success", False):
            total_sent = result.get("sent", 0)
            log_event("bulk_message_sent", f"{total_sent} mensagens enviadas em massa")
        else:
            log_event("bulk_message_error", f"Erro ao enviar mensagens em massa: {result.get('message', 'Erro desconhecido')}")
        
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        log_event("error", f"Erro ao enviar mensagens em massa: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.errorhandler(Exception)
def handle_exception(e):
    """Manipulador global de exceções"""
    traceback.print_exc()
    log_event("error", f"Erro não tratado: {str(e)}")
    return jsonify({
        "success": False,
        "message": "Erro interno do servidor",
        "error": str(e)
    }), 500

if __name__ == '__main__':
    # Criar diretório de templates se não existir
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # Iniciar webhook
    try:
        host_url = f"http://localhost:5000"
        webhook_url = f"{host_url}{WEBHOOK_ENDPOINT}"
        requests.post(
            f"{WHATSAPP_API_URL}/api/set-webhook",
            json={"url": webhook_url}
        )
        print(f"Webhook configurado para {webhook_url}")
    except Exception as e:
        print(f"Aviso: Não foi possível configurar webhook automaticamente: {str(e)}")
        print("Você pode configurá-lo manualmente através da rota /webhook/setup")
    
    app.run(debug=True, port=5000) 