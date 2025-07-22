import os
import json
import datetime
from typing import Dict, List, Any, Optional

class MessageStorage:
    def __init__(self, storage_dir: str = "storage"):
        """
        Inicializa o sistema de armazenamento de mensagens.
        
        Args:
            storage_dir: Diretório para armazenar as mensagens
        """
        self.storage_dir = storage_dir
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self) -> None:
        """Garante que o diretório de armazenamento exista"""
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def _get_client_file_path(self, sa: str) -> str:
        """
        Obtém o caminho do arquivo para um cliente específico.
        
        Args:
            sa: Número da SA do cliente
            
        Returns:
            Caminho do arquivo
        """
        return os.path.join(self.storage_dir, f"client_{sa}.json")
    
    def save_sent_message(self, sa: str, phone: str, message: str, 
                         client_info: Dict[str, Any]) -> None:
        """
        Salva uma mensagem enviada.
        
        Args:
            sa: Número da SA do cliente
            phone: Número de telefone do cliente
            message: Mensagem enviada
            client_info: Informações adicionais do cliente
        """
        file_path = self._get_client_file_path(sa)
        
        # Carregar dados existentes ou criar novo
        data = self._load_client_data(sa)
        
        # Adicionar informações do cliente se ainda não existirem
        if "client_info" not in data:
            data["client_info"] = client_info
        
        # Inicializar lista de mensagens se não existir
        if "messages" not in data:
            data["messages"] = []
        
        # Adicionar nova mensagem
        message_data = {
            "type": "sent",
            "timestamp": datetime.datetime.now().isoformat(),
            "message": message,
            "phone": phone
        }
        data["messages"].append(message_data)
        
        # Salvar dados
        self._save_client_data(sa, data)
    
    def save_received_message(self, sa: str, phone: str, message: str,
                            received_timestamp: Optional[str] = None) -> None:
        """
        Salva uma mensagem recebida.
        
        Args:
            sa: Número da SA do cliente
            phone: Número de telefone do cliente
            message: Mensagem recebida
            received_timestamp: Timestamp de recebimento (opcional)
        """
        file_path = self._get_client_file_path(sa)
        
        # Carregar dados existentes ou criar novo
        data = self._load_client_data(sa)
        
        # Inicializar lista de mensagens se não existir
        if "messages" not in data:
            data["messages"] = []
        
        # Adicionar nova mensagem
        message_data = {
            "type": "received",
            "timestamp": received_timestamp or datetime.datetime.now().isoformat(),
            "message": message,
            "phone": phone
        }
        data["messages"].append(message_data)
        
        # Salvar dados
        self._save_client_data(sa, data)
    
    def _load_client_data(self, sa: str) -> Dict[str, Any]:
        """
        Carrega dados de cliente do arquivo.
        
        Args:
            sa: Número da SA do cliente
            
        Returns:
            Dados do cliente
        """
        file_path = self._get_client_file_path(sa)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Erro ao carregar dados do cliente {sa}: {str(e)}")
        
        return {}
    
    def _save_client_data(self, sa: str, data: Dict[str, Any]) -> None:
        """
        Salva dados de cliente no arquivo.
        
        Args:
            sa: Número da SA do cliente
            data: Dados a serem salvos
        """
        file_path = self._get_client_file_path(sa)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar dados do cliente {sa}: {str(e)}")
    
    def get_client_messages(self, sa: str) -> List[Dict[str, Any]]:
        """
        Obtém todas as mensagens de um cliente.
        
        Args:
            sa: Número da SA do cliente
            
        Returns:
            Lista de mensagens
        """
        data = self._load_client_data(sa)
        return data.get("messages", [])
    
    def get_client_info(self, sa: str) -> Dict[str, Any]:
        """
        Obtém informações de um cliente.
        
        Args:
            sa: Número da SA do cliente
            
        Returns:
            Informações do cliente
        """
        data = self._load_client_data(sa)
        return data.get("client_info", {})
    
    def get_all_clients_with_messages(self) -> List[str]:
        """
        Obtém lista de todos os clientes com mensagens.
        
        Returns:
            Lista de SAs de clientes
        """
        clients = []
        if not os.path.exists(self.storage_dir):
            return clients
            
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("client_") and filename.endswith(".json"):
                try:
                    sa = filename[7:-5]  # Remover "client_" e ".json"
                    # Verificar se o arquivo tem mensagens
                    file_path = os.path.join(self.storage_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get("messages"):
                            clients.append(sa)
                except Exception as e:
                    print(f"Erro ao processar arquivo {filename}: {str(e)}")
        
        return clients


if __name__ == "__main__":
    # Teste simples da classe
    storage = MessageStorage()
    
    # Simular salvamento de mensagem
    test_sa = "12345"
    test_phone = "5511987654321"
    test_client_info = {
        "SA": test_sa,
        "Nome": "Cliente Teste",
        "Endereço": "Rua de Teste, 123"
    }
    
    storage.save_sent_message(
        test_sa, test_phone, "Olá, esta é uma mensagem de teste!", test_client_info
    )
    
    storage.save_received_message(
        test_sa, test_phone, "Recebi sua mensagem!"
    )
    
    # Recuperar e mostrar mensagens
    messages = storage.get_client_messages(test_sa)
    print(f"\nMensagens para o cliente {test_sa}:")
    for msg in messages:
        print(f"[{msg['type']}] {msg['timestamp']}: {msg['message']}")
    
    # Recuperar info do cliente
    client_info = storage.get_client_info(test_sa)
    print(f"\nInformações do cliente:")
    for key, value in client_info.items():
        print(f"{key}: {value}")
        
    # Testar obtenção de todos os clientes
    all_clients = storage.get_all_clients_with_messages()
    print(f"\nClientes com mensagens: {all_clients}") 