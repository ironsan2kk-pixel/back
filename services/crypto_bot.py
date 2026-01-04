"""
═══════════════════════════════════════════════════════════════════════════════
💳 CRYPTO BOT API — ПЛАТЕЖИ USDT
═══════════════════════════════════════════════════════════════════════════════
Полная интеграция с Crypto Bot для приёма платежей в USDT.

Функционал:
- Создание инвойсов
- Проверка статуса платежа
- Получение баланса
- Обработка webhook
- Перевод средств
═══════════════════════════════════════════════════════════════════════════════
"""

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Union

import aiohttp

logger = logging.getLogger(__name__)


class CryptoBotError(Exception):
    """Базовое исключение Crypto Bot API."""
    
    def __init__(self, message: str, code: Optional[int] = None):
        self.message = message
        self.code = code
        super().__init__(message)


class InvoiceStatus(str, Enum):
    """Статусы инвойса."""
    ACTIVE = "active"
    PAID = "paid"
    EXPIRED = "expired"


class Currency(str, Enum):
    """Поддерживаемые криптовалюты."""
    USDT = "USDT"
    TON = "TON"
    BTC = "BTC"
    ETH = "ETH"
    LTC = "LTC"
    BNB = "BNB"
    TRX = "TRX"
    USDC = "USDC"


class PaidButtonName(str, Enum):
    """Варианты кнопки после оплаты."""
    VIEW_ITEM = "viewItem"
    OPEN_CHANNEL = "openChannel"
    OPEN_BOT = "openBot"
    CALLBACK = "callback"


