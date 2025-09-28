# 🔧 Sistema de Edição de Bots - Guia de Uso

## 📋 **Funcionalidades Implementadas**

### ✅ **Sistema Completo de Edição**

- **URL de Edição**: `/bots/edit/{id_do_bot}`
- **Controle de Acesso**: Apenas o dono do bot ou admin pode editar
- **Segurança**: Verificação de permissões em cada acesso

### ✅ **Campos Editáveis**

#### **1. Informações Básicas**

- ✏️ Nome do Bot
- 🔑 Token do Bot (⚠️ Alterar token reinicia o bot automaticamente)
- 💬 Mensagem de Boas-vindas

#### **2. Mídia de Boas-vindas**

- 🖼️ Imagem de Boas-vindas (novo upload substitui anterior)
- 🔊 Áudio de Boas-vindas (novo upload substitui anterior)
- ℹ️ Mostra arquivo atual se houver

#### **3. Planos e Valores PIX**

- 💰 Valores PIX (R$) - Mínimo 0.01
- 🏷️ Nomes dos Planos (até 50 caracteres)
- ➕ Adicionar novos planos (máximo 10)
- 🗑️ Remover planos existentes

#### **4. Configurações de Grupos**

- 👑 **ID do Grupo VIP**: Onde clientes são adicionados após pagamento
- 📋 **ID do Grupo de Logs**: Onde são enviadas notificações de pagamento
- 🔧 **Formatação Automática**: Adiciona `-` automaticamente nos IDs

## 🚀 **Como Usar**

### **Passo 1: Acessar Edição**

1. Vá para a lista de bots (`/bots/`)
2. Clique no botão ✏️ **Editar** do bot desejado
3. Será redirecionado para `/bots/edit/{id_do_bot}`

### **Passo 2: Editar Configurações**

1. **Informações Básicas**: Altere nome, token ou mensagem
2. **Mídia**: Faça upload de nova imagem/áudio (opcional)
3. **Planos**: Configure valores e nomes dos planos
4. **Grupos**: Configure IDs dos grupos VIP e Logs

### **Passo 3: Salvar**

1. Clique em **"Salvar Alterações"**
2. Sistema validará os dados
3. Alterações serão aplicadas imediatamente
4. Se alterar token, bot será reiniciado automaticamente

## 🛡️ **Segurança e Validações**

### **Controle de Acesso**

```python
# Apenas o dono do bot ou admin pode editar
if bot.user_id != current_user.id and not current_user.is_admin:
    flash('Você não tem permissão para editar este bot.', 'error')
    return redirect(url_for('bots.list_bots'))
```

### **Validações Implementadas**

- ✅ Token deve estar no formato correto: `123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw`
- ✅ Pelo menos um valor PIX deve ser configurado
- ✅ Valores PIX devem ser maiores que R$ 0,01
- ✅ IDs de grupos são formatados automaticamente
- ✅ Arquivos de mídia devem ter extensões permitidas

### **Formatação Automática de Grupos**

```python
# Remove @ e prefixos, adiciona - se necessário
if id_vip:
    id_vip = id_vip.replace('@', '').replace('https://t.me/', '')
    if not id_vip.startswith('-'):
        id_vip = '-' + id_vip
    bot.id_vip = id_vip
```

## 📱 **Interface do Usuário**

### **Design Responsivo**

- 📱 Funciona perfeitamente em mobile e desktop
- 🎨 Interface moderna com gradientes e animações
- 💫 Efeitos visuais suaves e profissionais

### **Feedback Visual**

- ✅ Status do bot (Online/Offline, Configurado/Incompleto)
- 📊 Indicadores de arquivos atuais
- ⚡ Validação em tempo real
- 🔔 Notificações de sucesso/erro

## 🔧 **Como Obter ID do Grupo**

### **Método Recomendado**

1. Adicione o bot `@userinfobot` ao seu grupo
2. Digite `/start` no grupo
3. O bot retornará o ID do grupo (ex: `-1001234567890`)
4. Remova o `@userinfobot` do grupo
5. Adicione seu bot ao grupo e torne-o administrador
6. Use o ID obtido na configuração

### **Exemplos de IDs Válidos**

- `-1001234567890` (Grupo/Canal privado)
- `-1001111111111` (Supergrupo)
- O sistema adiciona automaticamente o `-` se não estiver presente

## ⚡ **Recursos Avançados**

### **Status Inteligente**

- 🟢 **Totalmente Configurado**: Bot tem token, grupos e valores PIX
- 🟡 **Configuração Incompleta**: Faltam informações essenciais
- 🔴 **Offline**: Bot não está rodando

### **Atualização Dinâmica**

- Alterações são aplicadas imediatamente
- Log detalhado de todas as modificações
- Histórico de changes preservado

## 🎯 **Próximos Passos para Testar**

1. **Acesse**: `http://localhost:5000/bots/`
2. **Clique em Editar** em qualquer bot existente
3. **Teste as funcionalidades**:
   - Altere nome e mensagem
   - Configure IDs de grupos
   - Adicione/remova planos
   - Faça upload de mídia
4. **Salve** e verifique se as alterações foram aplicadas

---

## 🚨 **Importante**

⚠️ **Alterar o token do bot fará com que ele seja reiniciado automaticamente**

✅ **Todas as alterações são salvas no banco de dados instantaneamente**

🔒 **Apenas o dono do bot pode editá-lo (exceto admins)**
