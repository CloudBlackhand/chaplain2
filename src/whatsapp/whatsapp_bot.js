const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');
const axios = require('axios');

// Carregar variáveis de ambiente
dotenv.config({ path: path.join(__dirname, '../../.env') });

const app = express();
const PORT = process.env.PORT || 3000;
const WEBHOOK_URL = process.env.WEBHOOK_URL || '';
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_INTERVAL = 5000; // 5 segundos
const WEBHOOK_RETRY_ATTEMPTS = 3;  // Número de tentativas para webhooks
const WEBHOOK_RETRY_DELAY = 2000;  // Delay entre tentativas em ms

// Contadores para estatísticas e monitoramento de saúde
let stats = {
    messagesReceived: 0,
    messagesSent: 0,
    reconnectAttempts: 0,
    lastReconnect: null,
    webhookSuccess: 0,
    webhookFailed: 0,
    errors: []
};

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Para garantir que o servidor aceite webhooks de qualquer origem
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
    next();
});

// Diretório para armazenar sessão
const SESSION_PATH = process.env.SESSION_PATH || './whatsapp_session';
const HEADLESS = process.env.HEADLESS !== 'false';

// Inicializar cliente do WhatsApp
let client;
let clientStatus = {
    isReady: false,
    qrCode: null,
    lastError: null,
    reconnecting: false
};

