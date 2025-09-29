"""
Serviço para gerenciar mídia via API do Telegram
Envia arquivos para grupo de notificações e retorna file_id para armazenamento
"""

import os
import asyncio
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any
from telegram import Bot
from telegram.error import TelegramError
from ..utils.logger import logger

class TelegramMediaService:
    """Serviço para gerenciar upload e armazenamento de mídia via Telegram"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
    
    async def upload_media_to_telegram(self, 
                                     file_path: str, 
                                     log_group_id: str, 
                                     bot_id: int,
                                     media_type: str = "photo") -> Optional[str]:
        """
        Envia mídia para o grupo de logs do Telegram e retorna o file_id
        
        Args:
            file_path: Caminho do arquivo local
            log_group_id: ID do grupo onde armazenar a mídia
            bot_id: ID do bot (para identificação)
            media_type: Tipo da mídia (photo, audio, video)
            
        Returns:
            file_id do Telegram ou None se falhar
        """
        try:
            if not log_group_id:
                logger.error("❌ ID do grupo de logs não configurado")
                return None
            
            # Verifica se o arquivo existe
            if not os.path.exists(file_path):
                logger.error(f"❌ Arquivo não encontrado: {file_path}")
                return None
            
            # Mensagem identificadora
            caption = f"📁 Bot ID: {bot_id} | Mídia: {media_type} | Upload: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}"
            
            logger.info(f"📤 Enviando {media_type} para grupo {log_group_id}")
            
            with open(file_path, 'rb') as media_file:
                if media_type == "photo":
                    message = await self.bot.send_photo(
                        chat_id=log_group_id,
                        photo=media_file,
                        caption=caption
                    )
                    file_id = message.photo[-1].file_id  # Pega a maior resolução
                    
                elif media_type == "audio":
                    message = await self.bot.send_audio(
                        chat_id=log_group_id,
                        audio=media_file,
                        caption=caption
                    )
                    file_id = message.audio.file_id
                    
                elif media_type == "video":
                    message = await self.bot.send_video(
                        chat_id=log_group_id,
                        video=media_file,
                        caption=caption
                    )
                    file_id = message.video.file_id
                    
                else:
                    logger.error(f"❌ Tipo de mídia não suportado: {media_type}")
                    return None
            
            logger.info(f"✅ Mídia enviada com sucesso! File ID: {file_id}")
            return file_id
            
        except TelegramError as e:
            logger.error(f"❌ Erro do Telegram ao enviar {media_type}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro geral ao enviar {media_type}: {e}")
            return None
    
    async def send_media_by_file_id(self, 
                                  chat_id: str, 
                                  file_id: str, 
                                  media_type: str = "photo",
                                  caption: str = None) -> bool:
        """
        Envia mídia usando file_id do Telegram
        
        Args:
            chat_id: ID do chat de destino
            file_id: File ID da mídia no Telegram
            media_type: Tipo da mídia
            caption: Legenda opcional
            
        Returns:
            True se enviou com sucesso, False caso contrário
        """
        try:
            if media_type == "photo":
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=caption
                )
            elif media_type == "audio":
                await self.bot.send_audio(
                    chat_id=chat_id,
                    audio=file_id,
                    caption=caption
                )
            elif media_type == "video":
                await self.bot.send_video(
                    chat_id=chat_id,
                    video=file_id,
                    caption=caption
                )
            else:
                logger.error(f"❌ Tipo de mídia não suportado: {media_type}")
                return False
                
            logger.info(f"✅ Mídia {media_type} enviada via file_id")
            return True
            
        except TelegramError as e:
            logger.error(f"❌ Erro do Telegram ao enviar mídia via file_id: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro geral ao enviar mídia via file_id: {e}")
            return False
    
    def validate_media_file(self, file, allowed_types: dict = None) -> Dict[str, Any]:
        """
        Valida arquivo de mídia
        
        Args:
            file: Arquivo do upload
            allowed_types: Tipos permitidos
            
        Returns:
            Dict com informações da validação
        """
        if not file or not file.filename:
            return {
                'valid': False,
                'error': 'Nenhum arquivo selecionado'
            }
        
        # Tipos padrão permitidos
        if allowed_types is None:
            allowed_types = {
                'photo': ['png', 'jpg', 'jpeg', 'gif'],
                'audio': ['mp3', 'wav', 'ogg', 'm4a'],
                'video': ['mp4', 'avi', 'mkv', 'mov']
            }
        
        # Obtém extensão
        filename = file.filename.lower()
        extension = filename.rsplit('.', 1)[1] if '.' in filename else ''
        
        # Determina tipo de mídia
        media_type = None
        for type_name, extensions in allowed_types.items():
            if extension in extensions:
                media_type = type_name
                break
        
        if not media_type:
            return {
                'valid': False,
                'error': f'Tipo de arquivo não suportado: .{extension}'
            }
        
        # Verifica tamanho (25MB = 25 * 1024 * 1024 bytes)
        max_size = 25 * 1024 * 1024
        if hasattr(file, 'content_length') and file.content_length > max_size:
            return {
                'valid': False,
                'error': 'Arquivo muito grande. Máximo: 25MB'
            }
        
        return {
            'valid': True,
            'media_type': media_type,
            'extension': extension,
            'filename': filename
        }
    
    def create_temp_file(self, file, prefix: str = "media_") -> str:
        """
        Cria arquivo temporário para upload
        
        Args:
            file: Arquivo do upload
            prefix: Prefixo do arquivo temporário
            
        Returns:
            Caminho do arquivo temporário
        """
        # Cria arquivo temporário
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=f".{file.filename.rsplit('.', 1)[1]}" if '.' in file.filename else '',
            prefix=prefix
        )
        
        try:
            # Salva o arquivo
            with os.fdopen(temp_fd, 'wb') as temp_file:
                file.save(temp_file)
            return temp_path
        except Exception as e:
            # Remove arquivo em caso de erro
            os.close(temp_fd)
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def cleanup_temp_file(self, temp_path: str):
        """Remove arquivo temporário"""
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                logger.info(f"🗑️  Arquivo temporário removido: {temp_path}")
        except Exception as e:
            logger.warning(f"⚠️  Erro ao remover arquivo temporário {temp_path}: {e}")

# Função auxiliar para uso em rotas síncronas
def run_async_media_upload(bot_token: str, file_path: str, log_group_id: str, bot_id: int, media_type: str) -> Optional[str]:
    """Wrapper síncrono para upload de mídia"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        service = TelegramMediaService(bot_token)
        return loop.run_until_complete(
            service.upload_media_to_telegram(file_path, log_group_id, bot_id, media_type)
        )
    except Exception as e:
        logger.error(f"❌ Erro no upload síncrono: {e}")
        return None
    finally:
        loop.close()