import os
import json
import time
import requests
from typing import List, Dict, Any, Optional, Callable
import threading
import glob
from datetime import datetime, timedelta
from queue import Queue, Empty
import traceback

from excel_reader.excel_handler import ExcelHandler
from storage.message_storage import MessageStorage

class WhatsAppManager:
    def __init__(self, excel_path: str, whatsapp_api_url: str = "http://localhost:3000", sheet_name: Optional[str] = None):
        """
        Inicializa o gerenciador de WhatsApp.
        
        Args:
            excel_path: Caminho para o arquivo Excel
            whatsapp_api_url: URL da API do WhatsApp
            sheet_name: Nome da aba mensal (opcional, usa a primeira disponível por padrão)
        """
        self.excel_handler = ExcelHandler(excel_path)
        
        # Se uma aba específica foi solicitada, tentar usá-la
        if sheet_name and sheet_name in self.excel_handler.get_available_sheets():
            self.excel_handler.set_current_sheet(sheet_name)
            
        self.storage = MessageStorage("storage")
        
                # Detectar a porta automaticamente, se falhar, usar a URL padrão
        detected_port = self.detect_whatsapp_port()
        if detected_port:
            self.whatsapp_api_url = f"http://localhost:{detected_port}"
            print(f"WhatsApp API detectada na porta {detected_port}")
        else:
            self.whatsapp_api_url = whatsapp_api_url
            print(f"Usando porta padrão para WhatsApp API: {whatsapp_api_url}")
            
        self.messages_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "messages")
        
        # Garantir que o diretório de mensagens exista
        os.makedirs(self.messages_dir, exist_ok=True)
        
        # Flag para controlar resposta automática
        self.auto_reply_enabled = True
        self.auto_reply_message = "Obrigado pelo feedback!"
        
        # Configuração de delay para mensagens em massa
        self.bulk_message_delay = 90  # 1 minuto e 30 segundos em segundos
        
        # Flags para controle de tarefas em execução
        self._cancel_requested = False
        self._tasks_running = False
        self._current_task = None
        self._task_queue = Queue()
        self._task_results = {}
        
        # Iniciar processamento de mensagens em background
        self.should_process_messages = True
        self.message_thread = threading.Thread(target=self._process_messages_loop)
        self.message_thread.daemon = True
        self.message_thread.start()
        
        # Thread para processamento de tarefas
        self.task_thread = threading.Thread(target=self._process_task_queue)
        self.task_thread.daemon = True
        self.task_thread.start()
        
        # Verificar histórico de mensagens não respondidas
        self._process_historical_messages()
    
    def detect_whatsapp_port(self) -> Optional[int]:
        """
        Detecta automaticamente a porta que o WhatsApp está usando
        através do arquivo DevToolsActivePort.
        
        Returns:
            Número da porta detectada ou None se não for possível detectar
        """
        try:
            # Caminho para o arquivo que contém a porta ativa
            port_file_path = os.path.join(
                os.path.dirname(__file__),
                "whatsapp",
                "whatsapp_session",
                "session",
                "DevToolsActivePort"
            )
            
            if os.path.exists(port_file_path):
                with open(port_file_path, 'r') as file:
                    # A porta está na primeira linha do arquivo
                    port = file.readline().strip()
                    
                    if port and port.isdigit():
                        return int(port)
                        
            return None
        except Exception as e:
            print(f"Erro ao detectar porta do WhatsApp: {str(e)}")
            return None
    
    def _process_task_queue(self):
        """Thread que processa tarefas da fila em background"""
        while self.should_process_messages:  # Usa a mesma flag do loop de mensagens
            try:
                # Esperar por uma nova tarefa
                try:
                    task = self._task_queue.get(timeout=1)
                except Empty:
                    continue
                
                # Marcar tarefa como em execução
                self._tasks_running = True
                self._current_task = task.get("id")
                self._cancel_requested = False
                
                # Executar tarefa
                task_type = task.get("type")
                task_id = task.get("id")
                task_args = task.get("args", {})
                
                try:
                    result = None
                    if task_type == "bulk_messages":
                        result = self._execute_bulk_messages(task_args)
                    # Adicionar outros tipos de tarefas aqui no futuro
                    
                    # Armazenar resultado
                    if task_id:
                        if self._cancel_requested:
                            self._task_results[task_id] = {
                                "success": False,
                                "cancelled": True,
                                "message": "Tarefa cancelada pelo usuário"
                            }
                        else:
                            self._task_results[task_id] = result
                
                except Exception as e:
                    print(f"Erro ao executar tarefa {task_id}: {str(e)}")
                    traceback.print_exc()
                    if task_id:
                        self._task_results[task_id] = {
                            "success": False,
                            "error": str(e),
                            "message": "Erro na execução da tarefa"
                        }
                
                # Limpar estado da tarefa
                self._tasks_running = False
                self._current_task = None
                self._cancel_requested = False
                self._task_queue.task_done()
                
            except Exception as e:
                print(f"Erro no processador de tarefas: {str(e)}")
                time.sleep(5)  # Esperar um pouco em caso de erro
    
    def _execute_bulk_messages(self, args):
        """Executa o envio em massa em background"""
        sa_list = args.get("sa_list")
        message_template = args.get("message_template", "")
        progress_callback = args.get("progress_callback")
        avoid_duplicates = args.get("avoid_duplicates", True)
        
        # Obter contatos da planilha
        contacts = self.excel_handler.get_contacts_by_sa(sa_list)
        
        if not contacts:
            return {"success": False, "message": "Nenhum contato encontrado"}
        
        # Rastrear clientes processados (para evitar duplicações)
        processed_clients = set()
        
        # Preparar lista de mensagens
        message_list = []
        for contact in contacts:
            sa = str(contact.get('SA', ''))
            phone = contact.get('Telefone')
            
            # Verificar duplicatas se solicitado
            if avoid_duplicates and sa in processed_clients:
                print(f"Cliente com SA {sa} já foi processado. Pulando.")
                continue
                
            processed_clients.add(sa)
            
            if not phone:
                print(f"Cliente com SA {sa} não possui número de telefone.")
                continue
            
            # Formatar mensagem personalizada
            personalized_message = message_template
            for key, value in contact.items():
                placeholder = '{' + key.lower() + '}'
                if placeholder in personalized_message:
                    personalized_message = personalized_message.replace(placeholder, str(value))
            
            message_list.append({
                "phone": str(phone),
                "message": personalized_message,
                "sa": sa
            })
        
        # Resultados
        results = []
        total_messages = len(message_list)
        sent_count = 0
        
        # Enviar mensagens uma a uma com delay entre elas
        for index, msg in enumerate(message_list):
            # Verificar se cancelamento foi solicitado
            if self._cancel_requested:
                print("Cancelamento solicitado. Interrompendo envio em massa.")
                break
                
            try:
                # Atualizar progresso
                if progress_callback:
                    progress_callback(index + 1, total_messages)
                
                # Extrair dados
                phone = msg["phone"]
                message = msg["message"]
                sa = msg["sa"]
                
                print(f"Enviando mensagem {index + 1}/{total_messages} para SA {sa}")
                
                # Enviar mensagem individual
                result = self.send_message(phone, message, sa)
                
                results.append({
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                    "phone": phone,
                    "sa": sa
                })
                
                if result.get("success", False):
                    sent_count += 1
                
                # Aguardar delay configurado entre mensagens (exceto após a última)
                if index < total_messages - 1 and not self._cancel_requested:
                    print(f"Aguardando {self.bulk_message_delay} segundos antes da próxima mensagem...")
                    
                    # Aguardar em pequenos incrementos para poder cancelar
                    delay_remaining = self.bulk_message_delay
                    while delay_remaining > 0 and not self._cancel_requested:
                        sleep_time = min(delay_remaining, 1)  # Dormir no máximo 1 segundo por vez
                        time.sleep(sleep_time)
                        delay_remaining -= sleep_time
                
            except Exception as e:
                print(f"Erro ao enviar mensagem para {msg['phone']}: {str(e)}")
                results.append({
                    "success": False,
                    "message": f"Erro: {str(e)}",
                    "phone": msg["phone"],
                    "sa": msg["sa"]
                })
        
        # Resultado final
        return {
            "success": True,
            "results": results,
            "total": total_messages,
            "sent": sent_count,
            "cancelled": self._cancel_requested
        }
    
    def set_sheet(self, sheet_name: str) -> bool:
        """
        Define a aba mensal a ser usada.
        
        Args:
            sheet_name: Nome da aba
            
        Returns:
            True se a aba foi configurada com sucesso
        """
        return self.excel_handler.set_current_sheet(sheet_name)
    
    def get_available_sheets(self) -> List[str]:
        """
        Obtém a lista de abas mensais disponíveis.
        
        Returns:
            Lista de nomes de abas
        """
        return self.excel_handler.get_available_sheets()
    
    def check_whatsapp_status(self) -> Dict[str, Any]:
        """
        Verifica o status do cliente WhatsApp.
        
        Returns:
            Status do cliente
        """
        try:
            response = requests.get(f"{self.whatsapp_api_url}/api/status")
            return response.json()
        except Exception as e:
            print(f"Erro ao verificar status do WhatsApp: {str(e)}")
            return {"ready": False, "error": str(e)}
    
    def send_message(self, phone: str, message: str, sa: Optional[str] = None) -> Dict[str, Any]:
        """
        Envia uma mensagem para um número de telefone.
        
        Args:
            phone: Número de telefone
            message: Mensagem a ser enviada
            sa: Número da SA (opcional)
            
        Returns:
            Resultado do envio
        """
        try:
            payload = {
                "phone": phone,
                "message": message
            }
            
            response = requests.post(
                f"{self.whatsapp_api_url}/api/send-message",
                json=payload
            )
            
            result = response.json()
            
            # Se SA foi fornecido, salvar a mensagem enviada
            if sa and result.get("success"):
                client_info = self.excel_handler.get_client_info_by_sa(sa)
                self.storage.save_sent_message(sa, phone, message, client_info)
                
            return result
        except Exception as e:
            print(f"Erro ao enviar mensagem: {str(e)}")
            return {"success": False, "error": str(e)}

    def set_bulk_message_delay(self, seconds: int) -> None:
        """
        Define o delay entre mensagens em massa.
        
        Args:
            seconds: Tempo em segundos
        """
        self.bulk_message_delay = max(1, seconds)  # Mínimo de 1 segundo
    
    def send_bulk_messages(self, sa_list: Optional[List[str]] = None, 
                          message_template: str = "", 
                          progress_callback: Optional[Callable[[int, int], None]] = None,
                          avoid_duplicates: bool = True) -> Dict[str, Any]:
        """
        Envia mensagens em massa para clientes.
        
        Args:
            sa_list: Lista de SAs para enviar mensagens (opcional)
            message_template: Modelo de mensagem (pode incluir marcadores como {nome}, {endereco}, etc.)
            progress_callback: Função de callback para atualizar progresso (recebe atual, total)
            avoid_duplicates: Evitar enviar para o mesmo cliente mais de uma vez
            
        Returns:
            ID da tarefa em andamento
        """
        if self._tasks_running:
            return {"success": False, "message": "Já existe uma tarefa em andamento"}
        
        # Gerar ID da tarefa
        task_id = f"bulk_{int(time.time())}"
        
        # Criar tarefa na fila
        self._task_queue.put({
            "id": task_id,
            "type": "bulk_messages",
            "args": {
                "sa_list": sa_list,
                "message_template": message_template,
                "progress_callback": progress_callback,
                "avoid_duplicates": avoid_duplicates
            }
        })
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Envio de mensagens iniciado em segundo plano"
        }
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém o resultado de uma tarefa pelo ID.
        
        Args:
            task_id: ID da tarefa
            
        Returns:
            Resultado da tarefa ou None se não encontrado
        """
        result = self._task_results.get(task_id)
        if result:
            # Remover resultado da memória após a consulta (opcional)
            # del self._task_results[task_id]
            return result
        return None
    
    def cancel_current_task(self) -> Dict[str, Any]:
        """
        Cancela a tarefa atualmente em execução.
        
        Returns:
            Resultado da operação de cancelamento
        """
        if not self._tasks_running:
            return {"success": False, "message": "Nenhuma tarefa em andamento"}
            
        self._cancel_requested = True
        return {
            "success": True,
            "message": f"Cancelamento solicitado para a tarefa: {self._current_task}"
        }
    
    def is_task_running(self) -> bool:
        """
        Verifica se há tarefas em execução.
        
        Returns:
            True se houver tarefas em execução
        """
        return self._tasks_running
    
    def _process_messages_loop(self) -> None:
        """Loop para processar mensagens recebidas em segundo plano"""
        while self.should_process_messages:
            self._process_received_messages()
            time.sleep(5)  # Verificar a cada 5 segundos
    
    def _process_received_messages(self) -> None:
        """Processa mensagens recebidas do WhatsApp"""
        try:
            # Buscar arquivos de mensagens
            files = glob.glob(os.path.join(self.messages_dir, "received_*.json"))
            
            for file_path in files:
                try:
                    # Carregar dados da mensagem
                    with open(file_path, 'r', encoding='utf-8') as f:
                        message_data = json.load(f)
                    
                    # Processar mensagem recebida
                    self._process_message(message_data)
                    
                    # Remover arquivo processado
                    os.remove(file_path)
                except Exception as e:
                    print(f"Erro ao processar arquivo {file_path}: {str(e)}")
        except Exception as e:
            print(f"Erro ao processar mensagens recebidas: {str(e)}")
    
    def _process_historical_messages(self) -> None:
        """Processa mensagens históricas para verificar mensagens não respondidas"""
        print("Verificando mensagens históricas não respondidas...")
        try:
            # Obter lista de clientes com mensagens
            clients = self.storage.get_all_clients_with_messages()
            responded_count = 0
            
            for sa in clients:
                # Obter todas as mensagens do cliente
                messages = self.storage.get_client_messages(sa)
                
                # Ordenar por timestamp
                messages.sort(key=lambda x: x.get('timestamp', ''))
                
                # Verificar se última mensagem é recebida e não foi respondida
                if messages and messages[-1].get('type') == 'received':
                    # Verificar se a mensagem é recente (últimas 24 horas)
                    last_msg_time = None
                    try:
                        last_msg_time = datetime.fromisoformat(messages[-1].get('timestamp', ''))
                    except (ValueError, TypeError):
                        continue
                        
                    if last_msg_time and (datetime.now() - last_msg_time) < timedelta(hours=24):
                        # Obter telefone do cliente
                        phone = messages[-1].get('phone')
                        if phone:
                            # Enviar resposta automática
                            client_info = self.storage.get_client_info(sa)
                            nome = client_info.get('Nome', '')
                            personalizada = self.auto_reply_message
                            if nome:
                                personalizada = f"Olá {nome}, {self.auto_reply_message.lower()}"
                            
                            print(f"Enviando resposta automática para SA {sa}, telefone {phone}")
                            result = self.send_message(phone, personalizada, sa)
                            
                            if result.get('success'):
                                responded_count += 1
            
            print(f"Respostas automáticas enviadas: {responded_count}")
                    
        except Exception as e:
            print(f"Erro ao processar mensagens históricas: {str(e)}")
    
    def _process_message(self, message_data: Dict[str, Any]) -> None:
        """
        Processa uma mensagem recebida.
        
        Args:
            message_data: Dados da mensagem
        """
        phone = message_data.get("contactNumber")
        if not phone:
            print("Mensagem sem número de telefone.")
            return
        
        # Buscar SA pelo número de telefone na planilha
        sa = self._find_sa_by_phone(phone)
        
        if sa:
            # Salvar mensagem recebida
            self.storage.save_received_message(
                sa=sa,
                phone=phone,
                message=message_data.get("body", ""),
                received_timestamp=message_data.get("timestamp")
            )
            print(f"Mensagem de {phone} armazenada para SA {sa}")
            
            # Enviar resposta automática se habilitado
            if self.auto_reply_enabled:
                # Obter informações do cliente para personalização
                client_info = self.excel_handler.get_client_info_by_sa(sa)
                nome = client_info.get('Nome', '')
                
                # Personalizar mensagem
                resposta = self.auto_reply_message
                if nome:
                    resposta = f"Olá {nome}, {self.auto_reply_message.lower()}"
                
                # Enviar resposta
                time.sleep(1)  # Pequeno atraso para simular comportamento humano
                print(f"Enviando resposta automática para {phone}")
                self.send_message(phone, resposta, sa)
        else:
            print(f"SA não encontrada para o número {phone}")
    
    def _find_sa_by_phone(self, phone: str) -> Optional[str]:
        """
        Busca o número da SA pelo telefone na planilha.
        
        Args:
            phone: Número de telefone
            
        Returns:
            SA correspondente ou None
        """
        # Esta implementação depende da estrutura da planilha
        # Vamos fazer uma implementação simples
        if self.excel_handler.data is None or self.excel_handler.data.empty:
            return None
        
        # Limpar número de telefone para comparação
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Verificar se a coluna Telefone existe
        if 'Telefone' not in self.excel_handler.data.columns:
            print("Coluna Telefone não encontrada na planilha.")
            return None
        
        # Buscar SA em todas as abas mensais disponíveis
        for sheet_name in self.excel_handler.get_available_sheets():
            # Salvar aba atual
            current_sheet = self.excel_handler.current_sheet
            
            # Mudar temporariamente para a aba que estamos verificando
            if current_sheet is not None:  # Garantir que current_sheet não é None
                # Verificar se sheet_name não é None antes de passar para set_current_sheet
                if sheet_name:
                    self.excel_handler.set_current_sheet(sheet_name)
                    
                    # Buscar em todas as linhas da aba atual
                    for _, row in self.excel_handler.data.iterrows():
                        row_phone = str(row.get('Telefone', ''))
                        row_phone_clean = ''.join(filter(str.isdigit, row_phone))
                        
                        # Comparar números com lógica flexível
                        if row_phone_clean and clean_phone.endswith(row_phone_clean[-8:]):
                            sa = str(row.get('SA', ''))
                            # Restaurar aba original
                            self.excel_handler.set_current_sheet(current_sheet)
                            return sa
                
                # Restaurar aba original
                self.excel_handler.set_current_sheet(current_sheet)
        
        return None
    
    def set_auto_reply(self, enabled: bool, message: Optional[str] = None) -> None:
        """
        Configura a resposta automática.
        
        Args:
            enabled: Se a resposta automática deve ser ativada
            message: Mensagem de resposta automática (opcional)
        """
        self.auto_reply_enabled = enabled
        if message:
            self.auto_reply_message = message
    
    def stop(self) -> None:
        """Para o processamento de mensagens em background"""
        self.should_process_messages = False
        self._cancel_requested = True
        if self.message_thread.is_alive():
            self.message_thread.join(timeout=2)
        if self.task_thread.is_alive():
            self.task_thread.join(timeout=2) 