function initializeWhatsAppClient() {
    console.log("Iniciando cliente do WhatsApp...");
    
    client = new Client({
        authStrategy: new LocalAuth({
            dataPath: SESSION_PATH
        }),
        puppeteer: {
            headless: HEADLESS,
            args: [
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        },
        restartOnAuthFail: true
    });

    // Evento de geração do QR Code
    client.on('qr', (qr) => {
        console.log('QR Code recebido, escaneie para autenticar');
        qrcode.generate(qr, { small: true });
        clientStatus.qrCode = qr;
        clientStatus.lastError = null;
    });

    // Evento de autenticação
    client.on('authenticated', () => {
        console.log('Autenticado com sucesso!');
        clientStatus.qrCode = null;
        clientStatus.lastError = null;
        stats.reconnectAttempts = 0;
    });

    // Evento de pronto
    client.on('ready', () => {
        console.log('Cliente WhatsApp pronto!');
        clientStatus.isReady = true;
        clientStatus.lastError = null;
        stats.reconnectAttempts = 0;
        
        // Salvar log de inicialização
        logEvent('ready', 'Cliente WhatsApp inicializado com sucesso');
    });

    // Evento de desconexão
    client.on('disconnected', (reason) => {
        console.log('Cliente desconectado:', reason);
        clientStatus.isReady = false;
        clientStatus.lastError = reason;
        
        logEvent('disconnected', `Cliente desconectado: ${reason}`);
        
        // Reconectar se não estiver reconectando no momento
        if (!clientStatus.reconnecting && stats.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            handleReconnection();
        } else if (stats.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            console.log('Número máximo de tentativas de reconexão excedido. Favor reiniciar manualmente.');
            logEvent('error', 'Número máximo de tentativas de reconexão excedido');
        }
    });

    // Evento de mensagem recebida
    client.on('message', async (message) => {
        try {
            const contact = await message.getContact();
            const chat = await message.getChat();
            stats.messagesReceived++;
            
            const messageData = {
                id: message.id.id,
                from: message.from,
                body: message.body,
                timestamp: message.timestamp,
                contactName: contact.name || contact.pushname || '',
                contactNumber: contact.number,
                isGroup: chat.isGroup,
                hasMedia: message.hasMedia
            };
            
            // Salvar em arquivo para integração com Python
            saveReceivedMessage(messageData);
            
            // Enviar para webhook, se configurado
            if (WEBHOOK_URL) {
                sendWebhookWithRetry(WEBHOOK_URL, messageData);
            }
            
            console.log(`Mensagem recebida de ${messageData.contactName} (${messageData.contactNumber}): ${messageData.body}`);
            logEvent('message_received', `De: ${messageData.contactNumber}, Msg: ${messageData.body.substring(0, 50)}...`);
            
        } catch (error) {
            console.error('Erro ao processar mensagem recebida:', error);
            logEvent('error', `Erro ao processar mensagem recebida: ${error.message}`);
        }
    });

    // Adicionar manipuladores para outros eventos importantes
    client.on('change_state', state => {
        console.log('Estado do cliente alterado:', state);
        logEvent('state_change', `Estado alterado para: ${state}`);
    });
    
    client.on('loading_screen', (percent, message) => {
        console.log(`Carregando: ${percent}% - ${message}`);
    });

    client.on('auth_failure', (message) => {
        console.error('Falha de autenticação:', message);
        clientStatus.lastError = `Falha de autenticação: ${message}`;
        logEvent('auth_failure', message);
    });

    // Inicializar cliente
    client.initialize().catch(err => {
        console.error('Erro ao inicializar cliente:', err);
        clientStatus.lastError = `Erro de inicialização: ${err.message}`;
        logEvent('error', `Erro ao inicializar cliente: ${err.message}`);
        
        // Tentar reconectar após erro de inicialização
        if (stats.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            handleReconnection();
        }
    });
}

// Função para reconexão
function handleReconnection() {
    if (clientStatus.reconnecting) return;
    
    clientStatus.reconnecting = true;
    stats.reconnectAttempts++;
    stats.lastReconnect = new Date().toISOString();
    
    console.log(`Tentando reconectar... Tentativa ${stats.reconnectAttempts} de ${MAX_RECONNECT_ATTEMPTS}`);
    logEvent('reconnect_attempt', `Tentativa ${stats.reconnectAttempts} de ${MAX_RECONNECT_ATTEMPTS}`);
    
    setTimeout(() => {
        try {
            client.destroy();
            client = null;
            
            setTimeout(() => {
                clientStatus.reconnecting = false;
                initializeWhatsAppClient();
            }, 1000);
            
        } catch (error) {
            console.error('Erro durante reconexão:', error);
            logEvent('error', `Erro durante reconexão: ${error.message}`);
            clientStatus.reconnecting = false;
            
            // Tentar novamente
            if (stats.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                setTimeout(handleReconnection, RECONNECT_INTERVAL);
            }
        }
    }, RECONNECT_INTERVAL);
}

// Funções para salvar mensagens e logs
function saveReceivedMessage(messageData) {
    const messagesDir = path.join(__dirname, '../../messages');
    if (!fs.existsSync(messagesDir)) {
        fs.mkdirSync(messagesDir, { recursive: true });
    }
    
    const fileName = path.join(messagesDir, `received_${Date.now()}.json`);
    fs.writeFileSync(fileName, JSON.stringify(messageData, null, 2));
}

function logEvent(type, message) {
    try {
        const logsDir = path.join(__dirname, '../../logs');
        if (!fs.existsSync(logsDir)) {
            fs.mkdirSync(logsDir, { recursive: true });
        }
        
        const now = new Date();
        const logEntry = {
            timestamp: now.toISOString(),
            type,
            message
        };
        
        // Salvar em arquivo de log
        const logFile = path.join(logsDir, `whatsapp_${now.toISOString().split('T')[0]}.log`);
        fs.appendFileSync(logFile, JSON.stringify(logEntry) + '\n');
        
        // Guardar os últimos 10 erros para monitoramento
        if (type === 'error') {
            stats.errors.push(logEntry);
            if (stats.errors.length > 10) {
                stats.errors.shift();
            }
        }
    } catch (error) {
        console.error('Erro ao salvar log:', error);
    }
}

// Função para enviar webhook com retentativas
async function sendWebhookWithRetry(url, data, attempt = 1) {
    try {
        console.log(`Tentativa ${attempt} de envio para webhook: ${url}`);
        
        const response = await axios.post(url, data, {
            headers: {
                'Content-Type': 'application/json'
            },
            timeout: 10000 // 10 segundos de timeout
        });
        
        if (response.status >= 200 && response.status < 300) {
            console.log(`Webhook enviado com sucesso para: ${url} (Status: ${response.status})`);
            stats.webhookSuccess++;
            return true;
        } else {
            throw new Error(`Resposta com status inesperado: ${response.status}`);
        }
    } catch (error) {
        console.error(`Erro ao enviar webhook (tentativa ${attempt}):`, error.message);
        
        if (attempt < WEBHOOK_RETRY_ATTEMPTS) {
            // Esperar antes da próxima tentativa (com backoff exponencial)
            const delay = WEBHOOK_RETRY_DELAY * attempt;
            console.log(`Aguardando ${delay}ms antes da próxima tentativa...`);
            await new Promise(resolve => setTimeout(resolve, delay));
            
            // Tentar novamente
            return sendWebhookWithRetry(url, data, attempt + 1);
        } else {
            // Todas as tentativas falharam
            console.error(`Falha ao enviar webhook após ${WEBHOOK_RETRY_ATTEMPTS} tentativas`);
            logEvent('error', `Falha no webhook: ${error.message} após ${WEBHOOK_RETRY_ATTEMPTS} tentativas`);
            stats.webhookFailed++;
            return false;
        }
    }
}

// Inicializar cliente do WhatsApp
initializeWhatsAppClient();

// Rotas da API
// Verificação de saúde do sistema
app.get('/api/health', (req, res) => {
    const health = {
        status: clientStatus.isReady ? 'up' : 'down',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        port: PORT,
        stats: {
            messagesReceived: stats.messagesReceived,
            messagesSent: stats.messagesSent,
            reconnectAttempts: stats.reconnectAttempts,
            lastReconnect: stats.lastReconnect,
            webhook: {
                url: WEBHOOK_URL || 'não configurado',
                success: stats.webhookSuccess,
                failed: stats.webhookFailed,
                successRate: stats.webhookSuccess + stats.webhookFailed > 0 
                    ? ((stats.webhookSuccess / (stats.webhookSuccess + stats.webhookFailed)) * 100).toFixed(2) + '%' 
                    : 'N/A'
            }
        },
        lastErrors: stats.errors.slice(-3)  // Retorna apenas os 3 últimos erros
    };
    
    res.json(health);
});

// Obter status do cliente
app.get('/api/status', (req, res) => {
    res.json({
        ready: clientStatus.isReady,
        qrCode: clientStatus.qrCode,
        error: clientStatus.lastError,
        reconnecting: clientStatus.reconnecting,
        stats: {
            messagesReceived: stats.messagesReceived,
            messagesSent: stats.messagesSent
        }
    });
});

// Força reconexão
app.post('/api/reconnect', (req, res) => {
    if (clientStatus.reconnecting) {
        return res.status(400).json({ success: false, message: 'Já está tentando reconectar' });
    }
    
    try {
        stats.reconnectAttempts = 0;
        handleReconnection();
        return res.json({ success: true, message: 'Iniciando reconexão' });
    } catch (error) {
        return res.status(500).json({ success: false, message: 'Erro ao iniciar reconexão', error: error.message });
    }
});

// Enviar mensagem
app.post('/api/send-message', async (req, res) => {
    if (!clientStatus.isReady) {
        return res.status(400).json({ success: false, message: 'Cliente não está pronto' });
    }
    
    try {
        const { phone, message } = req.body;
        
        if (!phone || !message) {
            return res.status(400).json({ success: false, message: 'Número de telefone e mensagem são obrigatórios' });
        }
        
        // Formatar número de telefone
        let formattedNumber = phone.replace(/\D/g, '');
        if (!formattedNumber.endsWith('@c.us')) {
            formattedNumber = `${formattedNumber}@c.us`;
        }
        
        // Validar que o número existe no WhatsApp
        const isRegistered = await client.isRegisteredUser(formattedNumber);
        if (!isRegistered) {
            return res.status(400).json({ 
                success: false, 
                message: 'Número de telefone não está registrado no WhatsApp' 
            });
        }
        
        // Enviar mensagem
        await client.sendMessage(formattedNumber, message);
        stats.messagesSent++;
        
        logEvent('message_sent', `Para: ${phone}, Msg: ${message.substring(0, 50)}...`);
        return res.json({ success: true, message: 'Mensagem enviada com sucesso' });
    } catch (error) {
        console.error('Erro ao enviar mensagem:', error);
        logEvent('error', `Erro ao enviar mensagem: ${error.message}`);
        return res.status(500).json({ success: false, message: 'Erro ao enviar mensagem', error: error.message });
    }
});

// Enviar mensagens em massa
app.post('/api/send-bulk', async (req, res) => {
    if (!clientStatus.isReady) {
        return res.status(400).json({ success: false, message: 'Cliente não está pronto' });
    }
    
    try {
        const { messages } = req.body;
        
        if (!messages || !Array.isArray(messages) || messages.length === 0) {
            return res.status(400).json({ success: false, message: 'Lista de mensagens inválida' });
        }
        
        const results = [];
        
        for (const msg of messages) {
            try {
                const { phone, message, sa } = msg;
                
                if (!phone || !message) {
                    results.push({ 
                        success: false, 
                        message: 'Número de telefone e mensagem são obrigatórios',
                        sa: sa || 'desconhecido'
                    });
                    continue;
                }
                
                // Formatar número de telefone
                let formattedNumber = phone.replace(/\D/g, '');
                if (!formattedNumber.endsWith('@c.us')) {
                    formattedNumber = `${formattedNumber}@c.us`;
                }
                
                // Validar que o número existe no WhatsApp
                const isRegistered = await client.isRegisteredUser(formattedNumber);
                if (!isRegistered) {
                    results.push({ 
                        success: false, 
                        message: 'Número não registrado no WhatsApp',
                        phone,
                        sa: sa || 'desconhecido'
                    });
                    continue;
                }
                
                // Enviar mensagem
                await client.sendMessage(formattedNumber, message);
                stats.messagesSent++;
                
                results.push({ 
                    success: true, 
                    message: 'Mensagem enviada com sucesso',
                    phone,
                    sa: sa || 'desconhecido'
                });
                
                logEvent('bulk_message_sent', `Para: ${phone}, SA: ${sa || 'desconhecido'}`);
                
                // Aguardar pequeno intervalo para evitar bloqueio
                await new Promise(resolve => setTimeout(resolve, 500));
                
            } catch (error) {
                console.error(`Erro ao enviar para ${msg.phone}:`, error);
                logEvent('error', `Erro ao enviar mensagem em massa para ${msg.phone}: ${error.message}`);
                
                results.push({ 
                    success: false, 
                    message: `Erro: ${error.message}`,
                    phone: msg.phone,
                    sa: msg.sa || 'desconhecido'
                });
            }
        }
        
        return res.json({ 
            success: true, 
            results,
            stats: {
                total: messages.length,
                success: results.filter(r => r.success).length,
                failed: results.filter(r => !r.success).length
            }
        });
    } catch (error) {
        console.error('Erro ao enviar mensagens em massa:', error);
        logEvent('error', `Erro no processamento de mensagens em massa: ${error.message}`);
        return res.status(500).json({ 
            success: false, 
            message: 'Erro ao enviar mensagens em massa', 
            error: error.message 
        });
    }
});

// Definir webhook externo
app.post('/api/set-webhook', (req, res) => {
    const { url } = req.body;
    
    if (!url) {
        return res.status(400).json({ success: false, message: 'URL do webhook é obrigatória' });
    }
    
    try {
        // Salvar em variável de ambiente temporária
        process.env.WEBHOOK_URL = url;
        
        // Tentar fazer uma chamada de teste para o webhook
        const testData = { 
            type: 'test',
            timestamp: new Date().toISOString(),
            message: 'Teste de conexão com webhook'
        };
        
        // Usar nossa nova função de retentativa
        sendWebhookWithRetry(url, testData)
            .then((success) => {
                if (success) {
                    // Redefinir estatísticas de webhook ao mudar a URL
                    stats.webhookSuccess = 0;
                    stats.webhookFailed = 0;
                    
                    logEvent('webhook_set', `Webhook configurado para: ${url}`);
                    return res.json({ 
                        success: true, 
                        message: 'Webhook configurado e testado com sucesso',
                        port: PORT
                    });
                } else {
                    logEvent('warning', `Webhook configurado mas teste falhou: ${url}`);
                    return res.json({ 
                        success: true, 
                        message: 'Webhook configurado, mas teste falhou após várias tentativas. Verifique se o endpoint está acessível.',
                        warning: 'Falha no teste de conexão',
                        port: PORT
                    });
                }
            })
            .catch(error => {
                logEvent('error', `Erro ao testar webhook ${url}: ${error.message}`);
                return res.json({ 
                    success: true, 
                    message: 'Webhook configurado, mas teste falhou. Verifique se o endpoint está acessível.',
                    warning: error.message,
                    port: PORT
                });
            });
    } catch (error) {
        console.error('Erro ao configurar webhook:', error);
        logEvent('error', `Erro ao configurar webhook: ${error.message}`);
        return res.status(500).json({ 
            success: false, 
            message: 'Erro ao configurar webhook', 
            error: error.message,
            port: PORT
        });
    }
});

// Middleware de tratamento de erros
app.use((err, req, res, next) => {
    console.error('Erro na API:', err);
    logEvent('api_error', `${req.method} ${req.path}: ${err.message}`);
    
    res.status(500).json({
        success: false,
        message: 'Erro interno do servidor',
        error: err.message
    });
});

// Iniciar servidor Express
app.listen(PORT, () => {
    console.log(`Servidor rodando na porta ${PORT}`);
});

// Tratar erros não capturados
process.on('uncaughtException', (error) => {
    console.error('Erro não tratado:', error);
    logEvent('uncaught_exception', error.message);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Promessa rejeitada não tratada:', reason);
    logEvent('unhandled_rejection', String(reason));
}); 