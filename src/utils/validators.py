from ..utils.logger import logger

def validate_bot_token(token: str) -> bool:
    if not isinstance(token, str) or len(token) == 0:
        return False
    # Additional validation logic can be added here
    return True

class TelegramValidationService:
    """Serviço para validação de tokens do Telegram"""
    
    def validate_bot_token(self, token: str) -> dict:
        """Valida token do bot e retorna informações"""
        try:
            import requests
            
            logger.info(f"🔍 Validando token: {token[:10]}...")
            
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)
            
            logger.info(f"📡 Response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"❌ Status HTTP inválido: {response.status_code}")
                return {
                    'valid': False,
                    'error': 'Token inválido ou bot não encontrado'
                }
            
            data = response.json()
            logger.info(f"📋 Response data: {data}")
            
            if not data.get('ok'):
                logger.error(f"❌ Telegram API retornou ok=False: {data}")
                return {
                    'valid': False,
                    'error': data.get('description', 'Token inválido')
                }
            
            bot_info = data.get('result', {})
            
            # Extrair informações do bot
            username = bot_info.get('username', '')  # Username sem @
            first_name = bot_info.get('first_name', '')
            bot_id = bot_info.get('id', '')
            
            logger.info(f"🔍 Dados do bot validado:")
            logger.info(f"   - ID: {bot_id}")
            logger.info(f"   - Username (sem @): {username}")
            logger.info(f"   - First name: {first_name}")
            logger.info(f"   - Can join groups: {bot_info.get('can_join_groups', False)}")
            logger.info(f"   - Can read all group messages: {bot_info.get('can_read_all_group_messages', False)}")
            
            if not username:
                logger.warning("⚠️ Bot não tem username configurado!")
            
            if not first_name:
                logger.warning("⚠️ Bot não tem first_name configurado!")
                
            if not bot_id:
                logger.error("❌ Bot não tem ID - isso é crítico!")
                return {
                    'valid': False,
                    'error': 'Bot não possui ID válido'
                }
            
            return {
                'valid': True,
                'username': username,  # Retorna SEM @ para ser formatado depois
                'first_name': first_name,
                'id': bot_id,
                'can_join_groups': bot_info.get('can_join_groups', False),
                'can_read_all_group_messages': bot_info.get('can_read_all_group_messages', False),
                'supports_inline_queries': bot_info.get('supports_inline_queries', False)
            }
            
        except requests.exceptions.RequestException as req_error:
            logger.error(f"❌ Erro de conexão na validação: {req_error}")
            return {
                'valid': False,
                'error': f'Erro de conexão: {str(req_error)}'
            }
        except Exception as e:
            logger.error(f"❌ Erro geral na validação do token: {e}")
            logger.error(f"❌ Stack trace: {str(e)}")
            return {
                'valid': False,
                'error': f'Erro ao validar token: {str(e)}'
            }

def validate_client_id(client_id: str) -> bool:
    if not isinstance(client_id, str) or len(client_id) == 0:
        return False
    # Additional validation logic can be added here
    return True

def validate_payment_value(value: float) -> bool:
    if not isinstance(value, (int, float)) or value <= 0:
        return False
    return True

def validate_webhook_url(url: str) -> bool:
    if not isinstance(url, str) or len(url) == 0:
        return False
    # Additional URL validation logic can be added here
    return True