@dataclass
class Invoice:
    """Модель инвойса."""
    invoice_id: int
    hash: str
    currency_type: str
    asset: str
    amount: Decimal
    pay_url: str
    mini_app_invoice_url: str
    bot_invoice_url: str
    web_app_invoice_url: str
    description: Optional[str]
    status: InvoiceStatus
    created_at: datetime
    paid_at: Optional[datetime]
    allow_comments: bool
    allow_anonymous: bool
    expiration_date: Optional[datetime]
    paid_anonymously: Optional[bool]
    comment: Optional[str]
    hidden_message: Optional[str]
    payload: Optional[str]
    paid_btn_name: Optional[str]
    paid_btn_url: Optional[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Invoice":
        """Создание из словаря API."""
        return cls(
            invoice_id=data["invoice_id"],
            hash=data.get("hash", ""),
            currency_type=data.get("currency_type", "crypto"),
            asset=data.get("asset", "USDT"),
            amount=Decimal(str(data.get("amount", 0))),
            pay_url=data.get("pay_url", ""),
            mini_app_invoice_url=data.get("mini_app_invoice_url", ""),
            bot_invoice_url=data.get("bot_invoice_url", ""),
            web_app_invoice_url=data.get("web_app_invoice_url", ""),
            description=data.get("description"),
            status=InvoiceStatus(data.get("status", "active")),
            created_at=cls._parse_datetime(data.get("created_at")),
            paid_at=cls._parse_datetime(data.get("paid_at")),
            allow_comments=data.get("allow_comments", False),
            allow_anonymous=data.get("allow_anonymous", False),
            expiration_date=cls._parse_datetime(data.get("expiration_date")),
            paid_anonymously=data.get("paid_anonymously"),
            comment=data.get("comment"),
            hidden_message=data.get("hidden_message"),
            payload=data.get("payload"),
            paid_btn_name=data.get("paid_btn_name"),
            paid_btn_url=data.get("paid_btn_url"),
        )
    
    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        """Парсинг даты из API."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
    
    @property
    def is_paid(self) -> bool:
        """Оплачен ли инвойс."""
        return self.status == InvoiceStatus.PAID
    
    @property
    def is_expired(self) -> bool:
        """Истёк ли инвойс."""
        return self.status == InvoiceStatus.EXPIRED
    
    @property
    def is_active(self) -> bool:
        """Активен ли инвойс."""
        return self.status == InvoiceStatus.ACTIVE


@dataclass
class Balance:
    """Баланс по валюте."""
    currency_code: str
    available: Decimal
    onhold: Decimal
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Balance":
        """Создание из словаря API."""
        return cls(
            currency_code=data.get("currency_code", ""),
            available=Decimal(str(data.get("available", 0))),
            onhold=Decimal(str(data.get("onhold", 0))),
        )
    
    @property
    def total(self) -> Decimal:
        """Общий баланс."""
        return self.available + self.onhold


@dataclass
class ExchangeRate:
    """Курс обмена."""
    is_valid: bool
    is_crypto: bool
    is_fiat: bool
    source: str
    target: str
    rate: Decimal
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExchangeRate":
        """Создание из словаря API."""
        return cls(
            is_valid=data.get("is_valid", False),
            is_crypto=data.get("is_crypto", False),
            is_fiat=data.get("is_fiat", False),
            source=data.get("source", ""),
            target=data.get("target", ""),
            rate=Decimal(str(data.get("rate", 0))),
        )


@dataclass 
class Transfer:
    """Модель перевода."""
    transfer_id: int
    user_id: int
    asset: str
    amount: Decimal
    status: str
    completed_at: datetime
    comment: Optional[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transfer":
        """Создание из словаря API."""
        return cls(
            transfer_id=data.get("transfer_id", 0),
            user_id=data.get("user_id", 0),
            asset=data.get("asset", ""),
            amount=Decimal(str(data.get("amount", 0))),
            status=data.get("status", ""),
            completed_at=Invoice._parse_datetime(data.get("completed_at")) or datetime.utcnow(),
            comment=data.get("comment"),
        )


class CryptoBotAPI:
    """
    Клиент Crypto Bot API.
    
    Документация: https://help.crypt.bot/crypto-pay-api
    """
    
    MAINNET_URL = "https://pay.crypt.bot/api"
    TESTNET_URL = "https://testnet-pay.crypt.bot/api"
    
    def __init__(
        self,
        token: str,
        testnet: bool = False,
        timeout: int = 30,
    ):
        """
        Инициализация клиента.
        
        Args:
            token: API токен Crypto Bot
            testnet: Использовать тестовую сеть
            timeout: Таймаут запросов в секундах
        """
        self.token = token
        self.testnet = testnet
        self.timeout = timeout
        self.base_url = self.TESTNET_URL if testnet else self.MAINNET_URL
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def session(self) -> aiohttp.ClientSession:
        """Получение HTTP сессии."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Crypto-Pay-API-Token": self.token,
                    "Content-Type": "application/json",
                }
            )
        return self._session
    
    async def close(self) -> None:
        """Закрытие сессии."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self) -> "CryptoBotAPI":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
    
    async def _request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Выполнение запроса к API.
        
        Args:
            method: Метод API
            params: Параметры запроса
            
        Returns:
            Результат запроса
            
        Raises:
            CryptoBotError: При ошибке API
        """
        url = f"{self.base_url}/{method}"
        
        # Фильтруем None параметры
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        
        try:
            async with self.session.post(url, json=params or {}) as response:
                data = await response.json()
                
                if not data.get("ok"):
                    error = data.get("error", {})
                    raise CryptoBotError(
                        message=error.get("name", "Unknown error"),
                        code=error.get("code"),
                    )
                
                return data.get("result", {})
                
        except aiohttp.ClientError as e:
            logger.error(f"Crypto Bot API request error: {e}")
            raise CryptoBotError(f"Connection error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Crypto Bot API JSON decode error: {e}")
            raise CryptoBotError(f"Invalid response: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # МЕТОДЫ API
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_me(self) -> Dict[str, Any]:
        """
        Получение информации о приложении.
        
        Returns:
            Информация о боте
        """
        return await self._request("getMe")
    
    async def get_balance(self) -> List[Balance]:
        """
        Получение балансов по всем валютам.
        
        Returns:
            Список балансов
        """
        result = await self._request("getBalance")
        return [Balance.from_dict(item) for item in result]
    
    async def get_balance_by_currency(self, currency: Union[str, Currency]) -> Optional[Balance]:
        """
        Получение баланса по конкретной валюте.
        
        Args:
            currency: Код валюты (USDT, TON, BTC и т.д.)
            
        Returns:
            Баланс или None
        """
        if isinstance(currency, Currency):
            currency = currency.value
            
        balances = await self.get_balance()
        for balance in balances:
            if balance.currency_code == currency:
                return balance
        return None
    
    async def get_exchange_rates(self) -> List[ExchangeRate]:
        """
        Получение курсов обмена.
        
        Returns:
            Список курсов
        """
        result = await self._request("getExchangeRates")
        return [ExchangeRate.from_dict(item) for item in result]
    
    async def get_currencies(self) -> List[Dict[str, Any]]:
        """
        Получение списка поддерживаемых валют.
        
        Returns:
            Список валют
        """
        return await self._request("getCurrencies")
    
    async def create_invoice(
        self,
        amount: Union[Decimal, float, str],
        currency_type: str = "crypto",
        asset: Union[str, Currency] = Currency.USDT,
        description: Optional[str] = None,
        hidden_message: Optional[str] = None,
        paid_btn_name: Optional[Union[str, PaidButtonName]] = None,
        paid_btn_url: Optional[str] = None,
        payload: Optional[str] = None,
        allow_comments: bool = False,
        allow_anonymous: bool = True,
        expires_in: Optional[int] = None,
    ) -> Invoice:
        """
        Создание инвойса для оплаты.
        
        Args:
            amount: Сумма оплаты
            currency_type: Тип валюты ('crypto' или 'fiat')
            asset: Криптовалюта (USDT, TON, BTC и т.д.)
            description: Описание платежа (до 1024 символов)
            hidden_message: Скрытое сообщение после оплаты (до 2048 символов)
            paid_btn_name: Название кнопки после оплаты
            paid_btn_url: URL кнопки после оплаты
            payload: Пользовательские данные (до 4096 символов)
            allow_comments: Разрешить комментарии
            allow_anonymous: Разрешить анонимную оплату
            expires_in: Время жизни в секундах (60-2678400, ~31 день)
            
        Returns:
            Созданный инвойс
        """
        if isinstance(asset, Currency):
            asset = asset.value
            
        if isinstance(paid_btn_name, PaidButtonName):
            paid_btn_name = paid_btn_name.value
        
        params = {
            "currency_type": currency_type,
            "asset": asset,
            "amount": str(amount),
            "description": description,
            "hidden_message": hidden_message,
            "paid_btn_name": paid_btn_name,
            "paid_btn_url": paid_btn_url,
            "payload": payload,
            "allow_comments": allow_comments,
            "allow_anonymous": allow_anonymous,
            "expires_in": expires_in,
        }
        
        result = await self._request("createInvoice", params)
        invoice = Invoice.from_dict(result)
        
        logger.info(
            f"Created invoice #{invoice.invoice_id}: "
            f"{invoice.amount} {invoice.asset}"
        )
        
        return invoice
    
    async def delete_invoice(self, invoice_id: int) -> bool:
        """
        Удаление инвойса.
        
        Args:
            invoice_id: ID инвойса
            
        Returns:
            True если удалён
        """
        result = await self._request("deleteInvoice", {"invoice_id": invoice_id})
        return result is True or result == {}
    
    async def get_invoices(
        self,
        asset: Optional[Union[str, Currency]] = None,
        invoice_ids: Optional[List[int]] = None,
        status: Optional[Union[str, InvoiceStatus]] = None,
        offset: int = 0,
        count: int = 100,
    ) -> List[Invoice]:
        """
        Получение списка инвойсов.
        
        Args:
            asset: Фильтр по валюте
            invoice_ids: Фильтр по ID
            status: Фильтр по статусу
            offset: Смещение
            count: Количество (макс. 1000)
            
        Returns:
            Список инвойсов
        """
        if isinstance(asset, Currency):
            asset = asset.value
            
        if isinstance(status, InvoiceStatus):
            status = status.value
        
        params = {
            "asset": asset,
            "invoice_ids": ",".join(map(str, invoice_ids)) if invoice_ids else None,
            "status": status,
            "offset": offset,
            "count": min(count, 1000),
        }
        
        result = await self._request("getInvoices", params)
        items = result.get("items", []) if isinstance(result, dict) else result
        return [Invoice.from_dict(item) for item in items]
    
    async def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """
        Получение инвойса по ID.
        
        Args:
            invoice_id: ID инвойса
            
        Returns:
            Инвойс или None
        """
        invoices = await self.get_invoices(invoice_ids=[invoice_id])
        return invoices[0] if invoices else None
    
    async def check_invoice_paid(self, invoice_id: int) -> bool:
        """
        Проверка оплаты инвойса.
        
        Args:
            invoice_id: ID инвойса
            
        Returns:
            True если оплачен
        """
        invoice = await self.get_invoice(invoice_id)
        return invoice.is_paid if invoice else False
    
    async def transfer(
        self,
        user_id: int,
        asset: Union[str, Currency],
        amount: Union[Decimal, float, str],
        spend_id: str,
        comment: Optional[str] = None,
        disable_send_notification: bool = False,
    ) -> Transfer:
        """
        Перевод средств пользователю Telegram.
        
        Args:
            user_id: Telegram ID получателя
            asset: Валюта
            amount: Сумма
            spend_id: Уникальный ID операции (для идемпотентности)
            comment: Комментарий
            disable_send_notification: Отключить уведомление
            
        Returns:
            Информация о переводе
        """
        if isinstance(asset, Currency):
            asset = asset.value
        
        params = {
            "user_id": user_id,
            "asset": asset,
            "amount": str(amount),
            "spend_id": spend_id,
            "comment": comment,
            "disable_send_notification": disable_send_notification,
        }
        
        result = await self._request("transfer", params)
        transfer = Transfer.from_dict(result)
        
        logger.info(
            f"Transfer #{transfer.transfer_id} to user {user_id}: "
            f"{transfer.amount} {transfer.asset}"
        )
        
        return transfer
    
    async def get_transfers(
        self,
        asset: Optional[Union[str, Currency]] = None,
        transfer_ids: Optional[List[int]] = None,
        offset: int = 0,
        count: int = 100,
    ) -> List[Transfer]:
        """
        Получение списка переводов.
        
        Args:
            asset: Фильтр по валюте
            transfer_ids: Фильтр по ID
            offset: Смещение
            count: Количество
            
        Returns:
            Список переводов
        """
        if isinstance(asset, Currency):
            asset = asset.value
        
        params = {
            "asset": asset,
            "transfer_ids": ",".join(map(str, transfer_ids)) if transfer_ids else None,
            "offset": offset,
            "count": min(count, 1000),
        }
        
        result = await self._request("getTransfers", params)
        items = result.get("items", []) if isinstance(result, dict) else result
        return [Transfer.from_dict(item) for item in items]
    
    # ═══════════════════════════════════════════════════════════════════════
    # WEBHOOK
    # ═══════════════════════════════════════════════════════════════════════
    
    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
    ) -> bool:
        """
        Проверка подписи webhook.
        
        Args:
            body: Тело запроса (bytes)
            signature: Значение заголовка crypto-pay-api-signature
            
        Returns:
            True если подпись верна
        """
        # Создаём секрет из токена
        secret = hashlib.sha256(self.token.encode()).digest()
        
        # Вычисляем HMAC
        expected_signature = hmac.new(
            secret,
            body,
            hashlib.sha256,
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    def parse_webhook_update(self, data: Dict[str, Any]) -> Optional[Invoice]:
        """
        Парсинг webhook обновления.
        
        Args:
            data: Данные webhook
            
        Returns:
            Инвойс если это invoice_paid событие
        """
        update_type = data.get("update_type")
        
        if update_type == "invoice_paid":
            payload = data.get("payload", {})
            return Invoice.from_dict(payload)
        
        return None


# ═══════════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════════

def create_payment_payload(
    user_id: int,
    subscription_type: str,  # 'channel' или 'package'
    item_id: int,
    plan_id: int,
    promocode_id: Optional[int] = None,
) -> str:
    """
    Создание payload для инвойса.
    
    Args:
        user_id: ID пользователя
        subscription_type: Тип подписки
        item_id: ID канала или пакета
        plan_id: ID тарифного плана
        promocode_id: ID промокода (опционально)
        
    Returns:
        JSON строка payload
    """
    data = {
        "u": user_id,
        "t": subscription_type,
        "i": item_id,
        "p": plan_id,
    }
    
    if promocode_id:
        data["promo"] = promocode_id
    
    return json.dumps(data, separators=(',', ':'))


def parse_payment_payload(payload: str) -> Dict[str, Any]:
    """
    Парсинг payload из инвойса.
    
    Args:
        payload: JSON строка payload
        
    Returns:
        Словарь с данными
    """
    try:
        data = json.loads(payload)
        return {
            "user_id": data.get("u"),
            "subscription_type": data.get("t"),
            "item_id": data.get("i"),
            "plan_id": data.get("p"),
            "promocode_id": data.get("promo"),
        }
    except (json.JSONDecodeError, TypeError):
        return {}


async def create_subscription_invoice(
    api: CryptoBotAPI,
    user_id: int,
    amount: Decimal,
    description: str,
    subscription_type: str,
    item_id: int,
    plan_id: int,
    promocode_id: Optional[int] = None,
    bot_username: Optional[str] = None,
    expires_in: int = 3600,  # 1 час
) -> Invoice:
    """
    Создание инвойса для подписки.
    
    Args:
        api: Экземпляр CryptoBotAPI
        user_id: ID пользователя
        amount: Сумма
        description: Описание
        subscription_type: 'channel' или 'package'
        item_id: ID канала/пакета
        plan_id: ID тарифа
        promocode_id: ID промокода
        bot_username: Username бота для кнопки
        expires_in: Время жизни инвойса
        
    Returns:
        Созданный инвойс
    """
    payload = create_payment_payload(
        user_id=user_id,
        subscription_type=subscription_type,
        item_id=item_id,
        plan_id=plan_id,
        promocode_id=promocode_id,
    )
    
    # Кнопка после оплаты
    paid_btn_name = None
    paid_btn_url = None
    
    if bot_username:
        paid_btn_name = PaidButtonName.OPEN_BOT
        paid_btn_url = f"https://t.me/{bot_username}"
    
    return await api.create_invoice(
        amount=amount,
        asset=Currency.USDT,
        description=description[:1024] if description else None,
        payload=payload,
        paid_btn_name=paid_btn_name,
        paid_btn_url=paid_btn_url,
        allow_anonymous=True,
        allow_comments=False,
        expires_in=expires_in,
    )
