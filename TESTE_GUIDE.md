# 🧪 **GUIA DE TESTE - Sistema de Adição Automática aos Grupos**

## 🚀 **IMPLEMENTADO COM SUCESSO:**

### ✅ **1. Sistema de Teste Sem Pagamento PIX**

- 🧪 **Botão "TESTE - Simular Pagamento"** em cada PIX gerado
- ✅ **Simula pagamento aprovado** instantaneamente
- 🎯 **Testa toda a funcionalidade** sem custos
- 📝 **Logs completos** do processo de teste

### ✅ **2. Colunas do Banco de Dados Criadas**

- 🗄️ **`id_vip`** - ID do grupo VIP (entregável)
- 📝 **`id_logs`** - ID do grupo de notificações
- ✅ **Migração executada** com sucesso

---

## 🔧 **COMO CONFIGURAR PARA TESTE:**

### **Passo 1: Configure um bot de teste**

```bash
# Execute dentro do container:
docker-compose exec telegram-bot-manager python /app/setup_test_bot.py
```

### **Passo 2: Obtenha os IDs dos grupos**

1. **Crie dois grupos no Telegram**:

   - 🏆 **Grupo VIP** (onde os clientes serão adicionados)
   - 📝 **Grupo de Logs** (para notificações)

2. **Adicione o bot como ADMIN** em ambos os grupos

3. **Obtenha os IDs dos grupos**:
   - Adicione `@userinfobot` aos grupos
   - Ele mostrará o ID (formato: `-1002715465964`)

### **Passo 3: Configure no banco ou interface web**

```sql
-- Via SQL direto:
UPDATE telegram_bots
SET id_vip = '-1002715465964',
    id_logs = '-1002715465965'
WHERE id = 1;
```

**OU** configure pela interface web do dashboard.

---

## 🧪 **COMO TESTAR:**

### **1. Teste Completo**

1. 📱 **Envie `/start`** para seu bot no Telegram
2. 🎁 **Escolha um plano** (qualquer valor)
3. 🧪 **Clique em "TESTE - Simular Pagamento"**
4. ✅ **Aguarde o resultado:**
   - Se configurado corretamente: Link de convite enviado
   - Se erro: Mensagem explicando o problema

### **2. Verificação de Logs**

- 📝 **Grupo de logs** receberá notificação automática
- 🎯 **Logs no terminal** do container
- 📊 **Status no banco** atualizado para `approved`

### **3. Teste de Grupo VIP**

- 👑 **Cliente recebe link** de convite exclusivo
- 🔗 **Link funciona apenas 1 vez**
- ⚡ **Entrada automática** no grupo

---

## 🛠️ **COMANDOS ÚTEIS:**

### **Ver logs em tempo real:**

```bash
docker-compose logs -f telegram-bot-manager
```

### **Executar script de configuração:**

```bash
docker-compose exec telegram-bot-manager python /app/setup_test_bot.py
```

### **Verificar banco de dados:**

```bash
docker-compose exec postgres psql -U postgres -d telegram_bot_manager -c "SELECT bot_name, id_vip, id_logs FROM telegram_bots;"
```

### **Resetar pagamentos de teste:**

```bash
docker-compose exec postgres psql -U postgres -d telegram_bot_manager -c "DELETE FROM payments WHERE status = 'approved';"
```

---

## 🎯 **CENÁRIOS DE TESTE:**

### ✅ **Teste de Sucesso:**

- ✅ Bot é admin nos grupos
- ✅ IDs dos grupos corretos
- ✅ Cliente recebe link de convite
- ✅ Notificação enviada para logs

### ❌ **Teste de Erro:**

- ❌ IDs de grupos inválidos
- ❌ Bot não é admin
- ❌ Grupos não existem
- ❌ Logs mostram o erro específico

---

## 🚨 **IMPORTANTE:**

### **⚠️ Só para Desenvolvimento:**

- 🧪 O botão de TESTE **só deve existir em desenvolvimento**
- 🔒 **Remova em produção** para evitar fraudes
- 🎯 Use apenas para **validar a funcionalidade**

### **🔑 Requisitos:**

- Bot deve ser **ADMIN** nos grupos
- IDs devem estar no formato **`-1002715465964`**
- Grupos devem **existir e estar ativos**

---

## 🎉 **RESULTADO ESPERADO:**

Quando tudo funcionar:

1. 🧪 **Cliente clica** "TESTE - Simular Pagamento"
2. ⚡ **Sistema processa** instantaneamente
3. 📧 **Link de convite** enviado ao cliente
4. 📝 **Notificação** enviada ao grupo de logs
5. 🎊 **Cliente entra** automaticamente no grupo VIP

**Sistema 100% funcional para testes! 🚀**
