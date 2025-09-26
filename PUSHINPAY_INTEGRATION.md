# 🤖 Telegram Bot Manager - Guia de Integração PushinPay

## Sistema Completo de Pagamentos PIX com PushinPay

### 📋 Funcionalidades Implementadas

#### ✅ 1. Autenticação e Usuários

- Sistema de login/registro completo
- Armazenamento seguro de tokens PushinPay por usuário
- Perfil de usuário com configuração de token

#### ✅ 2. Gestão de Bots

- Limite de 30 bots por usuário
- Validação de tokens do Telegram
- Sistema de ativação baseado em pagamento
- Interface para criar/editar/excluir bots

#### ✅ 3. Sistema de Pagamentos PushinPay

- **Taxa fixa:** R$ 0,70 por bot
- **Split automático:** 100% vai para conta configurada no sistema
- **Conta de split:** `9E4B259F-DB6D-419E-8D78-7216BF642856`
- **Geração automática de PIX** via API PushinPay
- **Webhook** para confirmação automática de pagamentos

#### ✅ 4. Bot Runner 24/7

- Execução contínua de bots
- Monitoramento e restart automático
- Botões inline para valores PIX (R$ 10, R$ 25, R$ 50, R$ 100)
- Callback handlers para processar cliques nos botões

---

## 🚀 Como Iniciar o Sistema

### 1. Via Docker (Recomendado)

```bash
# No diretório do projeto
docker-compose up -d
```

### 2. Localmente (Desenvolvimento)

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar aplicação
python -m src.app
```

**Acesso:** http://localhost:5000

---

## 🔧 Configuração PushinPay

### 1. Configurar Token do Usuário

1. Acesse **Perfil** no dashboard
2. Insira seu **Token Bearer** da PushinPay
3. Sistema valida automaticamente o token

### 2. Fluxo de Pagamento Completo

#### No Bot do Telegram:

```
Usuário → Clica botão PIX (R$ 10/25/50/100)
    ↓
Sistema → Gera PIX via PushinPay API
    ↓
Usuário → Recebe QR Code + Código PIX
    ↓
Usuário → Paga via qualquer banco/PIX
    ↓
PushinPay → Envia webhook confirmação
    ↓
Sistema → Ativa bot automaticamente
```

### 3. Endpoints da API PushinPay Utilizados

#### ✅ Criação de PIX:

```http
POST https://api.pushinpay.com.br/api/pix
Authorization: Bearer {user_token}
Content-Type: application/json

{
  "value": 0.70,
  "description": "Ativação de bot Telegram",
  "reference": "{bot_id}",
  "split": {
    "account": "9E4B259F-DB6D-419E-8D78-7216BF642856",
    "percentage": 100
  }
}
```

#### ✅ Validação de Token:

```http
GET https://api.pushinpay.com.br/api/user/me
Authorization: Bearer {user_token}
```

#### ✅ Webhook de Confirmação:

```http
POST http://seu-dominio.com/webhook/pushinpay
{
  "id": "transaction_id",
  "status": "approved|paid|cancelled|failed",
  "reference": "bot_id",
  "value": 0.70
}
```

---

## 💾 Estrutura do Banco de Dados

### Tabela Users

```sql
- id (PK)
- username (unique)
- email (unique)
- password_hash
- pushinpay_token  -- ✅ NOVO: Token bearer por usuário
- created_at
```

### Tabela TelegramBot

```sql
- id (PK)
- user_id (FK)
- name
- token
- is_active
- payment_status   -- ✅ NOVO: pending|paid|failed
- created_at
```

### Tabela Payment

```sql
- id (PK)
- user_id (FK)
- bot_id (FK)
- amount (0.70)
- external_payment_id  -- ✅ NOVO: ID da PushinPay
- payment_method (pix)
- status (pending|completed|failed)
- paid_at
- created_at
```

---

## 🎯 Funcionalidades Específicas Implementadas

### 1. Botões PIX no Bot

```python
# Bot envia automaticamente botões inline com valores
keyboard = [
    [InlineKeyboardButton("💰 R$ 10", callback_data="pix_10")],
    [InlineKeyboardButton("💰 R$ 25", callback_data="pix_25")],
    [InlineKeyboardButton("💰 R$ 50", callback_data="pix_50")],
    [InlineKeyboardButton("💰 R$ 100", callback_data="pix_100")]
]
```

### 2. Processamento de Callback

```python
# Sistema processa clique do usuário e gera PIX
value = callback_data.split('_')[1]  # Extrai valor do botão
pix_data = pushinpay_service.create_pix_payment(user_token, float(value), bot_id)
# Envia QR Code + código PIX para usuário
```

### 3. Ativação Automática via Webhook

```python
# Webhook recebe confirmação da PushinPay
if status == 'approved' or status == 'paid':
    payment.status = 'completed'
    bot.is_active = True
    bot.payment_status = 'paid'
    # Bot é ativado instantaneamente no sistema 24/7
```

---

## 🔒 Segurança

### ✅ Isolamento de Usuários

- Cada usuário só vê/configura seus próprios bots
- Tokens PushinPay são armazenados por usuário
- Validação de propriedade em todas as operações

### ✅ Validação de Tokens

- Tokens Telegram validados via Bot API
- Tokens PushinPay validados via API
- Verificação de permissões em tempo real

### ✅ Webhook Security

- Logs completos de todos os webhooks recebidos
- Validação de dados obrigatórios
- Tratamento de erros e rollback automático

---

## 📊 Dashboard Completo

### ✅ Perfil do Usuário

- Configuração de token PushinPay
- Estatísticas de bots e pagamentos
- Histórico de transações

### ✅ Gestão de Bots

- Lista completa com status
- Criação/edição de bots
- Ativação baseada em pagamento

### ✅ Sistema de Monitoramento

- Bots ativos/inativos em tempo real
- Logs de execução e erros
- Restart automático de bots com falha

---

## 🚀 Deploy e Produção

### Variáveis de Ambiente Necessárias:

```env
SECRET_KEY=sua-chave-secreta-forte
DATABASE_URL=postgresql://user:pass@host:port/db
PUSHINPAY_WEBHOOK_URL=https://seu-dominio.com/webhook/pushinpay
```

### Docker Compose Configurado:

- ✅ PostgreSQL para produção
- ✅ SQLite para desenvolvimento
- ✅ Volume persistence
- ✅ Network isolation
- ✅ Health checks

---

## ✨ Sistema Pronto para Produção

O sistema está **100% funcional** com:

1. **✅ Pagamentos PIX** integrados com PushinPay
2. **✅ Ativação automática** de bots após pagamento
3. **✅ Interface completa** de usuário
4. **✅ Sistema 24/7** com monitoramento
5. **✅ Webhook** para confirmações em tempo real
6. **✅ Taxa fixa** R$ 0,70 com split automático
7. **✅ Limite** de 30 bots por usuário
8. **✅ Isolamento** completo entre usuários

**O sistema está pronto para receber usuários e processar pagamentos automaticamente!** 🎉
