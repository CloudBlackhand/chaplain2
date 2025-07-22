import pandas as pd
import os
from typing import Dict, List, Any, Optional
import re

class ExcelHandler:
    def __init__(self, excel_path: str):
        """
        Inicializa o manipulador de Excel.
        
        Args:
            excel_path: Caminho para o arquivo Excel
        """
        self.excel_path = excel_path
        self.data = None
        self.sheet_data = {}  # Dados de todas as abas por mês
        self.current_sheet = None  # Aba atual em uso
        self._load_data()
    
    def _load_data(self) -> None:
        """Carrega os dados do arquivo Excel, focando nas abas com nomes de meses"""
        try:
            # Identificar todas as abas na planilha
            excel_file = pd.ExcelFile(self.excel_path)
            sheet_names = excel_file.sheet_names
            
            # Filtrar abas com nomes de meses
            month_sheets = self._filter_month_sheets(sheet_names)
            
            if not month_sheets:
                print("Nenhuma aba com nome de mês encontrada na planilha.")
                return
            
            # Carregar dados de cada aba mensal
            for sheet in month_sheets:
                try:
                    self.sheet_data[sheet] = pd.read_excel(self.excel_path, sheet_name=sheet)
                    print(f"Aba '{sheet}' carregada com sucesso. {len(self.sheet_data[sheet])} registros encontrados.")
                except Exception as e:
                    print(f"Erro ao carregar aba '{sheet}': {str(e)}")
            
            # Usar a primeira aba mensal como aba atual por padrão
            if month_sheets:
                self.current_sheet = month_sheets[0]
                self.data = self.sheet_data[self.current_sheet]
                print(f"Usando aba '{self.current_sheet}' como padrão.")
            
        except Exception as e:
            print(f"Erro ao carregar a planilha: {str(e)}")
            self.data = pd.DataFrame()
    
    def _filter_month_sheets(self, sheet_names: List[str]) -> List[str]:
        """
        Filtra abas com nomes de meses em português.
        
        Args:
            sheet_names: Lista com todos os nomes de abas
            
        Returns:
            Lista filtrada com abas de meses
        """
        month_names = [
            'janeiro', 'fevereiro', 'março', 'marco', 'abril', 'maio', 'junho',
            'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
            'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'
        ]
        
        # Também considerar abas com formato "Mês/Ano" como "Janeiro/2023"
        month_pattern = re.compile(r'(?:' + '|'.join(month_names) + r')(?:\s*/?[\d]{0,4})?', re.IGNORECASE)
        
        return [sheet for sheet in sheet_names if month_pattern.search(sheet.lower())]
    
    def set_current_sheet(self, sheet_name: str) -> bool:
        """
        Define a aba atual para trabalhar.
        
        Args:
            sheet_name: Nome da aba para usar
            
        Returns:
            True se a aba foi encontrada e definida, False caso contrário
        """
        if sheet_name in self.sheet_data:
            self.current_sheet = sheet_name
            self.data = self.sheet_data[sheet_name]
            return True
        return False
    
    def get_available_sheets(self) -> List[str]:
        """
        Retorna a lista de abas mensais disponíveis.
        
        Returns:
            Lista de nomes de abas mensais
        """
        return list(self.sheet_data.keys())
    
    def get_contacts_by_sa(self, sa_list: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Obtém contatos filtrados por SA.
        
        Args:
            sa_list: Lista de SAs para filtrar (opcional)
            
        Returns:
            Lista de dicionários com informações dos contatos
        """
        if self.data is None or self.data.empty:
            return []
        
        # Verificar se a coluna SA existe
        if 'SA' not in self.data.columns:
            print("Coluna SA não encontrada na planilha.")
            return []
        
        # Filtrar por SA se fornecido
        filtered_data = self.data if sa_list is None else self.data[self.data['SA'].isin(sa_list)]
        
        # Converter para lista de dicionários
        return filtered_data.to_dict('records')
    
    def get_all_sa_numbers(self) -> List[str]:
        """
        Retorna todas as SAs disponíveis na planilha
        
        Returns:
            Lista de SAs
        """
        if self.data is None or self.data.empty or 'SA' not in self.data.columns:
            return []
            
        return self.data['SA'].dropna().astype(str).tolist()
    
    def get_phone_number_by_sa(self, sa: str) -> Optional[str]:
        """
        Obtém o número de telefone associado a uma SA.
        
        Args:
            sa: Número da SA
            
        Returns:
            Número de telefone ou None se não encontrado
        """
        if self.data is None or self.data.empty:
            return None
            
        if 'SA' not in self.data.columns or 'Telefone' not in self.data.columns:
            print("Colunas SA ou Telefone não encontradas na planilha.")
            return None
            
        result = self.data[self.data['SA'] == sa]['Telefone'].values
        return str(result[0]) if len(result) > 0 else None
    
    def get_client_info_by_sa(self, sa: str) -> Dict[str, Any]:
        """
        Obtém todas as informações de um cliente por SA.
        
        Args:
            sa: Número da SA
            
        Returns:
            Dicionário com informações do cliente
        """
        if self.data is None or self.data.empty:
            return {}
            
        if 'SA' not in self.data.columns:
            print("Coluna SA não encontrada na planilha.")
            return {}
            
        result = self.data[self.data['SA'] == sa]
        return result.to_dict('records')[0] if not result.empty else {}


if __name__ == "__main__":
    # Teste simples da classe
    excel_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                             "excel", "Rota LAS.xlsx")
    handler = ExcelHandler(excel_path)
    
    # Mostrar abas disponíveis
    available_sheets = handler.get_available_sheets()
    print(f"\nAbas mensais disponíveis: {available_sheets}")
    
    # Mostrar as 5 primeiras linhas para verificação
    if handler.data is not None and not handler.data.empty:
        print(f"\nColunas disponíveis na aba '{handler.current_sheet}':")
        print(handler.data.columns.tolist())
        
        print(f"\nPrimeiras 5 linhas da aba '{handler.current_sheet}':")
        print(handler.data.head())
    
    # Testar busca de SAs
    sa_numbers = handler.get_all_sa_numbers()
    if sa_numbers:
        print(f"\nTotal de SAs encontradas: {len(sa_numbers)}")
        print(f"Exemplos de SAs: {sa_numbers[:5]}")
        
        # Testar obtenção de informações de cliente
        if sa_numbers:
            test_sa = sa_numbers[0]
            client_info = handler.get_client_info_by_sa(test_sa)
            print(f"\nInformações do cliente com SA {test_sa}:")
            for key, value in client_info.items():
                print(f"{key}: {value}") 