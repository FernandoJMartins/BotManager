# 🤖 Telegram Bot Manager

Sistema completo para hospedar e gerenciar bots do Telegram 24/7 com sistema de pagamento PIX integrado.

## 📋 Descrição

Este é um sistema completo que permite aos usuários criar, configurar e hospedar até 30 bots do Telegram simultaneamente. Cada bot roda 24/7 com sistema de monitoramento automático e restart em caso de falha.

### ✨ Características Principais

- 🔐 **Sistema de Autenticação**: Registro e login seguro de usuários
- 🤖 **Gerenciamento de Bots**: Até 30 bots por usuário com validação de token
- 💰 **Pagamento PIX**: Taxa fixa de R$ 0,70 por bot com QR Code automático
- 📱 **Interface Web**: Dashboard moderno e responsivo
- 🔄 **Sistema 24/7**: Monitoramento contínuo com reinicialização automática
- 🎛️ **Configuração Personalizada**: Welcome message, imagem, áudio e valores PIX
- 🚀 **API REST**: Endpoints completos para integração
- 🛡️ **Isolamento**: Cada usuário só acessa seus próprios bots

## 🏗️ Arquitetura

```
telegram-bot-manager/
├── src/
│   ├── api/
│   │   └── routes/          # Rotas da API (auth, bots)
│   ├── bot_runners/         # Executores dos bots individuais
│   ├── database/           # Configuração do banco de dados
│   ├── models/             # Modelos SQLAlchemy (User, Bot, Payment)
│   ├── services/           # Serviços (PIX, Telegram, Bot Manager)
│   ├── templates/          # Templates HTML (Dashboard, Forms)
│   └── utils/              # Utilitários e configurações
├── uploads/                # Arquivos de imagem e áudio dos bots
├── requirements.txt        # Dependências Python
└── docker-compose.yml      # Configuração Docker
```

## 🚀 Instalação e Execução

### Pré-requisitos

- Python 3.8+
- SQLite ou PostgreSQL
- Tokens de bots do Telegram

### 1. Clone o repositório

```bash
git clone <repository-url>
cd telegram-bot-manager
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

```bash
# Crie um arquivo .env na raiz do projeto
SECRET_KEY=sua-chave-secreta-super-segura
DATABASE_URL=sqlite:///telegram_bot_manager.db
PIX_KEY=sua@chave.pix
```

### 4. Execute a aplicação

```bash
python src/app.py
```

### 5. Acesse o dashboard

Abra seu navegador em: `http://localhost:5000`

## 🐳 Execução com Docker

```bash
# Build da imagem
docker build -t telegram-bot-manager .

# Executar com docker-compose
docker-compose up -d
```

## 📊 Como Usar

### 1. Criar Conta

- Acesse `/auth/register`
- Preencha username, email e senha
- Faça login

### 2. Criar Primeiro Bot

- No dashboard, clique em "Criar Novo Bot"
- Cole o token do seu bot do Telegram
- Sistema valida o token automaticamente
- Configure mensagem de boas-vindas, imagem, áudio
- Defina valores para PIX (opcional)

### 3. Realizar Pagamento

- Sistema gera PIX de R$ 0,70
- Escaneie o QR Code ou copie o código PIX
- Após confirmação, bot é ativado automaticamente

### 4. Bot Ativo 24/7

- Bot começa a rodar imediatamente
- Sistema monitora e reinicia automaticamente
- Comandos disponíveis:
  - `/start` - Mensagem de boas-vindas + mídia
  - `/pix` - Gera PIX com valores configurados

## 🔧 Funcionalidades Técnicas

### Sistema de Monitoramento

- **Verificação contínua**: Cada 30 segundos
- **Auto-restart**: Em caso de falha ou crash
- **Health check**: Atualização de status em tempo real
- **Logging detalhado**: Para debugging e auditoria

### Validação de Tokens

