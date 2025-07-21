# Chaplain - Sistema de Mensagens WhatsApp

Sistema automatizado para gerenciamento de mensagens WhatsApp com integração Excel e detecção automática de porta.

## Características

- Detecção automática de porta do WhatsApp
- Integração com planilhas Excel para gerenciamento de contatos
- Envio de mensagens em massa com personalização
- Interface gráfica para gerenciamento
- Sistema de webhooks para integração com outros sistemas
- Armazenamento de histórico de mensagens
- Resposta automática para mensagens recebidas

## Instalação e Execução

Para instalar e iniciar o sistema, dê dois cliques no arquivo `Chaplain-Completo.desktop` ou execute:

```bash
./instalar_e_iniciar_chaplain.sh
```

Este script irá:
1. Instalar todas as dependências necessárias
2. Configurar o ambiente
3. Iniciar o sistema automaticamente

## Requisitos

- Python 3.8+
- Node.js 14+
- Navegador compatível com WhatsApp Web

## Estrutura do Projeto

- `src/` - Código fonte principal
  - `excel_reader/` - Módulo para leitura de planilhas
  - `interface/` - Interface gráfica
  - `storage/` - Sistema de armazenamento
  - `whatsapp/` - Bot WhatsApp
- `excel/` - Planilhas de dados
- `logs/` - Registros do sistema
- `messages/` - Mensagens temporárias
- `storage/` - Armazenamento de dados

## Desenvolvimento

Para desenvolvedores que desejam contribuir com o projeto, siga estas etapas:

1. Clone o repositório
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   cd src/whatsapp && npm install
   ```
3. Execute o sistema em modo de desenvolvimento:
   ```bash
   python src/main.py
   ``` 