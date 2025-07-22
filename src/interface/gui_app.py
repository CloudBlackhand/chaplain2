import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import pandas as pd
import json
import traceback
from datetime import datetime
import time
from PIL import Image, ImageTk

# Adicionar diretório pai ao path para importação
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from excel_reader.excel_handler import ExcelHandler
from storage.message_storage import MessageStorage
from whatsapp_manager import WhatsAppManager

class WhatsAppGUI:
    def __init__(self, root):
        """
        Inicializa a interface gráfica.
        
        Args:
            root: Janela principal do Tkinter
        """
        self.root = root
        self.root.title("Sistema de Envio de Mensagens WhatsApp")
        # Tamanho reduzido para caber melhor na tela
        self.root.geometry("900x600")
        self.root.minsize(800, 500)
        
        # Permitir que a janela seja redimensionável
        self.root.resizable(True, True)
        
        # Variáveis
        self.excel_path = tk.StringVar()
        self.whatsapp_api_url = tk.StringVar(value="http://localhost:3000")
        self.selected_sa = tk.StringVar()
        self.search_query = tk.StringVar()
        self.message_template = tk.StringVar()
        self.status_text = tk.StringVar(value="Aguardando carregamento...")
        self.selected_sheet = tk.StringVar()
        self.auto_reply_enabled = tk.BooleanVar(value=True)
        self.auto_reply_message = tk.StringVar(value="Obrigado pelo feedback!")
        self.bulk_delay_minutes = tk.IntVar(value=1)
        self.bulk_delay_seconds = tk.IntVar(value=30)
        
        # Flag para operação em andamento
        self.is_sending_bulk = False
        
        # Variáveis para controle de tarefas
        self.current_task_id = None
        self.monitoring_task = False
        
        # Iniciar monitoramento de tarefas
        self.task_monitor_thread = None
        
        # Gerenciadores
        self.excel_handler = None
        self.whatsapp_manager = None
        
        # Configurar interface
        self._setup_ui()
        
        # Iniciar verificação de status em segundo plano
        self.status_thread = threading.Thread(target=self._check_whatsapp_status_loop, daemon=True)
        self.status_thread.start()
    
    def _setup_ui(self):
        """Configura os elementos da interface"""
        # Criar notebook (abas)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Aba 1: Configuração
        self.config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="Configuração")
        self._setup_config_tab()
        
        # Aba 2: Lista de Clientes
        self.clients_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.clients_frame, text="Lista de Clientes")
        self._setup_clients_tab()
        
        # Aba 3: Envio de Mensagens
        self.messages_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.messages_frame, text="Envio de Mensagens")
        self._setup_messages_tab()
        
        # Aba 4: Histórico
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="Histórico de Mensagens")
        self._setup_history_tab()
        
        # Aba 5: Configurações de Automação
        self.automation_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.automation_frame, text="Automação")
        self._setup_automation_tab()
        
        # Barra de status
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(self.status_bar, textvariable=self.status_text)
        self.status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.whatsapp_status_label = ttk.Label(self.status_bar, text="WhatsApp: Desconectado", foreground="red")
        self.whatsapp_status_label.pack(side=tk.RIGHT, padx=5, pady=2)
    
    def _setup_config_tab(self):
        """Configura a aba de configuração"""
        # Usar um Canvas com scrollbar para permitir rolagem em telas menores
        canvas = tk.Canvas(self.config_frame)
        scrollbar = ttk.Scrollbar(self.config_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        frame = ttk.Frame(scrollable_frame, padding=10)
        frame.pack(fill='both', expand=True)
        
        # Seleção de arquivo Excel
        ttk.Label(frame, text="Arquivo Excel:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.excel_path, width=40).grid(row=0, column=1, sticky=tk.W+tk.E, pady=5, padx=5)
        ttk.Button(frame, text="Selecionar...", command=self._select_excel_file).grid(row=0, column=2, sticky=tk.W, pady=5)
        
        # Seleção de aba mensal
        ttk.Label(frame, text="Aba Mensal:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.sheet_combo = ttk.Combobox(frame, textvariable=self.selected_sheet, state="readonly", width=20)
        self.sheet_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Button(frame, text="Carregar Aba", command=self._load_selected_sheet).grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # URL da API do WhatsApp
        ttk.Label(frame, text="URL da API WhatsApp:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.whatsapp_api_url, width=40).grid(row=2, column=1, sticky=tk.W+tk.E, pady=5, padx=5)
        
        # Botão para iniciar WhatsApp
        ttk.Button(frame, text="Iniciar WhatsApp Bot", command=self._start_whatsapp_bot).grid(row=3, column=0, columnspan=3, pady=10)
        
        # Quadro de informações
        info_frame = ttk.LabelFrame(frame, text="Informações do Sistema")
        info_frame.grid(row=4, column=0, columnspan=3, sticky=tk.W+tk.E, pady=10)
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=10, width=60, wrap=tk.WORD)
        self.info_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.info_text.insert(tk.END, "Sistema de Envio de Mensagens WhatsApp\n\n")
        self.info_text.insert(tk.END, "Instruções:\n")
        self.info_text.insert(tk.END, "1. Selecione o arquivo Excel com os dados dos clientes\n")
        self.info_text.insert(tk.END, "2. Selecione a aba mensal desejada\n")
        self.info_text.insert(tk.END, "3. Inicie o bot do WhatsApp\n")
        self.info_text.insert(tk.END, "4. Escaneie o código QR no terminal\n")
        self.info_text.insert(tk.END, "5. Use as abas para gerenciar clientes e enviar mensagens\n\n")
        self.info_text.configure(state='disabled')
    
    def _setup_clients_tab(self):
        """Configura a aba de lista de clientes"""
        frame = ttk.Frame(self.clients_frame, padding=10)
        frame.pack(fill='both', expand=True)
        
        # Frame de pesquisa
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="Pesquisar:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(search_frame, textvariable=self.search_query, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Buscar", command=self._search_clients).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Atualizar Lista", command=self._refresh_clients).pack(side=tk.RIGHT, padx=5)
        
        # Criar um frame para conter a tabela e a barra de rolagem
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill='both', expand=True, pady=5)
        
        # Tabela de clientes
        self.clients_tree = ttk.Treeview(table_frame, columns=("sa", "nome", "telefone", "endereco", "enviadas", "recebidas"), show='headings')
        
        # Configurar colunas
        self.clients_tree.heading("sa", text="SA")
        self.clients_tree.heading("nome", text="Nome")
        self.clients_tree.heading("telefone", text="Telefone")
        self.clients_tree.heading("endereco", text="Endereço")
        self.clients_tree.heading("enviadas", text="Enviadas")
        self.clients_tree.heading("recebidas", text="Recebidas")
        
        self.clients_tree.column("sa", width=60, minwidth=50)
        self.clients_tree.column("nome", width=150, minwidth=100)
        self.clients_tree.column("telefone", width=100, minwidth=80)
        self.clients_tree.column("endereco", width=200, minwidth=120)
        self.clients_tree.column("enviadas", width=60, minwidth=50)
        self.clients_tree.column("recebidas", width=60, minwidth=50)
        
        # Barra de rolagem vertical
        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.clients_tree.yview)
        self.clients_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Barra de rolagem horizontal
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.clients_tree.xview)
        self.clients_tree.configure(xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.clients_tree.pack(side=tk.LEFT, fill='both', expand=True)
        
        # Evento de clique
        self.clients_tree.bind("<Double-1>", self._on_client_select)
    
    def _setup_messages_tab(self):
        """Configura a aba de envio de mensagens"""
        # Usar um Canvas com scrollbar para permitir rolagem
        canvas = tk.Canvas(self.messages_frame)
        scrollbar = ttk.Scrollbar(self.messages_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        frame = ttk.Frame(scrollable_frame, padding=10)
        frame.pack(fill='both', expand=True)
        
        # Seleção de cliente
        client_frame = ttk.LabelFrame(frame, text="Seleção de Cliente")
        client_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(client_frame, text="SA do Cliente:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(client_frame, textvariable=self.selected_sa, width=15).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(client_frame, text="Carregar Cliente", command=self._load_client_info).grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Informações do cliente
        self.client_info_label = ttk.Label(client_frame, text="Nenhum cliente selecionado")
        self.client_info_label.grid(row=0, column=3, sticky=tk.W, padx=20, pady=5)
        
        # Template de mensagem
        template_frame = ttk.LabelFrame(frame, text="Template de Mensagem")
        template_frame.pack(fill='both', expand=True, pady=10)
        
        ttk.Label(template_frame, text="Você pode usar variáveis da planilha como {nome}, {endereco}, etc.").pack(anchor=tk.W, padx=5, pady=5)
        
        self.template_text = scrolledtext.ScrolledText(template_frame, height=8, wrap=tk.WORD)
        self.template_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Exemplos de template
        ttk.Button(template_frame, text="Inserir Template Exemplo", command=self._insert_template_example).pack(anchor=tk.W, padx=5, pady=5)
        
        # Visualização de mensagem
        preview_frame = ttk.LabelFrame(frame, text="Pré-visualização")
        preview_frame.pack(fill='both', expand=True, pady=10)
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=6, wrap=tk.WORD)
        self.preview_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        ttk.Button(preview_frame, text="Gerar Pré-visualização", command=self._generate_preview).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Progresso do envio em massa
        progress_frame = ttk.LabelFrame(frame, text="Progresso de Envio")
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Adicionar indicador de status da tarefa
        self.task_status_label = ttk.Label(progress_frame, text="")
        self.task_status_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Botões de envio
        send_frame = ttk.Frame(frame)
        send_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(send_frame, text="Enviar para o Cliente Selecionado", command=self._send_to_selected).pack(side=tk.LEFT, padx=5)
        
        button_frame_right = ttk.Frame(send_frame)
        button_frame_right.pack(side=tk.RIGHT, padx=5)
        
        self.send_all_button = ttk.Button(button_frame_right, text="Enviar para Todos os Clientes", command=self._send_to_all)
        self.send_all_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(button_frame_right, text="Cancelar Envio", command=self._cancel_bulk_send, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
    
    def _setup_history_tab(self):
        """Configura a aba de histórico de mensagens"""
        frame = ttk.Frame(self.history_frame, padding=10)
        frame.pack(fill='both', expand=True)
        
        # Dividir a tela em dois painéis
        panel_frame = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        panel_frame.pack(fill='both', expand=True)
        
        # Painel da esquerda - Lista de SAs com histórico
        left_frame = ttk.Frame(panel_frame)
        panel_frame.add(left_frame, weight=1)
        
        # Título e botão para atualizar
        header_frame = ttk.Frame(left_frame)
        header_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(header_frame, text="SAs com histórico:").pack(side=tk.LEFT, padx=5)
        ttk.Button(header_frame, text="Atualizar", command=self._load_history_list).pack(side=tk.RIGHT, padx=5)
        
        # Lista de SAs
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True, pady=5)
        
        # Criar listbox com scrollbar
        self.history_list = tk.Listbox(list_frame, width=20)
        scrollbar_list = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_list.yview)
        self.history_list.configure(yscrollcommand=scrollbar_list.set)
        
        scrollbar_list.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_list.pack(side=tk.LEFT, fill='both', expand=True)
        
        # Vincular evento de seleção
        self.history_list.bind('<<ListboxSelect>>', self._on_history_sa_select)
        
        # Painel da direita - Histórico de mensagens
        right_frame = ttk.Frame(panel_frame)
        panel_frame.add(right_frame, weight=3)
        
        # Informações do cliente selecionado
        self.history_client_info = ttk.Label(right_frame, text="Selecione uma SA para ver o histórico")
        self.history_client_info.pack(fill=tk.X, pady=5, padx=5)
        
        # Histórico de mensagens
        self.history_text = scrolledtext.ScrolledText(right_frame, height=20, wrap=tk.WORD)
        self.history_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Botões de ação
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Button(button_frame, text="Exportar Histórico", command=self._export_history).pack(side=tk.RIGHT, padx=5)
    
    def _setup_automation_tab(self):
        """Configura a aba de automação"""
        frame = ttk.Frame(self.automation_frame, padding=10)
        frame.pack(fill='both', expand=True)
        
        # Frame para resposta automática
        auto_reply_frame = ttk.LabelFrame(frame, text="Resposta Automática")
        auto_reply_frame.pack(fill='both', expand=True, pady=10)
        
        # Checkbox para habilitar/desabilitar
        ttk.Checkbutton(auto_reply_frame, text="Habilitar resposta automática", 
                      variable=self.auto_reply_enabled,
                      command=self._update_auto_reply).pack(anchor=tk.W, padx=10, pady=10)
        
        # Entrada de texto para mensagem
        ttk.Label(auto_reply_frame, text="Mensagem de resposta:").pack(anchor=tk.W, padx=10, pady=5)
        
        msg_frame = ttk.Frame(auto_reply_frame)
        msg_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.auto_reply_text = ttk.Entry(msg_frame, textvariable=self.auto_reply_message, width=50)
        self.auto_reply_text.pack(side=tk.LEFT, fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(msg_frame, text="Aplicar", command=self._update_auto_reply).pack(side=tk.RIGHT)
        
        # Informações sobre variáveis disponíveis
        info_frame = ttk.LabelFrame(auto_reply_frame, text="Informações")
        info_frame.pack(fill='both', expand=True, pady=10, padx=10)
        
        info_text = ("A mensagem de resposta automática será enviada sempre que uma nova mensagem for recebida.\n\n"
                    "Ela também será enviada para mensagens recebidas enquanto o sistema estava desligado.\n\n"
                    "O nome do cliente será automaticamente adicionado quando disponível.")
                    
        info_label = ttk.Label(info_frame, text=info_text, wraplength=600)
        info_label.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Frame para configuração de envio em massa
        bulk_config_frame = ttk.LabelFrame(frame, text="Configurações de Envio em Massa")
        bulk_config_frame.pack(fill='both', expand=True, pady=10)
        
        # Delay entre mensagens
        delay_frame = ttk.Frame(bulk_config_frame)
        delay_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(delay_frame, text="Delay entre mensagens:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Spinbox para minutos e segundos
        minutes_frame = ttk.Frame(delay_frame)
        minutes_frame.grid(row=0, column=1, padx=5)
        
        ttk.Spinbox(minutes_frame, from_=0, to=10, width=3, textvariable=self.bulk_delay_minutes).pack(side=tk.LEFT)
        ttk.Label(minutes_frame, text="min").pack(side=tk.LEFT)
        
        seconds_frame = ttk.Frame(delay_frame)
        seconds_frame.grid(row=0, column=2, padx=5)
        
        ttk.Spinbox(seconds_frame, from_=0, to=59, width=3, textvariable=self.bulk_delay_seconds).pack(side=tk.LEFT)
        ttk.Label(seconds_frame, text="seg").pack(side=tk.LEFT)
        
        ttk.Button(delay_frame, text="Aplicar", command=self._update_bulk_delay).grid(row=0, column=3, padx=10)
        
        # Explicação do delay
        ttk.Label(bulk_config_frame, text="Um delay maior entre mensagens reduz o risco de bloqueio do WhatsApp.", 
                wraplength=600).pack(anchor=tk.W, padx=10, pady=5)
        
        # Frame para outras configurações de automação
        other_config_frame = ttk.LabelFrame(frame, text="Outras Configurações")
        other_config_frame.pack(fill='both', expand=True, pady=10)
        
        ttk.Label(other_config_frame, text="Verificar mensagens a cada (segundos):").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        self.check_interval = ttk.Spinbox(other_config_frame, from_=1, to=60, width=5)
        self.check_interval.set(5)
        self.check_interval.grid(row=0, column=1, sticky=tk.W, padx=10, pady=10)
        
        ttk.Button(other_config_frame, text="Verificar Mensagens Agora", 
                 command=self._process_historical_now).grid(row=1, column=0, columnspan=2, pady=10)
    
    def _select_excel_file(self):
        """Abre diálogo para selecionar arquivo Excel"""
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo Excel",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.excel_path.set(file_path)
            self._load_excel_file(file_path)
    
    def _load_excel_file(self, file_path):
        """Carrega o arquivo Excel selecionado"""
        try:
            # Atualizar status
            self.status_text.set("Carregando arquivo Excel...")
            self.root.update_idletasks()
            
            # Inicializar handler Excel
            self.excel_handler = ExcelHandler(file_path)
            
            if self.excel_handler.data is not None and not self.excel_handler.data.empty:
                # Mostrar informações
                self.info_text.configure(state='normal')
                self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Arquivo Excel carregado: {os.path.basename(file_path)}\n")
                
                # Atualizar combobox com abas mensais disponíveis
                available_sheets = self.excel_handler.get_available_sheets()
                self.sheet_combo["values"] = available_sheets
                
                if available_sheets and self.excel_handler.current_sheet:
                    self.selected_sheet.set(self.excel_handler.current_sheet)
                    self.info_text.insert(tk.END, f"Abas mensais encontradas: {', '.join(available_sheets)}\n")
                    self.info_text.insert(tk.END, f"Aba atual: {self.excel_handler.current_sheet}\n")
                    self.info_text.insert(tk.END, f"Total de registros: {len(self.excel_handler.data)}\n")
                    self.info_text.insert(tk.END, f"Colunas disponíveis: {', '.join(self.excel_handler.data.columns.tolist())}\n")
                else:
                    self.info_text.insert(tk.END, "Nenhuma aba mensal encontrada na planilha.\n")
                    
                self.info_text.see(tk.END)
                self.info_text.configure(state='disabled')
                
                # Atualizar status
                self.status_text.set(f"Arquivo Excel carregado: {len(self.excel_handler.data)} registros")
                
                # Carregar lista de clientes
                self._refresh_clients()
            else:
                messagebox.showerror("Erro", "Não foi possível carregar o arquivo Excel ou o arquivo está vazio.")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao carregar o arquivo Excel:\n{str(e)}")
    
    def _load_selected_sheet(self):
        """Carrega a aba mensal selecionada"""
        if not self.excel_handler:
            messagebox.showerror("Erro", "Selecione um arquivo Excel primeiro.")
            return
            
        sheet_name = self.selected_sheet.get()
        
        if not sheet_name:
            messagebox.showinfo("Aviso", "Selecione uma aba mensal.")
            return
            
        try:
            # Definir aba atual
            if self.excel_handler.set_current_sheet(sheet_name):
                # Mostrar informações
                self.info_text.configure(state='normal')
                self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Aba '{sheet_name}' carregada\n")
                self.info_text.insert(tk.END, f"Total de registros: {len(self.excel_handler.data)}\n")
                self.info_text.see(tk.END)
                self.info_text.configure(state='disabled')
                
                # Atualizar status
                self.status_text.set(f"Aba '{sheet_name}' carregada: {len(self.excel_handler.data)} registros")
                
                # Atualizar lista de clientes
                self._refresh_clients()
            else:
                messagebox.showerror("Erro", f"Aba '{sheet_name}' não encontrada.")
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao carregar aba '{sheet_name}':\n{str(e)}")
    
    def _start_whatsapp_bot(self):
        """Inicia o bot do WhatsApp"""
        if not self.excel_handler:
            messagebox.showerror("Erro", "Selecione um arquivo Excel primeiro.")
            return
            
        try:
            # Atualizar status
            self.status_text.set("Iniciando WhatsApp Bot...")
            self.root.update_idletasks()
            
            # Tentar detectar a porta automaticamente
            try:
                port_file_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "whatsapp",
                    "whatsapp_session",
                    "session",
                    "DevToolsActivePort"
                )
                
                if os.path.exists(port_file_path):
                    with open(port_file_path, 'r') as file:
                        port = file.readline().strip()
                        if port and port.isdigit():
                            self.whatsapp_api_url.set(f"http://localhost:{port}")
                            self.info_text.configure(state='normal')
                            self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Porta do WhatsApp detectada: {port}\n")
                            self.info_text.see(tk.END)
                            self.info_text.configure(state='disabled')
            except Exception as e:
                self.info_text.configure(state='normal')
                self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Não foi possível detectar a porta: {str(e)}\n")
                self.info_text.see(tk.END)
                self.info_text.configure(state='disabled')
                print(f"Erro ao detectar porta do WhatsApp: {str(e)}")
            
            # Inicializar gerenciador de WhatsApp
            self.whatsapp_manager = WhatsAppManager(
                self.excel_path.get(),
                self.whatsapp_api_url.get()
            )
            
            # Configurar resposta automática
            self.whatsapp_manager.set_auto_reply(
                self.auto_reply_enabled.get(),
                self.auto_reply_message.get()
            )
            
            # Informar usuário
            self.info_text.configure(state='normal')
            self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Bot do WhatsApp iniciado\n")
            self.info_text.insert(tk.END, "Por favor, verifique o terminal e escaneie o código QR para autenticar o WhatsApp.\n")
            self.info_text.see(tk.END)
            self.info_text.configure(state='disabled')
            
            messagebox.showinfo("WhatsApp Bot", "Bot iniciado! Verifique o terminal e escaneie o código QR para autenticar o WhatsApp.")
            
            # Inicializar lista de histórico
            if hasattr(self, 'history_list'):
                self._load_history_list()
            
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao iniciar o bot do WhatsApp:\n{str(e)}")
    
    def _check_whatsapp_status_loop(self):
        """Loop para verificar o status do WhatsApp em segundo plano"""
        while True:
            if self.whatsapp_manager:
                try:
                    status = self.whatsapp_manager.check_whatsapp_status()
                    
                    if status.get("ready"):
                        self.root.after(0, lambda: self.whatsapp_status_label.config(
                            text="WhatsApp: Conectado", foreground="green"))
                    elif status.get("qrCode"):
                        self.root.after(0, lambda: self.whatsapp_status_label.config(
                            text="WhatsApp: Aguardando QR Code", foreground="orange"))
                    else:
                        self.root.after(0, lambda: self.whatsapp_status_label.config(
                            text="WhatsApp: Desconectado", foreground="red"))
                
                except Exception:
                    pass
            
            time.sleep(5)
    
    def _refresh_clients(self):
        """Atualiza a lista de clientes"""
        if not self.excel_handler:
            return
            
        try:
            # Limpar tabela
            for item in self.clients_tree.get_children():
                self.clients_tree.delete(item)
                
            # Obter dados dos clientes
            sa_list = self.excel_handler.get_all_sa_numbers()
            
            # Preencher tabela
            for sa in sa_list:
                client_info = self.excel_handler.get_client_info_by_sa(sa)
                
                if not client_info:
                    continue
                    
                # Obter informações de mensagens
                messages = []
                if self.whatsapp_manager:
                    storage = self.whatsapp_manager.storage
                    messages = storage.get_client_messages(sa)
                
                sent_count = sum(1 for m in messages if m['type'] == 'sent')
                received_count = sum(1 for m in messages if m['type'] == 'received')
                
                # Valores padrão para colunas que podem não existir
                nome = client_info.get('Nome', '')
                telefone = client_info.get('Telefone', '')
                endereco = client_info.get('Endereço', '')
                
                self.clients_tree.insert('', tk.END, values=(
                    sa, nome, telefone, endereco, sent_count, received_count
                ))
                
            # Também atualizar a lista de histórico se estiver disponível
            if hasattr(self, 'history_list') and self.whatsapp_manager:
                self._load_history_list()
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao atualizar lista de clientes:\n{str(e)}")
    
    def _search_clients(self):
        """Pesquisa clientes na tabela"""
        query = self.search_query.get().lower()
        
        if not query:
            self._refresh_clients()
            return
            
        try:
            # Limpar tabela
            for item in self.clients_tree.get_children():
                self.clients_tree.delete(item)
                
            # Obter dados dos clientes
            sa_list = self.excel_handler.get_all_sa_numbers()
            
            # Filtrar e preencher tabela
            for sa in sa_list:
                client_info = self.excel_handler.get_client_info_by_sa(sa)
                
                if not client_info:
                    continue
                    
                # Verificar se algum campo contém a consulta
                found = False
                for key, value in client_info.items():
                    if query in str(value).lower():
                        found = True
                        break
                        
                if not found:
                    continue
                    
                # Obter informações de mensagens
                messages = []
                if self.whatsapp_manager:
                    storage = self.whatsapp_manager.storage
                    messages = storage.get_client_messages(sa)
                
                sent_count = sum(1 for m in messages if m['type'] == 'sent')
                received_count = sum(1 for m in messages if m['type'] == 'received')
                
                # Valores padrão para colunas que podem não existir
                nome = client_info.get('Nome', '')
                telefone = client_info.get('Telefone', '')
                endereco = client_info.get('Endereço', '')
                
                self.clients_tree.insert('', tk.END, values=(
                    sa, nome, telefone, endereco, sent_count, received_count
                ))
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao pesquisar clientes:\n{str(e)}")
    
    def _on_client_select(self, event):
        """Manipula o evento de seleção de cliente na tabela"""
        selection = self.clients_tree.selection()
        if selection:
            item = self.clients_tree.item(selection[0])
            sa = item['values'][0]
            self.selected_sa.set(sa)
            self._load_client_info()
            
            # Alternar para a aba de envio de mensagens
            self.notebook.select(2)  # Índice da aba de mensagens
    
    def _load_client_info(self):
        """Carrega informações do cliente selecionado"""
        sa = self.selected_sa.get()
        
        if not sa or not self.excel_handler:
            return
            
        try:
            client_info = self.excel_handler.get_client_info_by_sa(sa)
            
            if client_info:
                # Atualizar rótulo de informações do cliente
                nome = client_info.get('Nome', 'N/A')
                telefone = client_info.get('Telefone', 'N/A')
                endereco = client_info.get('Endereço', 'N/A')
                
                info_text = f"Cliente: {nome} | Telefone: {telefone} | Endereço: {endereco}"
                self.client_info_label.config(text=info_text)
            else:
                self.client_info_label.config(text="Cliente não encontrado")
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao carregar informações do cliente:\n{str(e)}")
    
    def _insert_template_example(self):
        """Insere um exemplo de template de mensagem"""
        template = (
            "Olá {nome},\n\n"
            "Gostaríamos de informar que seu serviço (SA: {sa}) está agendado para o endereço:\n"
            "{endereco}\n\n"
            "Em caso de dúvidas, por favor, entre em contato conosco.\n\n"
            "Atenciosamente,\nEquipe de Suporte"
        )
        
        self.template_text.delete(1.0, tk.END)
        self.template_text.insert(tk.END, template)
    
    def _generate_preview(self):
        """Gera uma prévia da mensagem com os dados do cliente"""
        template = self.template_text.get(1.0, tk.END)
        sa = self.selected_sa.get()
        
        if not template or not sa or not self.excel_handler:
            messagebox.showinfo("Aviso", "Selecione um cliente e defina um template de mensagem.")
            return
            
        try:
            client_info = self.excel_handler.get_client_info_by_sa(sa)
            
            if not client_info:
                messagebox.showinfo("Aviso", "Cliente não encontrado.")
                return
                
            # Formatar mensagem personalizada
            personalized_message = template
            for key, value in client_info.items():
                placeholder = '{' + key.lower() + '}'
                if placeholder in personalized_message:
                    personalized_message = personalized_message.replace(placeholder, str(value))
            
            # Mostrar prévia
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, personalized_message)
            
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao gerar prévia da mensagem:\n{str(e)}")
    
    def _send_to_selected(self):
        """Envia a mensagem para o cliente selecionado"""
        if not self.whatsapp_manager:
            messagebox.showinfo("Aviso", "Inicie o bot do WhatsApp primeiro.")
            return
            
        sa = self.selected_sa.get()
        template = self.template_text.get(1.0, tk.END)
        
        if not sa or not template:
            messagebox.showinfo("Aviso", "Selecione um cliente e defina um template de mensagem.")
            return
            
        try:
            # Verificar status do WhatsApp
            status = self.whatsapp_manager.check_whatsapp_status()
            if not status.get("ready"):
                messagebox.showinfo("Aviso", "WhatsApp não está pronto. Verifique a conexão.")
                return
            
            # Obter informações do cliente
            client_info = self.excel_handler.get_client_info_by_sa(sa)
            
            if not client_info:
                messagebox.showinfo("Aviso", "Cliente não encontrado.")
                return
                
            phone = client_info.get('Telefone')
            
            if not phone:
                messagebox.showinfo("Aviso", f"Cliente com SA {sa} não possui número de telefone.")
                return
                
            # Formatar mensagem personalizada
            personalized_message = template
            for key, value in client_info.items():
                placeholder = '{' + key.lower() + '}'
                if placeholder in personalized_message:
                    personalized_message = personalized_message.replace(placeholder, str(value))
            
            # Enviar mensagem
            result = self.whatsapp_manager.send_message(
                phone=str(phone),
                message=personalized_message,
                sa=sa
            )
            
            if result.get("success"):
                messagebox.showinfo("Sucesso", "Mensagem enviada com sucesso!")
                
                # Atualizar log
                self.info_text.configure(state='normal')
                self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Mensagem enviada para {client_info.get('Nome', sa)}\n")
                self.info_text.see(tk.END)
                self.info_text.configure(state='disabled')
            else:
                messagebox.showerror("Erro", f"Erro ao enviar mensagem: {result.get('message', 'Erro desconhecido')}")
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao enviar mensagem:\n{str(e)}")
    
    def _start_task_monitor(self, task_id):
        """Inicia monitoramento de uma tarefa em background"""
        self.current_task_id = task_id
        self.monitoring_task = True
        
        if self.task_monitor_thread and self.task_monitor_thread.is_alive():
            # Já há um monitor rodando, não criar outro
            return
        
        self.task_monitor_thread = threading.Thread(
            target=self._monitor_task_progress,
            daemon=True
        )
        self.task_monitor_thread.start()
    
    def _monitor_task_progress(self):
        """Thread para monitorar progresso de tarefas em background"""
        try:
            while self.monitoring_task and self.current_task_id and self.whatsapp_manager:
                # Verificar se o gerenciador ainda está rodando uma tarefa
                is_running = self.whatsapp_manager.is_task_running()
                
                # Verificar se há resultado disponível
                result = self.whatsapp_manager.get_task_result(self.current_task_id)
                
                # Atualizar UI na thread principal
                self.root.after(0, lambda r=is_running, res=result: self._update_task_ui(r, res))
                
                # Se não estiver mais rodando e temos um resultado, podemos parar o monitoramento
                if not is_running and result:
                    self.monitoring_task = False
                    break
                
                # Aguardar um pouco antes da próxima verificação
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Erro no monitoramento de tarefa: {str(e)}")
            traceback.print_exc()
            
            # Atualizar UI na thread principal para mostrar o erro
            self.root.after(0, lambda: self._handle_task_error(str(e)))
    
    def _update_task_ui(self, is_running, result):
        """Atualiza a UI com base no status da tarefa"""
        try:
            # Atualizar botões
            if is_running:
                self.send_all_button.configure(state=tk.DISABLED)
                self.cancel_button.configure(state=tk.NORMAL)
                self.task_status_label.configure(text="Tarefa em execução...")
            else:
                self.send_all_button.configure(state=tk.NORMAL)
                self.cancel_button.configure(state=tk.DISABLED)
                
                if result:
                    # Processar resultado final
                    self._process_task_result(result)
                    
        except Exception as e:
            print(f"Erro ao atualizar UI: {str(e)}")
    
    def _process_task_result(self, result):
        """Processa o resultado final de uma tarefa"""
        try:
            if result.get("success", False):
                # Atualizar progresso final
                total = result.get("total", 0)
                sent = result.get("sent", 0)
                cancelled = result.get("cancelled", False)
                
                self.progress_bar["value"] = 100
                
                if cancelled:
                    status_text = f"Envio cancelado: {sent}/{total} enviadas antes do cancelamento"
                    self.task_status_label.configure(text="Envio cancelado pelo usuário")
                else:
                    status_text = f"Concluído: {sent}/{total} enviadas com sucesso"
                    self.task_status_label.configure(text="Envio concluído com sucesso")
                
                self.progress_label.configure(text=status_text)
                
                # Log
                self.info_text.configure(state='normal')
                self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] {status_text}\n")
                self.info_text.see(tk.END)
                self.info_text.configure(state='disabled')
                
                if not cancelled:
                    messagebox.showinfo("Envio Concluído", status_text)
            else:
                error_msg = result.get("message", "Erro desconhecido")
                self.task_status_label.configure(text=f"Erro: {error_msg}")
                self.progress_label.configure(text="")
                
                # Log do erro
                self.info_text.configure(state='normal')
                self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Erro no envio: {error_msg}\n")
                self.info_text.see(tk.END)
                self.info_text.configure(state='disabled')
                
                messagebox.showerror("Erro", f"Erro no envio: {error_msg}")
        except Exception as e:
            print(f"Erro ao processar resultado: {str(e)}")
    
    def _handle_task_error(self, error_message):
        """Manipula erros no monitoramento de tarefas"""
        try:
            # Restaurar UI
            self.send_all_button.configure(state=tk.NORMAL)
            self.cancel_button.configure(state=tk.DISABLED)
            self.task_status_label.configure(text=f"Erro: {error_message}")
            
            # Log
            self.info_text.configure(state='normal')
            self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Erro no sistema: {error_message}\n")
            self.info_text.see(tk.END)
            self.info_text.configure(state='disabled')
        except Exception as e:
            print(f"Erro ao manipular erro de tarefa: {str(e)}")
    
    def _send_to_all(self):
        """Envia a mensagem para todos os clientes"""
        if not self.whatsapp_manager:
            messagebox.showinfo("Aviso", "Inicie o bot do WhatsApp primeiro.")
            return
            
        template = self.template_text.get(1.0, tk.END)
        
        if not template:
            messagebox.showinfo("Aviso", "Defina um template de mensagem.")
            return
            
        # Confirmar com o usuário
        # Calcular delay
        minutes = self.bulk_delay_minutes.get()
        seconds = self.bulk_delay_seconds.get()
        delay_text = f"{minutes} min {seconds} seg"
        
        confirm = messagebox.askyesno(
            "Confirmação", 
            f"Tem certeza que deseja enviar esta mensagem para TODOS os clientes?\n\n"
            f"Delay entre mensagens: {delay_text}\n\n"
            f"Esta ação não pode ser desfeita, mas pode ser interrompida."
        )
        
        if not confirm:
            return
            
        try:
            # Verificar status do WhatsApp
            status = self.whatsapp_manager.check_whatsapp_status()
            if not status.get("ready"):
                messagebox.showinfo("Aviso", "WhatsApp não está pronto. Verifique a conexão.")
                return
            
            # Resetar UI para modo de envio
            self.progress_bar["value"] = 0
            self.progress_label.configure(text="Preparando envio...")
            self.task_status_label.configure(text="Iniciando tarefa...")
            
            # Enviar em background
            def update_progress(current, total):
                # Atualizar na thread da interface
                if total > 0:
                    percentage = int(100 * current / total)
                    self.root.after(0, lambda: self._update_progress_display(current, total, percentage))
            
            result = self.whatsapp_manager.send_bulk_messages(
                message_template=template,
                progress_callback=update_progress,
                avoid_duplicates=True  # Evitar duplicatas
            )
            
            if result.get("success", False):
                # Obter ID da tarefa e iniciar monitoramento
                task_id = result.get("task_id")
                if task_id:
                    self._start_task_monitor(task_id)
                    
                    # Adicionar ao log
                    self.info_text.configure(state='normal')
                    self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Iniciado envio em massa (ID: {task_id})\n")
                    self.info_text.see(tk.END)
                    self.info_text.configure(state='disabled')
                else:
                    messagebox.showerror("Erro", "Não foi possível obter ID da tarefa")
            else:
                messagebox.showerror("Erro", result.get("message", "Erro ao iniciar envio"))
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao iniciar envio em massa:\n{str(e)}")
    
    def _update_progress_display(self, current, total, percentage):
        """Atualiza a exibição do progresso na UI"""
        try:
            self.progress_bar["value"] = percentage
            self.progress_label.configure(text=f"Enviando mensagem {current} de {total} ({percentage}%)")
        except Exception as e:
            print(f"Erro ao atualizar progresso: {str(e)}")
    
    def _cancel_bulk_send(self):
        """Cancela o envio em massa em andamento"""
        if not self.whatsapp_manager:
            return
            
        if messagebox.askyesno("Confirmação", "Deseja realmente cancelar o envio em massa?\n\nO sistema irá interromper após a mensagem atual."):
            try:
                # Solicitar cancelamento
                result = self.whatsapp_manager.cancel_current_task()
                
                if result.get("success", False):
                    # Atualizar UI
                    self.task_status_label.configure(text="Cancelando envio... (aguarde término da mensagem atual)")
                    
                    # Adicionar ao log
                    self.info_text.configure(state='normal')
                    self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Solicitação de cancelamento enviada\n")
                    self.info_text.see(tk.END)
                    self.info_text.configure(state='disabled')
                else:
                    messagebox.showinfo("Aviso", result.get("message", "Erro ao cancelar tarefa"))
            except Exception as e:
                traceback.print_exc()
                messagebox.showerror("Erro", f"Erro ao cancelar envio:\n{str(e)}")
    
    def _load_history_list(self):
        """Carrega a lista de SAs com histórico"""
        if not self.whatsapp_manager:
            messagebox.showinfo("Aviso", "Inicie o bot do WhatsApp primeiro.")
            return
            
        try:
            # Limpar lista atual
            self.history_list.delete(0, tk.END)
            
            # Obter lista de clientes com mensagens
            clients_with_messages = self.whatsapp_manager.storage.get_all_clients_with_messages()
            
            if not clients_with_messages:
                messagebox.showinfo("Aviso", "Nenhum histórico de mensagens encontrado.")
                return
                
            # Obter informações adicionais dos clientes
            for sa in clients_with_messages:
                client_info = self.whatsapp_manager.storage.get_client_info(sa)
                name = client_info.get('Nome', 'Desconhecido') if client_info else 'Desconhecido'
                
                # Adicionar à lista
                self.history_list.insert(tk.END, f"{sa} - {name}")
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao carregar lista de histórico:\n{str(e)}")
    
    def _on_history_sa_select(self, event):
        """Manipula a seleção de uma SA na lista de histórico"""
        if not self.whatsapp_manager:
            return
            
        selection = self.history_list.curselection()
        if not selection:
            return
            
        # Obter SA selecionada (formato "SA - Nome")
        item_text = self.history_list.get(selection[0])
        sa = item_text.split(" - ")[0]
        
        self._show_message_history(sa)
    
    def _show_message_history(self, sa):
        """Mostra o histórico de mensagens para uma SA específica"""
        try:
            # Obter histórico de mensagens
            messages = self.whatsapp_manager.storage.get_client_messages(sa)
            client_info = self.whatsapp_manager.storage.get_client_info(sa)
            
            # Limpar área de texto
            self.history_text.delete(1.0, tk.END)
            
            # Mostrar informações do cliente
            if client_info:
                nome = client_info.get('Nome', 'N/A')
                telefone = client_info.get('Telefone', 'N/A')
                endereco = client_info.get('Endereço', 'N/A')
                
                # Atualizar label com informações do cliente
                self.history_client_info.config(
                    text=f"Cliente: {nome} | SA: {sa} | Telefone: {telefone}"
                )
                
                # Adicionar ao texto
                self.history_text.insert(tk.END, f"Cliente: {nome}\n")
                self.history_text.insert(tk.END, f"SA: {sa}\n")
                self.history_text.insert(tk.END, f"Telefone: {telefone}\n")
                self.history_text.insert(tk.END, f"Endereço: {endereco}\n\n")
            else:
                # Atualizar label
                self.history_client_info.config(text=f"SA: {sa}")
                self.history_text.insert(tk.END, f"Cliente SA: {sa}\n\n")
                
            # Mostrar mensagens
            if messages:
                self.history_text.insert(tk.END, f"Total de mensagens: {len(messages)}\n\n")
                
                # Ordenar mensagens por timestamp
                for msg in sorted(messages, key=lambda m: m.get('timestamp', '')):
                    timestamp = msg.get('timestamp', '')
                    if timestamp:
                        try:
                            # Tentar formatar o timestamp
                            dt = datetime.fromisoformat(timestamp)
                            timestamp = dt.strftime('%d/%m/%Y %H:%M:%S')
                        except:
                            pass
                            
                    msg_type = 'Enviada' if msg.get('type') == 'sent' else 'Recebida'
                    
                    # Adicionar tags para colorir o texto
                    tag = "sent" if msg.get('type') == 'sent' else "received"
                    
                    position = self.history_text.index(tk.END)
                    self.history_text.insert(tk.END, f"[{timestamp}] {msg_type}:\n")
                    self.history_text.insert(tk.END, f"{msg.get('message', '')}\n\n")
                    
                    # Configurar cores diferentes para mensagens enviadas e recebidas
                    if tag == "sent":
                        self.history_text.tag_add("sent", position, f"{position} lineend +1 lines")
                        self.history_text.tag_config("sent", foreground="blue")
                    else:
                        self.history_text.tag_add("received", position, f"{position} lineend +1 lines")
                        self.history_text.tag_config("received", foreground="green")
            else:
                self.history_text.insert(tk.END, "Nenhuma mensagem encontrada para este cliente.")
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao carregar histórico de mensagens:\n{str(e)}")
    
    def _export_history(self):
        """Exporta o histórico de mensagens atual para arquivo"""
        if not self.history_text.get(1.0, tk.END).strip():
            messagebox.showinfo("Aviso", "Nenhum histórico para exportar.")
            return
            
        try:
            # Abrir diálogo para salvar arquivo
            file_path = filedialog.asksaveasfilename(
                title="Salvar Histórico",
                defaultextension=".txt",
                filetypes=[("Arquivo de Texto", "*.txt"), ("Todos os Arquivos", "*.*")]
            )
            
            if not file_path:
                return
                
            # Salvar conteúdo do histórico
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.history_text.get(1.0, tk.END))
                
            messagebox.showinfo("Sucesso", f"Histórico exportado para {file_path}")
                
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao exportar histórico:\n{str(e)}")

    def _update_auto_reply(self):
        """Atualiza configurações de resposta automática no gerenciador"""
        if not self.whatsapp_manager:
            messagebox.showinfo("Aviso", "Inicie o bot do WhatsApp primeiro.")
            return
        
        enabled = self.auto_reply_enabled.get()
        message = self.auto_reply_message.get()
        
        if not message and enabled:
            messagebox.showinfo("Aviso", "Por favor, defina uma mensagem de resposta.")
            return
        
        try:
            self.whatsapp_manager.set_auto_reply(enabled, message)
            
            status = "habilitada" if enabled else "desabilitada"
            self.info_text.configure(state='normal')
            self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Resposta automática {status}.\n")
            if enabled:
                self.info_text.insert(tk.END, f"Mensagem: {message}\n")
            self.info_text.see(tk.END)
            self.info_text.configure(state='disabled')
            
            messagebox.showinfo("Sucesso", f"Resposta automática {status} com sucesso.")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao configurar resposta automática:\n{str(e)}")
    
    def _process_historical_now(self):
        """Força a verificação de mensagens históricas"""
        if not self.whatsapp_manager:
            messagebox.showinfo("Aviso", "Inicie o bot do WhatsApp primeiro.")
            return
        
        try:
            self.status_text.set("Verificando mensagens históricas...")
            self.root.update_idletasks()
            
            # Executar em thread separada para não travar a interface
            def process_task():
                try:
                    self.whatsapp_manager._process_historical_messages()
                    self.root.after(0, lambda: self.status_text.set("Verificação de mensagens concluída."))
                except Exception as e:
                    self.root.after(0, lambda: self.status_text.set(f"Erro: {str(e)}"))
            
            threading.Thread(target=process_task, daemon=True).start()
            
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao iniciar verificação de mensagens:\n{str(e)}")

    def _update_bulk_delay(self):
        """Atualiza o delay entre mensagens em massa"""
        if not self.whatsapp_manager:
            messagebox.showinfo("Aviso", "Inicie o bot do WhatsApp primeiro.")
            return
        
        try:
            # Calcular delay total em segundos
            minutes = self.bulk_delay_minutes.get()
            seconds = self.bulk_delay_seconds.get()
            total_seconds = minutes * 60 + seconds
            
            # Aplicar delay (mínimo de 1 segundo)
            total_seconds = max(1, total_seconds)
            self.whatsapp_manager.set_bulk_message_delay(total_seconds)
            
            # Atualizar log
            self.info_text.configure(state='normal')
            self.info_text.insert(tk.END, f"\n[{datetime.now().strftime('%H:%M:%S')}] Delay entre mensagens configurado: {minutes} min {seconds} seg\n")
            self.info_text.see(tk.END)
            self.info_text.configure(state='disabled')
            
            messagebox.showinfo("Sucesso", f"Delay configurado: {minutes} min {seconds} seg")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Erro ao configurar delay:\n{str(e)}")

def main():
    # Criar janela principal
    root = tk.Tk()
    app = WhatsAppGUI(root)
    
    # Iniciar loop de eventos
    root.mainloop()

if __name__ == "__main__":
    main() 