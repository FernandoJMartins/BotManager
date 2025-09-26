import requests
import asyncio
from telegram import Bot
from telegram.error import TelegramError

class TelegramValidationService:
    """Serviço para validar tokens do Telegram Bot API"""
    
    @staticmethod
    def validate_bot_token(token: str) -> dict:
        """
        Valida um token do bot do Telegram
        
        Args:
            token (str): Token do bot do Telegram
            
        Returns:
            dict: Informações do bot se válido, ou erro se inválido
        """
        try:
            # Cria instância do bot
            bot = Bot(token=token)
            
            # Tenta obter informações do bot
            bot_info = asyncio.run(bot.get_me())
            
            return {
                'valid': True,
                'bot_id': bot_info.id,
                'username': bot_info.username,
                'first_name': bot_info.first_name,
                'can_join_groups': bot_info.can_join_groups,
                'can_read_all_group_messages': bot_info.can_read_all_group_messages,
                'supports_inline_queries': bot_info.supports_inline_queries
            }
            
        except TelegramError as e:
            return {
                'valid': False,
                'error': f'Token inválido: {str(e)}'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': f'Erro na validação: {str(e)}'
            }
    
    @staticmethod
    def check_bot_permissions(token: str) -> dict:
        """
        Verifica as permissões do bot
        
        Args:
            token (str): Token do bot
            
        Returns:
            dict: Permissões do bot
        """
        try:
            bot = Bot(token=token)
            bot_info = asyncio.run(bot.get_me())
            
            return {
                'can_receive_messages': True,
                'can_send_messages': True,
                'can_send_photos': True,
                'can_send_audio': True,
                'bot_username': bot_info.username,
                'bot_id': bot_info.id
            }
            
        except Exception as e:
            return {
                'error': f'Erro ao verificar permissões: {str(e)}'
            }
    
    @staticmethod
    def set_webhook(token: str, webhook_url: str) -> dict:
        """
        Configura webhook para o bot
        
        Args:
            token (str): Token do bot
            webhook_url (str): URL do webhook
            
        Returns:
            dict: Resultado da configuração do webhook
        """
        try:
            bot = Bot(token=token)
            result = asyncio.run(bot.set_webhook(url=webhook_url))
            
            return {
                'success': result,
                'webhook_url': webhook_url
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao configurar webhook: {str(e)}'
            }