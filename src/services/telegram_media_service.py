"""
Serviço para gerenciar mídia via API do Telegram
Envia arquivos para grupo de notificações e retorna file_id para armazenamento
"""

import os
import asyncio
import tempfile
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

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
    
    def validate_media_file(self, file) -> Dict[str, Any]:
        """Valida arquivo de mídia"""
        if not file or not file.filename:
            return {'valid': False, 'error': 'Nenhum arquivo fornecido'}
        
        filename = file.filename.lower()
        
        # Validação específica para OGG
        if filename.endswith('.ogg') or filename.endswith('.opus'):
            from ..api.routes.bots import validate_ogg_audio_file
            return validate_ogg_audio_file(file)
        
        # Validações para outros tipos
        if filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return {'valid': True, 'media_type': 'photo'}
        elif filename.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            return {'valid': True, 'media_type': 'video'}
        elif filename.endswith(('.mp3', '.wav', '.m4a')):
            return {'valid': True, 'media_type': 'audio'}
        else:
            return {'valid': False, 'error': 'Formato de arquivo não suportado'}
    
    def create_temp_file(self, file, prefix: str = "temp_") -> str:
        """Cria arquivo temporário para upload"""
        # Reset file pointer
        file.seek(0)
        
        # Extrai extensão do arquivo original
        _, ext = os.path.splitext(file.filename)
        
        # Cria arquivo temporário
        temp_fd, temp_path = tempfile.mkstemp(suffix=ext, prefix=prefix)
        
        try:
            # Escreve o conteúdo do arquivo no arquivo temporário
            with os.fdopen(temp_fd, 'wb') as temp_file:
                file.seek(0)  # Garante que está no início
                temp_file.write(file.read())
            
            logger.info(f"📂 Arquivo temporário criado: {temp_path}")
            return temp_path
            
        except Exception as e:
            # Se houve erro, limpa o arquivo temporário
            try:
                os.close(temp_fd)
                os.unlink(temp_path)
            except:
                pass
            raise e
    
    def cleanup_temp_file(self, temp_path: str):
        """Remove arquivo temporário"""
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                logger.info(f"🗑️ Arquivo temporário removido: {temp_path}")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao remover arquivo temporário {temp_path}: {e}")

async def upload_media_to_telegram(bot_token: str, file_path: str, chat_id: str, media_type: str) -> Optional[str]:
    """Upload de mídia para o Telegram com retry e melhor tratamento de erros"""
    bot = Bot(token=bot_token)
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🚀 Tentativa {attempt + 1}/{max_retries} de upload para {chat_id}")
            logger.info(f"📁 Arquivo: {file_path}")
            logger.info(f"🏷️ Tipo: {media_type}")
            
            # Verifica se arquivo existe
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
            # Verifica tamanho do arquivo
            file_size = os.path.getsize(file_path)
            logger.info(f"📊 Tamanho do arquivo: {file_size / 1024 / 1024:.2f}MB")
            
            with open(file_path, 'rb') as media_file:
                if media_type == 'photo':
                    message = await bot.send_photo(
                        chat_id=chat_id,
                        photo=media_file,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=30
                    )
                    file_id = message.photo[-1].file_id  # Pega a maior resolução
                    
                elif media_type == 'video':
                    # Verificar tamanho para vídeos (50MB limite do Telegram)
                    max_video_size = 50 * 1024 * 1024  # 50MB
                    if file_size > max_video_size:
                        logger.error(f"❌ Vídeo muito grande: {file_size/1024/1024:.1f}MB (máx: 50MB)")
                        raise ValueError(f"Vídeo muito grande: {file_size/1024/1024:.1f}MB")
                    
                    message = await bot.send_video(
                        chat_id=chat_id,
                        video=media_file,
                        supports_streaming=True,  # Melhor para vídeos grandes
                        read_timeout=180,  # 3 minutos para vídeos
                        write_timeout=180,
                        connect_timeout=30
                    )
                    file_id = message.video.file_id
                    
                elif media_type == 'voice' or (media_type == 'audio' and file_path.endswith('.ogg')):
                    # Para arquivos OGG, sempre usar como voice message
                    message = await bot.send_voice(
                        chat_id=chat_id,
                        voice=media_file,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=30
                    )
                    file_id = message.voice.file_id
                    
                elif media_type == 'audio':
                    message = await bot.send_audio(
                        chat_id=chat_id,
                        audio=media_file,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=30
                    )
                    file_id = message.audio.file_id
                    
                else:
                    raise ValueError(f"Tipo de mídia não suportado: {media_type}")
            
            logger.info(f"✅ Upload bem-sucedido! File ID: {file_id}")
            return file_id
            
        except Exception as e:
            logger.error(f"❌ Tentativa {attempt + 1} falhou: {e}")
            
            # Log específico para diferentes tipos de erro
            if "File too large" in str(e) or "Request Entity Too Large" in str(e):
                logger.error(f"❌ ERRO: Arquivo muito grande para o Telegram")
                return None  # Não retry para arquivos muito grandes
            elif "Bad Request" in str(e) and "invalid file" in str(e).lower():
                logger.error(f"❌ ERRO: Arquivo corrompido ou formato inválido")
                return None  # Não retry para arquivos inválidos
            elif attempt < max_retries - 1:
                # Espera antes da próxima tentativa
                wait_time = (attempt + 1) * 5  # 5, 10, 15 segundos
                logger.info(f"⏳ Aguardando {wait_time}s antes da próxima tentativa...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ Todas as tentativas de upload falharam")
                return None

def run_async_media_upload(bot_token: str, file_path: str, chat_id: str, bot_id: int, media_type: str) -> Optional[str]:
    """Wrapper síncrono para upload assíncrono de mídia"""
    try:
        # Cria novo loop se necessário
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Executa upload
        return loop.run_until_complete(
            upload_media_to_telegram(bot_token, file_path, chat_id, media_type)
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no wrapper assíncrono: {e}")
        return None