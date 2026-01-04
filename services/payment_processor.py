"""
═══════════════════════════════════════════════════════════════════════════════
💰 PAYMENT PROCESSOR — ОБРАБОТКА ПЛАТЕЖЕЙ
═══════════════════════════════════════════════════════════════════════════════
Полный цикл обработки платежа:
1. Создание инвойса
2. Проверка оплаты
3. Применение промокода
4. Активация подписки
5. Выдача доступа
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any, Callable

from aiogram import Bot

logger = logging.getLogger(__name__)


@dataclass
class PaymentResult:
    """Результат обработки платежа."""
    success: bool
    subscription_id: Optional[int] = None
    invite_links: Dict[int, str] = None  # {channel_id: link}
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.invite_links is None:
            self.invite_links = {}


@dataclass
class InvoiceData:
    """Данные для создания инвойса."""
    user_id: int
    telegram_id: int
    subscription_type: str  # 'channel' или 'package'
    item_id: int
    plan_id: int
    amount: Decimal
    description: str
    promocode_id: Optional[int] = None
    discount_amount: Decimal = Decimal("0")
    
    @property
    def final_amount(self) -> Decimal:
        """Итоговая сумма с учётом скидки."""
        return max(self.amount - self.discount_amount, Decimal("0"))


class PaymentProcessor:
    """
    Процессор платежей.
    
    Связывает Crypto Bot API, БД и менеджер каналов.
    """
    
    def __init__(
        self,
        bot: Bot,
        crypto_bot_api,  # CryptoBotAPI
        channel_manager,  # ChannelManager
        get_session: Callable,
        bot_username: Optional[str] = None,
        invoice_lifetime: int = 3600,  # 1 час
    ):
        """
        Инициализация процессора.
        
        Args:
            bot: Экземпляр aiogram Bot
            crypto_bot_api: Клиент Crypto Bot API
            channel_manager: Менеджер каналов
            get_session: Функция получения сессии БД
            bot_username: Username бота (для кнопки после оплаты)
            invoice_lifetime: Время жизни инвойса в секундах
        """
        self.bot = bot
        self.crypto_api = crypto_bot_api
        self.channel_manager = channel_manager
        self.get_session = get_session
        self.bot_username = bot_username
        self.invoice_lifetime = invoice_lifetime
    
    # ═══════════════════════════════════════════════════════════════════════
    # СОЗДАНИЕ ИНВОЙСА
    # ═══════════════════════════════════════════════════════════════════════
    
    async def create_invoice(self, data: InvoiceData) -> Tuple[str, int]:
        """
        Создание инвойса для оплаты.
        
        Args:
            data: Данные для инвойса
            
        Returns:
            Tuple (pay_url, invoice_id)
        """
        from services.crypto_bot import (
            create_payment_payload,
            Currency,
            PaidButtonName,
        )
        from database.crud import PaymentCRUD
        from database.models import PaymentStatus
        
        # Создаём payload
        payload = create_payment_payload(
            user_id=data.user_id,
            subscription_type=data.subscription_type,
            item_id=data.item_id,
            plan_id=data.plan_id,
            promocode_id=data.promocode_id,
        )
        
        # Создаём инвойс в Crypto Bot
        invoice = await self.crypto_api.create_invoice(
            amount=data.final_amount,
            asset=Currency.USDT,
            description=data.description[:1024],
            payload=payload,
            paid_btn_name=PaidButtonName.OPEN_BOT if self.bot_username else None,
            paid_btn_url=f"https://t.me/{self.bot_username}" if self.bot_username else None,
            allow_anonymous=True,
            allow_comments=False,
            expires_in=self.invoice_lifetime,
        )
        
        # Сохраняем в БД
        with self.get_session() as session:
            payment = PaymentCRUD.create(
                session,
                user_id=data.user_id,
                invoice_id=invoice.invoice_id,
                amount=data.final_amount,
                original_amount=data.amount,
                discount_amount=data.discount_amount,
                subscription_type=data.subscription_type,
                channel_id=data.item_id if data.subscription_type == "channel" else None,
                package_id=data.item_id if data.subscription_type == "package" else None,
                plan_id=data.plan_id,
                promocode_id=data.promocode_id,
                status=PaymentStatus.PENDING,
                pay_url=invoice.pay_url,
                expires_at=invoice.expiration_date,
            )
            
            logger.info(
                f"Created invoice #{invoice.invoice_id} for user {data.user_id}: "
                f"${data.final_amount} USDT"
            )
        
        return invoice.pay_url, invoice.invoice_id
    
    async def check_payment_status(self, invoice_id: int) -> Tuple[bool, Optional[str]]:
        """
        Проверка статуса платежа.
        
        Args:
            invoice_id: ID инвойса Crypto Bot
            
        Returns:
            Tuple (is_paid, error_message)
        """
        try:
            invoice = await self.crypto_api.get_invoice(invoice_id)
            
            if not invoice:
                return False, "Invoice not found"
            
            if invoice.is_paid:
                return True, None
            elif invoice.is_expired:
                return False, "Invoice expired"
            else:
                return False, None  # Ещё активен
                
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return False, str(e)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ОБРАБОТКА ОПЛАЧЕННОГО ПЛАТЕЖА
    # ═══════════════════════════════════════════════════════════════════════
    
    async def process_successful_payment(
        self,
        invoice_id: int,
    ) -> PaymentResult:
        """
        Обработка успешного платежа.
        
        Args:
            invoice_id: ID оплаченного инвойса
            
        Returns:
            Результат обработки
        """
        from services.crypto_bot import parse_payment_payload
        from database.crud import (
            PaymentCRUD, UserSubscriptionCRUD, UserCRUD,
            ChannelCRUD, PackageCRUD, PromocodeCRUD,
            SubscriptionPlanCRUD, PackagePlanCRUD,
        )
        from database.models import (
            PaymentStatus, SubscriptionStatus, SubscriptionType,
        )
        
        try:
            with self.get_session() as session:
                # Получаем платёж из БД
                payment = PaymentCRUD.get_by_invoice_id(session, invoice_id)
                
                if not payment:
                    return PaymentResult(
                        success=False,
                        error="Payment not found in database",
                    )
                
                # Проверяем, не обработан ли уже
                if payment.status == PaymentStatus.PAID:
                    # Уже обработан — возвращаем существующую подписку
                    subscription = UserSubscriptionCRUD.get_by_payment_id(
                        session, payment.id
                    )
                    return PaymentResult(
                        success=True,
                        subscription_id=subscription.id if subscription else None,
                    )
                
                # Получаем данные
                user = UserCRUD.get_by_id(session, payment.user_id)
                if not user:
                    return PaymentResult(success=False, error="User not found")
                
                # Определяем тип подписки и длительность
                duration_days = 30  # По умолчанию
                channel_ids = []
                
                if payment.subscription_type == "channel":
                    channel = ChannelCRUD.get_by_id(session, payment.channel_id)
                    if not channel:
                        return PaymentResult(success=False, error="Channel not found")
                    
                    channel_ids = [channel.telegram_id]
                    
                    # Получаем план
                    plan = SubscriptionPlanCRUD.get_by_id(session, payment.plan_id)
                    if plan:
                        duration_days = plan.duration_days
                
                elif payment.subscription_type == "package":
                    package = PackageCRUD.get_by_id(session, payment.package_id)
                    if not package:
                        return PaymentResult(success=False, error="Package not found")
                    
                    # Собираем каналы пакета
                    for pc in package.channels:
                        if pc.channel:
                            channel_ids.append(pc.channel.telegram_id)
                    
                    # Получаем план пакета
                    plan = PackagePlanCRUD.get_by_id(session, payment.plan_id)
                    if plan:
                        duration_days = plan.duration_days
                
                # Вычисляем даты подписки
                start_date = datetime.utcnow()
                end_date = start_date + timedelta(days=duration_days)
                
                # Применяем промокод если есть
                if payment.promocode_id:
                    promocode = PromocodeCRUD.get_by_id(session, payment.promocode_id)
                    if promocode and promocode.promocode_type.value == "bonus_time":
                        # Добавляем бонусные дни
                        bonus_days = promocode.bonus_days or 0
                        end_date += timedelta(days=bonus_days)
                    
                    # Отмечаем использование промокода
                    PromocodeCRUD.record_usage(
                        session,
                        promocode_id=payment.promocode_id,
                        user_id=payment.user_id,
                        payment_id=payment.id,
                    )
                
                # Создаём подписку
                subscription = UserSubscriptionCRUD.create(
                    session,
                    user_id=payment.user_id,
                    subscription_type=SubscriptionType(payment.subscription_type),
                    channel_id=payment.channel_id,
                    package_id=payment.package_id,
                    plan_id=payment.plan_id,
                    payment_id=payment.id,
                    status=SubscriptionStatus.ACTIVE,
                    start_date=start_date,
                    end_date=end_date,
                    auto_renew=False,
                )
                
                # Обновляем статус платежа
                PaymentCRUD.update_status(
                    session, payment.id, PaymentStatus.PAID
                )
                PaymentCRUD.set_paid_at(session, payment.id, datetime.utcnow())
                
                session.commit()
            
            # Создаём invite ссылки (вне транзакции БД)
            invite_links = {}
            
            if channel_ids:
                links = await self.channel_manager.create_links_for_multiple_channels(
                    channel_ids=channel_ids,
                    user_id=user.telegram_id,
                    subscription_end=end_date,
                )
                invite_links = {k: v for k, v in links.items() if v}
            
            logger.info(
                f"Successfully processed payment #{invoice_id} for user {user.telegram_id}: "
                f"subscription #{subscription.id}"
            )
            
            return PaymentResult(
                success=True,
                subscription_id=subscription.id,
                invite_links=invite_links,
            )
            
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return PaymentResult(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════
    # ПРОМОКОДЫ
    # ═══════════════════════════════════════════════════════════════════════
    
    def calculate_discount(
        self,
        promocode_id: int,
        original_amount: Decimal,
    ) -> Tuple[Decimal, str]:
        """
        Расчёт скидки по промокоду.
        
        Args:
            promocode_id: ID промокода
            original_amount: Исходная сумма
            
        Returns:
            Tuple (размер скидки, тип промокода)
        """
        from database.crud import PromocodeCRUD
        from database.models import PromocodeType
        
        with self.get_session() as session:
            promocode = PromocodeCRUD.get_by_id(session, promocode_id)
            
            if not promocode or not promocode.is_active:
                return Decimal("0"), ""
            
            promo_type = promocode.promocode_type
            
            if promo_type == PromocodeType.PERCENT:
                # Процентная скидка
                discount = original_amount * Decimal(str(promocode.discount_percent or 0)) / 100
                return discount, "percent"
            
            elif promo_type == PromocodeType.FIXED:
                # Фиксированная скидка
                discount = Decimal(str(promocode.discount_amount or 0))
                return min(discount, original_amount), "fixed"
            
            elif promo_type == PromocodeType.FREE:
                # Полностью бесплатно
                return original_amount, "free"
            
            elif promo_type == PromocodeType.FREE_DAYS:
                # Бонусные дни (скидки нет)
                return Decimal("0"), "bonus_time"
            
            return Decimal("0"), ""
    
    def validate_promocode(
        self,
        code: str,
        user_id: int,
        subscription_type: Optional[str] = None,
        item_id: Optional[int] = None,
    ) -> Tuple[Optional[int], str]:
        """
        Валидация промокода.
        
        Args:
            code: Код промокода
            user_id: ID пользователя
            subscription_type: Тип подписки (для проверки ограничений)
            item_id: ID канала/пакета
            
        Returns:
            Tuple (promocode_id или None, сообщение об ошибке)
        """
        from database.crud import PromocodeCRUD
        
        with self.get_session() as session:
            promocode = PromocodeCRUD.get_by_code(session, code)
            
            if not promocode:
                return None, "Промокод не найден"
            
            if not promocode.is_active:
                return None, "Промокод неактивен"
            
            # Проверка срока действия
            now = datetime.utcnow()
            if promocode.valid_from and now < promocode.valid_from:
                return None, "Промокод ещё не активен"
            
            if promocode.valid_until and now > promocode.valid_until:
                return None, "Срок действия промокода истёк"
            
            # Проверка лимита использований
            if promocode.max_uses and promocode.current_uses >= promocode.max_uses:
                return None, "Лимит использований исчерпан"
            
            # Проверка, не использовал ли пользователь
            if PromocodeCRUD.is_used_by_user(session, promocode.id, user_id):
                return None, "Вы уже использовали этот промокод"
            
            # Проверка ограничений по каналу/пакету
            if subscription_type == "channel" and promocode.channel_id:
                if promocode.channel_id != item_id:
                    return None, "Промокод не применим к этому каналу"
            
            if subscription_type == "package" and promocode.package_id:
                if promocode.package_id != item_id:
                    return None, "Промокод не применим к этому пакету"
            
            return promocode.id, "OK"
    
    # ═══════════════════════════════════════════════════════════════════════
    # WEBHOOK
    # ═══════════════════════════════════════════════════════════════════════
    
    async def handle_webhook(
        self,
        body: bytes,
        signature: str,
    ) -> Optional[PaymentResult]:
        """
        Обработка webhook от Crypto Bot.
        
        Args:
            body: Тело запроса
            signature: Подпись из заголовка
            
        Returns:
            Результат обработки или None
        """
        import json
        
        # Проверяем подпись
        if not self.crypto_api.verify_webhook_signature(body, signature):
            logger.warning("Invalid webhook signature")
            return None
        
        # Парсим данные
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            logger.error("Invalid webhook JSON")
            return None
        
        # Проверяем тип события
        update_type = data.get("update_type")
        
        if update_type != "invoice_paid":
            logger.debug(f"Ignoring webhook type: {update_type}")
            return None
        
        # Получаем инвойс
        invoice = self.crypto_api.parse_webhook_update(data)
        
        if not invoice:
            logger.error("Failed to parse invoice from webhook")
            return None
        
        # Обрабатываем платёж
        return await self.process_successful_payment(invoice.invoice_id)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ОТМЕНА И ВОЗВРАТ
    # ═══════════════════════════════════════════════════════════════════════
    
    async def cancel_payment(self, invoice_id: int) -> bool:
        """
        Отмена платежа (удаление инвойса).
        
        Args:
            invoice_id: ID инвойса
            
        Returns:
            True если успешно
        """
        from database.crud import PaymentCRUD
        from database.models import PaymentStatus
        
        try:
            # Удаляем в Crypto Bot
            await self.crypto_api.delete_invoice(invoice_id)
            
            # Обновляем статус в БД
            with self.get_session() as session:
                payment = PaymentCRUD.get_by_invoice_id(session, invoice_id)
                if payment:
                    PaymentCRUD.update_status(
                        session, payment.id, PaymentStatus.CANCELLED
                    )
            
            logger.info(f"Cancelled payment #{invoice_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling payment: {e}")
            return False
    
    async def expire_old_payments(self) -> int:
        """
        Отметка просроченных платежей.
        
        Returns:
            Количество обновлённых платежей
        """
        from database.crud import PaymentCRUD
        from database.models import PaymentStatus
        
        count = 0
        now = datetime.utcnow()
        
        with self.get_session() as session:
            # Получаем pending платежи с истекшим сроком
            pending_payments = PaymentCRUD.get_expired_pending(session, now)
            
            for payment in pending_payments:
                PaymentCRUD.update_status(
                    session, payment.id, PaymentStatus.EXPIRED
                )
                count += 1
        
        if count > 0:
            logger.info(f"Expired {count} old payments")
        
        return count


# ═══════════════════════════════════════════════════════════════════════════
# ДОПОЛНИТЕЛЬНЫЕ CRUD МЕТОДЫ
# ═══════════════════════════════════════════════════════════════════════════

def extend_payment_crud():
    """
    Расширение PaymentCRUD дополнительными методами.
    
    Эти методы нужно добавить в database/crud.py
    """
    
    code = '''
    @classmethod
    def get_by_invoice_id(
        cls,
        session: Session,
        invoice_id: int,
    ) -> Optional["Payment"]:
        """Получение платежа по ID инвойса Crypto Bot."""
        return session.query(Payment).filter(
            Payment.invoice_id == invoice_id
        ).first()
    
    @classmethod
    def update_status(
        cls,
        session: Session,
        payment_id: int,
        status: PaymentStatus,
    ) -> bool:
        """Обновление статуса платежа."""
        result = session.query(Payment).filter(
            Payment.id == payment_id
        ).update({"status": status})
        session.commit()
        return result > 0
    
    @classmethod
    def set_paid_at(
        cls,
        session: Session,
        payment_id: int,
        paid_at: datetime,
    ) -> bool:
        """Установка времени оплаты."""
        result = session.query(Payment).filter(
            Payment.id == payment_id
        ).update({"paid_at": paid_at})
        session.commit()
        return result > 0
    
    @classmethod
    def get_expired_pending(
        cls,
        session: Session,
        before_date: datetime,
    ) -> List["Payment"]:
        """Получение просроченных pending платежей."""
        return session.query(Payment).filter(
            Payment.status == PaymentStatus.PENDING,
            Payment.expires_at < before_date,
        ).all()
    '''
    
    return code


def extend_promocode_crud():
    """
    Расширение PromocodeCRUD дополнительными методами.
    """
    
    code = '''
    @classmethod
    def is_used_by_user(
        cls,
        session: Session,
        promocode_id: int,
        user_id: int,
    ) -> bool:
        """Проверка использования промокода пользователем."""
        return session.query(PromocodeUsage).filter(
            PromocodeUsage.promocode_id == promocode_id,
            PromocodeUsage.user_id == user_id,
        ).first() is not None
    
    @classmethod
    def record_usage(
        cls,
        session: Session,
        promocode_id: int,
        user_id: int,
        payment_id: int,
    ) -> "PromocodeUsage":
        """Запись использования промокода."""
        usage = PromocodeUsage(
            promocode_id=promocode_id,
            user_id=user_id,
            payment_id=payment_id,
        )
        session.add(usage)
        
        # Увеличиваем счётчик
        session.query(Promocode).filter(
            Promocode.id == promocode_id
        ).update({"current_uses": Promocode.current_uses + 1})
        
        session.commit()
        return usage
    '''
    
    return code


def extend_user_subscription_crud_for_payment():
    """
    Расширение UserSubscriptionCRUD для платежей.
    """
    
    code = '''
    @classmethod
    def get_by_payment_id(
        cls,
        session: Session,
        payment_id: int,
    ) -> Optional["UserSubscription"]:
        """Получение подписки по ID платежа."""
        return session.query(UserSubscription).filter(
            UserSubscription.payment_id == payment_id
        ).first()
    '''
    
    return code
