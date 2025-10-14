from typing import Optional, Dict, List
from ..models.offer import Offer, OrderBumpConfig, OfferPayment
from ..models.bot import TelegramBot
from ..models.payment import Payment
from ..database.models import db
from ..utils.logger import logger

class OfferService:
    
    def get_active_order_bump(self, bot_id: int) -> Optional[Offer]:
        """Busca order bump ativo do bot"""
        return Offer.query.filter_by(
            bot_id=bot_id,
            offer_type='order_bump',
            is_active=True
        ).join(OrderBumpConfig).first()
    
    def has_accepted_offer(self, telegram_user_id: int, offer_id: int) -> bool:
        """Verifica se usuário já aceitou uma oferta"""
        count = OfferPayment.query.join(Payment).filter(
            Payment.telegram_user_id == telegram_user_id,
            OfferPayment.offer_id == offer_id
        ).count()
        
        return count > 0
    
    def record_offer_payment(self, offer_id: int, payment_id: int, offer_amount: float) -> OfferPayment:
        """Registra que oferta gerou um pagamento"""
        try:
            offer_payment = OfferPayment(
                offer_id=offer_id,
                payment_id=payment_id,
                offer_amount=offer_amount
            )
            
            db.session.add(offer_payment)
            db.session.commit()
            
            logger.info(f"✅ Oferta registrada: offer_id={offer_id}, payment_id={payment_id}, amount={offer_amount}")
            
            return offer_payment
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao registrar oferta: {e}")
            raise e
    
    def create_order_bump(self, bot_id: int, name: str, message: str, price: float,
                         accept_button_text: str = '✅ Aceitar Oferta',
                         decline_button_text: str = '❌ Não, obrigado',
                         media_image_file_id: str = None,
                         media_video_file_id: str = None,
                         media_audio_file_id: str = None) -> Offer:
        """Cria um novo order bump"""
        try:
            # Cria oferta
            offer = Offer(
                bot_id=bot_id,
                offer_type='order_bump',
                name=name,
                message=message,
                accept_button_text=accept_button_text,
                decline_button_text=decline_button_text,
                media_image_file_id=media_image_file_id,
                media_video_file_id=media_video_file_id,
                media_audio_file_id=media_audio_file_id,
                is_active=True
            )
            
            db.session.add(offer)
            db.session.flush()  # Para obter offer.id
            
            # Cria configuração
            config = OrderBumpConfig(
                offer_id=offer.id,
                price=price
            )
            
            db.session.add(config)
            db.session.commit()
            
            logger.info(f"✅ Order Bump criado: {name} (R$ {price})")
            
            return offer
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao criar order bump: {e}")
            raise e
    
    def update_order_bump(self, offer_id: int, **kwargs) -> Offer:
        """Atualiza order bump existente"""
        try:
            offer = Offer.query.get_or_404(offer_id)
            
            # Atualiza campos da oferta
            for key in ['name', 'message', 'accept_button_text', 'decline_button_text',
                       'media_image_file_id', 'media_video_file_id', 'media_audio_file_id',
                       'is_active']:
                if key in kwargs:
                    setattr(offer, key, kwargs[key])
            
            # Atualiza preço se fornecido
            if 'price' in kwargs and offer.order_bump_config:
                offer.order_bump_config.price = kwargs['price']
            
            db.session.commit()
            
            logger.info(f"✅ Order Bump atualizado: {offer.name}")
            
            return offer
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao atualizar order bump: {e}")
            raise e
    
    def delete_order_bump(self, offer_id: int):
        """Deleta order bump"""
        try:
            offer = Offer.query.get_or_404(offer_id)
            db.session.delete(offer)
            db.session.commit()
            
            logger.info(f"✅ Order Bump deletado: {offer.name}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Erro ao deletar order bump: {e}")
            raise e
    
    def get_order_bump_by_bot(self, bot_id: int) -> List[Offer]:
        """Lista todos os order bumps de um bot"""
        return Offer.query.filter_by(
            bot_id=bot_id,
            offer_type='order_bump'
        ).join(OrderBumpConfig).all()

offer_service = OfferService()