- **API do Telegram**: Verificação em tempo real
- **Prevenção de duplicatas**: Um token por bot apenas
- **Verificação de permissões**: Bot ativo e funcional

### Sistema PIX

- **QR Code automático**: Geração instantânea
- **Taxa fixa**: R$ 0,70 por bot
- **Webhook support**: Para confirmação automática
- **Expiração**: 24h para pagamento

### Segurança

- **Isolamento de usuários**: Cada usuário só vê seus bots
- **Hash de senhas**: bcrypt para segurança
- **Sessões seguras**: Flask-Login
- **Validação de entrada**: Sanitização de dados

## 🎯 Endpoints da API

### Autenticação

```bash
POST /auth/register     # Criar conta
POST /auth/login        # Login
GET  /auth/logout       # Logout
GET  /auth/profile      # Ver perfil
```

### Gestão de Bots

```bash
GET    /bots/                          # Listar bots do usuário
POST   /bots/validate-token           # Validar token
POST   /bots/create                   # Criar novo bot
GET    /bots/<id>/payment-status      # Status do pagamento
POST   /bots/<id>/configure           # Configurar bot
GET    /bots/<id>                     # Ver detalhes
POST   /bots/<id>/delete              # Deletar bot
```

### Dashboard

```bash
GET /                    # Página inicial (redireciona)
GET /dashboard          # Dashboard principal
```

## 💡 Exemplos de Uso

### 1. Criar bot via API

```bash
curl -X POST http://localhost:5000/bots/validate-token \
  -H "Content-Type: application/json" \
  -d '{"token": "123456789:ABCdefGHIjklMN_opqRSTUVwxyZ"}'
```

### 2. Configurar mensagem de boas-vindas

```bash
curl -X POST http://localhost:5000/bots/create \
  -F "token=123456789:ABCdefGHIjklMN_opqRSTUVwxyZ" \
  -F "welcome_message=Olá! Bem-vindo ao meu bot!" \
  -F "pix_values=[5.00, 10.00, 20.00]" \
  -F "welcome_image=@image.jpg"
```

## 🔄 Workflow Completo

1. **Usuário se registra** → Sistema cria conta
2. **Faz login** → Acessa dashboard
3. **Cria novo bot** → Insere token do Telegram
4. **Sistema valida token** → Verifica com API do Telegram
5. **Configura bot** → Welcome message, mídia, valores PIX
6. **Sistema gera PIX** → QR Code de R$ 0,70
7. **Usuário paga** → Confirma pagamento
8. **Bot é ativado** → Inicia execução 24/7
9. **Monitoramento contínuo** → Auto-restart se necessário

## 🚨 Troubleshooting

### Bot não inicia

1. Verifique se o pagamento foi confirmado
2. Verifique se o token ainda é válido
3. Consulte os logs: `tail -f app.log`

### Token inválido

1. Obtenha novo token do @BotFather
2. Certifique-se de que o bot não está sendo usado em outro lugar

### Problemas de pagamento

1. Verifique se a chave PIX está configurada
2. Confirme se o webhook de pagamento está ativo

## 🔒 Considerações de Segurança

- **Nunca expor tokens**: Armazenados de forma segura no banco
- **Rate limiting**: Implementar para prevenir abuso
- **HTTPS obrigatório**: Em produção
- **Backup regular**: Do banco de dados
- **Logs auditoria**: Para rastreamento

## 📈 Melhorias Futuras

- [ ] Painel administrativo
- [ ] Métricas e analytics
- [ ] API para webhooks de pagamento
- [ ] Suporte a outros métodos de pagamento
- [ ] Backup automático de configurações
- [ ] Notificações por email
- [ ] API rate limiting
- [ ] Temas customizáveis

## 📄 Licença

Este projeto está licenciado sob a licença MIT.

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📞 Suporte

Para suporte, abra uma issue no GitHub ou entre em contato.

---

**⚡ Sistema pronto para produção com alta disponibilidade e escalabilidade!**
