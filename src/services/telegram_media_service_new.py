import os
import tempfile
import mimetypes
import asyncio
import time
import uuid
from typing import Optional, Dict, Any
from telegram import Bot
from telegram.error import TelegramError
from ..utils.logger import logger


class TelegramMediaService:
    """
    Serviço para gerenciar upload e armazenamento de mídia no Telegram
    usando file_id em vez de armazenamento local
    """
    
    def __init__(self):
        """Inicializa o serviço de mídia do Telegram"""
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"📁 Diretório temporário criado: {self.temp_dir}")

    def detect_media_type(self, filename: str) -> str:
        """
        Detecta o tipo de mídia baseado na extensão do arquivo
        
        Args:
            filename: Nome do arquivo
            
        Returns:
            Tipo da mídia: 'image', 'audio', 'video' ou 'document'
        """
        mime_type, _ = mimetypes.guess_type(filename)
        
        if mime_type:
            if mime_type.startswith('image/'):
                return 'image'
            elif mime_type.startswith('audio/'):
                return 'audio'
            elif mime_type.startswith('video/'):
                return 'video'
        
        return 'document'

    async def upload_media_to_telegram(
        self, 
        file_data: bytes,
        filename: str,
        bot_token: str,
        notification_group_id: str,
        bot_identifier: str,
        media_type: str = None
    ) -> Dict[str, Any]:
        """
        Faz upload de mídia para o Telegram e retorna o file_id
        
        Args:
            file_data: Dados binários do arquivo
            filename: Nome do arquivo
            bot_token: Token do bot para fazer o upload
            notification_group_id: ID do grupo de notificações
            bot_identifier: Identificador único do bot (para evitar conflitos)
            media_type: Tipo da mídia (image, audio, video)
            
        Returns:
            Dict com informações do upload incluindo file_id
        """
        temp_file_path = None
        try:
            # Detectar tipo de mídia automaticamente se não fornecido
            if not media_type:
                media_type = self.detect_media_type(filename)
            
            logger.info(f"📤 Iniciando upload de {media_type} para Telegram: {filename}")
            
            # Criar arquivo temporário
            timestamp = int(time.time())
            temp_filename = f"upload_{timestamp}_{filename}"
            temp_file_path = os.path.join(self.temp_dir, temp_filename)
            
            # Escrever dados no arquivo temporário
            with open(temp_file_path, 'wb') as temp_file:
                temp_file.write(file_data)
            
            # Inicializar bot
            bot = Bot(token=bot_token)
            
            # Criar caption com identificador único para evitar conflitos
            caption = f"🤖 **Bot ID: {bot_identifier}**\n📁 {filename}\n🔄 Upload automático"
            
            # Upload baseado no tipo de mídia
            if media_type == 'image':
                with open(temp_file_path, 'rb') as media_file:
                    message = await bot.send_photo(
                        chat_id=notification_group_id,
                        photo=media_file,
                        caption=caption
                    )
                    file_id = message.photo[-1].file_id  # Pega a maior resolução
                    file_unique_id = message.photo[-1].file_unique_id
                
            elif media_type == 'audio':
                with open(temp_file_path, 'rb') as media_file:
                    message = await bot.send_audio(
                        chat_id=notification_group_id,
                        audio=media_file,
                        caption=caption
                    )
                    file_id = message.audio.file_id
                    file_unique_id = message.audio.file_unique_id
                
            elif media_type == 'video':
                with open(temp_file_path, 'rb') as media_file:
                    message = await bot.send_video(
                        chat_id=notification_group_id,
                        video=media_file,
                        caption=caption
                    )
                    file_id = message.video.file_id
                    file_unique_id = message.video.file_unique_id
                
            else:
                # Para documentos genéricos
                with open(temp_file_path, 'rb') as media_file:
                    message = await bot.send_document(
                        chat_id=notification_group_id,
                        document=media_file,
                        caption=caption
                    )
                    file_id = message.document.file_id
                    file_unique_id = message.document.file_unique_id
            
            logger.info(f"✅ Upload concluído com sucesso! File ID: {file_id}")
            
            return {
                'success': True,
                'file_id': file_id,
                'file_unique_id': file_unique_id,
                'media_type': media_type,
                'message_id': message.message_id,
                'bot_identifier': bot_identifier,
                'filename': filename
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no upload da mídia: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'media_type': media_type,
                'bot_identifier': bot_identifier,
                'filename': filename
            }
        
        finally:
            # Limpar arquivo temporário
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    logger.debug(f"🧹 Arquivo temporário removido: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Não foi possível remover arquivo temporário: {e}")

    async def upload_media_from_file(
        self, 
        file_path: str,
        bot_token: str,
        notification_group_id: str,
        bot_identifier: str,
        media_type: str = None
    ) -> Dict[str, Any]:
        """
        Faz upload de mídia a partir de um arquivo local
        
        Args:
            file_path: Caminho para o arquivo local
            bot_token: Token do bot para fazer o upload
            notification_group_id: ID do grupo de notificações
            bot_identifier: Identificador único do bot
            media_type: Tipo da mídia (opcional, será detectado automaticamente)
            
        Returns:
            Dict com informações do upload incluindo file_id
        """
        try:
            # Ler arquivo
            with open(file_path, 'rb') as file:
                file_data = file.read()
            
            filename = os.path.basename(file_path)
            
            # Usar o método principal para fazer o upload
            return await self.upload_media_to_telegram(
                file_data=file_data,
                filename=filename,
                bot_token=bot_token,
                notification_group_id=notification_group_id,
                bot_identifier=bot_identifier,
                media_type=media_type
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao ler arquivo para upload: {str(e)}")
            return {
                'success': False,
                'error': f'Erro ao ler arquivo: {str(e)}',
                'filename': os.path.basename(file_path) if file_path else 'unknown'
            }

    async def get_media_info(self, bot_token: str, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações sobre um arquivo usando file_id
        
        Args:
            bot_token: Token do bot
            file_id: ID do arquivo no Telegram
            
        Returns:
            Dict com informações do arquivo ou None se falhar
        """
        try:
            bot = Bot(token=bot_token)
            file = await bot.get_file(file_id)
            
            return {
                'file_id': file.file_id,
                'file_unique_id': file.file_unique_id,
                'file_size': file.file_size,
                'file_path': file.file_path
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter info da mídia: {e}")
            return None

    def validate_media_file(self, file, media_type: str) -> Dict[str, Any]:
        """
        Valida arquivo de mídia antes do upload
        
        Args:
            file: Arquivo do Flask request
            media_type: Tipo esperado ('image', 'audio' ou 'video')
            
        Returns:
            Dict com resultado da validação
        """
        MAX_SIZE = 50 * 1024 * 1024  # 50MB (limite do Telegram)
        
        # Extensões permitidas
        allowed_extensions = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
            'audio': ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
        }
        
        # Tipos MIME permitidos
        allowed_mime_types = {
            'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'],
            'audio': ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/aac', 'audio/flac'],
            'video': ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/x-flv']
        }
        
        try:
            # Verifica se tem arquivo
            if not file or not file.filename:
                return {'valid': False, 'error': 'Nenhum arquivo selecionado'}
            
            # Verifica extensão
            file_ext = os.path.splitext(file.filename.lower())[1]
            if file_ext not in allowed_extensions.get(media_type, []):
                return {
                    'valid': False, 
                    'error': f'Extensão não permitida para {media_type}. Use: {", ".join(allowed_extensions[media_type])}'
                }
            
            # Lê dados do arquivo
            file_data = file.read()
            file.seek(0)  # Reset para uso posterior
            
            # Verifica tamanho
            if len(file_data) > MAX_SIZE:
                return {
                    'valid': False, 
                    'error': f'Arquivo muito grande. Máximo: 50MB (atual: {len(file_data)/1024/1024:.1f}MB)'
                }
            
            # Verifica se não está vazio
            if len(file_data) == 0:
                return {'valid': False, 'error': 'Arquivo está vazio'}
            
            # Validações específicas por tipo
            if media_type == 'image':
                # Validação básica de imagem
                if not file_data.startswith((b'\xff\xd8', b'\x89PNG', b'GIF8', b'RIFF')):
                    return {'valid': False, 'error': 'Arquivo não parece ser uma imagem válida'}
            
            return {
                'valid': True,
                'file_data': file_data,
                'filename': file.filename,
                'size': len(file_data),
                'extension': file_ext,
                'media_type': media_type
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na validação do arquivo: {e}")
            return {'valid': False, 'error': f'Erro na validação: {str(e)}'}

    def cleanup_temp_files(self):
        """Remove arquivos temporários antigos"""
        try:
            if os.path.exists(self.temp_dir):
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    try:
                        # Remove arquivos mais antigos que 1 hora
                        if os.path.getctime(file_path) < time.time() - 3600:
                            os.remove(file_path)
                            logger.debug(f"🧹 Arquivo temporário antigo removido: {filename}")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao remover arquivo temporário {filename}: {e}")
        except Exception as e:
            logger.error(f"❌ Erro na limpeza de arquivos temporários: {e}")

    def __del__(self):
        """Limpeza ao destruir o objeto"""
        try:
            self.cleanup_temp_files()
        except:
            pass

# Instância global do serviço
telegram_media_service = TelegramMediaService()