#!/usr/bin/env python3
"""
Script para configurar um bot de teste com valores de exemplo
Execute este script dentro do container Docker para facilitar os testes
"""

import sys
import os

# Adiciona o diretório src ao path
sys.path.insert(0, '/app/src')

try:
    from src.database.models import db
    from src.models.bot import TelegramBot
    from src.app import create_app
    
    # Cria a aplicação Flask
    app = create_app()
    
    with app.app_context():
        # Lista todos os bots para escolher qual configurar
        bots = TelegramBot.query.all()
        
        if not bots:
            print("❌ Nenhum bot encontrado no banco de dados!")
            print("📝 Crie um bot primeiro através da interface web.")
            sys.exit(1)
        
        print("🤖 Bots disponíveis para configurar:")
        for i, bot in enumerate(bots, 1):
            print(f"{i}. {bot.bot_name or bot.bot_username} (ID: {bot.id})")
        
        if len(bots) == 1:
            selected_bot = bots[0]
            print(f"\n🎯 Configurando automaticamente o bot: {selected_bot.bot_name or selected_bot.bot_username}")
        else:
            try:
                choice = input("\n🔢 Digite o número do bot para configurar (Enter para o primeiro): ").strip()
                if not choice:
                    selected_bot = bots[0]
                else:
                    selected_bot = bots[int(choice) - 1]
            except (ValueError, IndexError):
                print("❌ Escolha inválida. Usando o primeiro bot.")
                selected_bot = bots[0]
        
        print(f"\n🔧 Configurando bot: {selected_bot.bot_name or selected_bot.bot_username}")
        
        # Configurações de exemplo para teste
        print("📝 Aplicando configurações de teste...")
        
        # IDs de grupos de exemplo (você deve substituir pelos seus)
        test_vip_group = input("🔸 Digite o ID do grupo VIP (ex: -1002715465964) ou Enter para usar um de teste: ").strip()
        test_log_group = input("🔸 Digite o ID do grupo de LOGS (ex: -1002715465965) ou Enter para usar um de teste: ").strip()
        
        if not test_vip_group:
            test_vip_group = "-1001234567890"  # ID de teste
            print("⚠️  Usando ID de grupo VIP de teste: -1001234567890")
        
        if not test_log_group:
            test_log_group = "-1001234567891"  # ID de teste
            print("⚠️  Usando ID de grupo de LOGS de teste: -1001234567891")
        
        # Atualiza o bot com as configurações
        selected_bot.id_vip = test_vip_group
        selected_bot.id_logs = test_log_group
        selected_bot.pix_values = [10.0, 25.0, 50.0]  # Valores de teste
        selected_bot.plan_names = ["🧪 TESTE VIP", "🧪 TESTE PREMIUM", "🧪 TESTE ELITE"]
        selected_bot.welcome_message = "🧪 Bot de TESTE - Bem-vindo! Use o botão TESTE para simular pagamentos."
        
        # Salva no banco
        db.session.commit()
        
        print("\n✅ Bot configurado com sucesso!")
        print(f"📊 Configurações aplicadas:")
        print(f"   🏆 Grupo VIP: {selected_bot.id_vip}")
        print(f"   📝 Grupo Logs: {selected_bot.id_logs}")
        print(f"   💰 Valores PIX: {selected_bot.pix_values}")
        print(f"   🎁 Nomes dos Planos: {selected_bot.plan_names}")
        
        print(f"\n🎉 Agora você pode testar:")
        print(f"   1. Envie /start para o bot @{selected_bot.bot_username}")
        print(f"   2. Escolha um plano")
        print(f"   3. Clique em '🧪 TESTE - Simular Pagamento'")
        print(f"   4. O bot tentará adicionar você ao grupo VIP!")
        
        print(f"\n⚠️  IMPORTANTE:")
        print(f"   - Se os IDs dos grupos estiverem errados, você verá uma mensagem de erro")
        print(f"   - O bot precisa ser ADMIN nos grupos para gerar links de convite")
        print(f"   - Use grupos reais para testar a funcionalidade completa")

except Exception as e:
    print(f"❌ Erro: {e}")
    sys.exit(1)