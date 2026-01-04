"""
═══════════════════════════════════════════════════════════════════════════════
📢 CHANNEL MANAGER — УПРАВЛЕНИЕ КАНАЛАМИ TELEGRAM
═══════════════════════════════════════════════════════════════════════════════
Управление доступом к приватным каналам:
- Создание и отзыв invite ссылок
- Добавление и удаление пользователей
- Проверка членства
- Получение информации о канале
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Union, Tuple
from enum import Enum

from aiogram import Bot
from aiogram.types import (
    ChatInviteLink,
    ChatMember,
    ChatMemberOwner,
    ChatMemberAdministrator,
    ChatMemberMember,
    ChatMemberRestricted,
    ChatMemberLeft,
    ChatMemberBanned,
    Chat,
)
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramAPIError,
)

logger = logging.getLogger(__name__)


class MemberStatus(str, Enum):
    """Статусы членства в канале."""
    OWNER = "creator"
    ADMIN = "administrator"
    MEMBER = "member"
    RESTRICTED = "restricted"
    LEFT = "left"
    BANNED = "kicked"
    UNKNOWN = "unknown"


class ChannelError(Exception):
    """Базовое исключение управления каналами."""
    pass


class ChannelNotFoundError(ChannelError):
    """Канал не найден."""
    pass


class BotNotAdminError(ChannelError):
    """Бот не является администратором."""
    pass


class UserNotFoundError(ChannelError):
    """Пользователь не найден."""
    pass


class InviteLinkError(ChannelError):
    """Ошибка создания invite ссылки."""
    pass


@dataclass
class ChannelInfo:
    """Информация о канале."""
    id: int
    title: str
    username: Optional[str]
    description: Optional[str]
    member_count: int
    invite_link: Optional[str]
    is_private: bool
    
    @classmethod
    def from_chat(cls, chat: Chat, member_count: int = 0) -> "ChannelInfo":
        """Создание из объекта Chat."""
        return cls(
            id=chat.id,
            title=chat.title or "",
            username=chat.username,
            description=getattr(chat, 'description', None),
            member_count=member_count,
            invite_link=getattr(chat, 'invite_link', None),
            is_private=chat.username is None,
        )


@dataclass
class InviteLinkInfo:
    """Информация об invite ссылке."""
    link: str
    name: Optional[str]
    creator_id: int
    creates_join_request: bool
    is_primary: bool
    is_revoked: bool
    expire_date: Optional[datetime]
    member_limit: Optional[int]
    pending_join_request_count: int
    
    @classmethod
    def from_link(cls, link: ChatInviteLink) -> "InviteLinkInfo":
        """Создание из ChatInviteLink."""
        return cls(
            link=link.invite_link,
            name=link.name,
            creator_id=link.creator.id if link.creator else 0,
            creates_join_request=link.creates_join_request or False,
            is_primary=link.is_primary or False,
            is_revoked=link.is_revoked or False,
            expire_date=link.expire_date,
            member_limit=link.member_limit,
            pending_join_request_count=link.pending_join_request_count or 0,
        )


class ChannelManager:
    """
    Менеджер каналов Telegram.
    
    Обеспечивает управление приватными каналами:
    - Создание временных invite ссылок
    - Кик пользователей при истечении подписки
    - Проверка членства
    """
    
    def __init__(self, bot: Bot):
        """
        Инициализация менеджера.
        
        Args:
            bot: Экземпляр aiogram Bot
        """
        self.bot = bot
    
    # ═══════════════════════════════════════════════════════════════════════
    # ИНФОРМАЦИЯ О КАНАЛЕ
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_channel_info(self, channel_id: int) -> ChannelInfo:
        """
        Получение информации о канале.
        
        Args:
            channel_id: ID канала
            
        Returns:
            Информация о канале
            
        Raises:
            ChannelNotFoundError: Канал не найден
            BotNotAdminError: Бот не админ
        """
        try:
            chat = await self.bot.get_chat(channel_id)
            member_count = await self.bot.get_chat_member_count(channel_id)
            return ChannelInfo.from_chat(chat, member_count)
            
        except TelegramNotFound:
            raise ChannelNotFoundError(f"Channel {channel_id} not found")
        except TelegramForbiddenError:
            raise BotNotAdminError(f"Bot is not admin in channel {channel_id}")
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                raise ChannelNotFoundError(f"Channel {channel_id} not found")
            raise ChannelError(f"Error getting channel info: {e}")
    
    async def check_bot_admin(self, channel_id: int) -> Tuple[bool, List[str]]:
        """
        Проверка прав бота в канале.
        
        Args:
            channel_id: ID канала
            
        Returns:
            Tuple (является ли админом, список прав)
        """
        try:
            bot_member = await self.bot.get_chat_member(channel_id, self.bot.id)
            
            if isinstance(bot_member, (ChatMemberOwner, ChatMemberAdministrator)):
                rights = []
                
                if isinstance(bot_member, ChatMemberOwner):
                    return True, ["owner"]
                
                admin = bot_member
                if admin.can_invite_users:
                    rights.append("can_invite_users")
                if admin.can_restrict_members:
                    rights.append("can_restrict_members")
                if admin.can_promote_members:
                    rights.append("can_promote_members")
                if admin.can_manage_chat:
                    rights.append("can_manage_chat")
                if admin.can_delete_messages:
                    rights.append("can_delete_messages")
                if admin.can_post_messages:
                    rights.append("can_post_messages")
                    
                return True, rights
            
            return False, []
            
        except TelegramAPIError as e:
            logger.error(f"Error checking bot admin status: {e}")
            return False, []
    
    # ═══════════════════════════════════════════════════════════════════════
    # INVITE ССЫЛКИ
    # ═══════════════════════════════════════════════════════════════════════
    
    async def create_invite_link(
        self,
        channel_id: int,
        name: Optional[str] = None,
        expire_date: Optional[datetime] = None,
        member_limit: Optional[int] = None,
        creates_join_request: bool = False,
    ) -> InviteLinkInfo:
        """
        Создание invite ссылки.
        
        Args:
            channel_id: ID канала
            name: Название ссылки
            expire_date: Дата истечения
            member_limit: Лимит использований
            creates_join_request: Создавать заявки на вступление
            
        Returns:
            Информация о ссылке
            
        Raises:
            InviteLinkError: Ошибка создания
            BotNotAdminError: Бот не админ
        """
        try:
            link = await self.bot.create_chat_invite_link(
                chat_id=channel_id,
                name=name,
                expire_date=expire_date,
                member_limit=member_limit,
                creates_join_request=creates_join_request,
            )
            
            logger.info(
                f"Created invite link for channel {channel_id}: "
                f"{link.invite_link[:30]}..."
            )
            
            return InviteLinkInfo.from_link(link)
            
        except TelegramForbiddenError:
            raise BotNotAdminError(
                f"Bot cannot create invite links in channel {channel_id}"
            )
        except TelegramBadRequest as e:
            raise InviteLinkError(f"Error creating invite link: {e}")
    
    async def create_single_use_link(
        self,
        channel_id: int,
        user_id: int,
        expire_hours: int = 24,
    ) -> str:
        """
        Создание одноразовой ссылки для пользователя.
        
        Args:
            channel_id: ID канала
            user_id: ID пользователя (для имени ссылки)
            expire_hours: Срок действия в часах
            
        Returns:
            Invite ссылка
        """
        expire_date = datetime.utcnow() + timedelta(hours=expire_hours)
        
        link_info = await self.create_invite_link(
            channel_id=channel_id,
            name=f"user_{user_id}",
            expire_date=expire_date,
            member_limit=1,
        )
        
        return link_info.link
    
    async def create_subscription_link(
        self,
        channel_id: int,
        user_id: int,
        subscription_end: datetime,
    ) -> str:
        """
        Создание ссылки для подписки.
        
        Ссылка действует до конца подписки + 1 день запаса.
        
        Args:
            channel_id: ID канала
            user_id: ID пользователя
            subscription_end: Дата окончания подписки
            
        Returns:
            Invite ссылка
        """
        # Добавляем день запаса
        expire_date = subscription_end + timedelta(days=1)
        
        link_info = await self.create_invite_link(
            channel_id=channel_id,
            name=f"sub_{user_id}",
            expire_date=expire_date,
            member_limit=1,
        )
        
        return link_info.link
    
    async def revoke_invite_link(
        self,
        channel_id: int,
        invite_link: str,
    ) -> bool:
        """
        Отзыв invite ссылки.
        
        Args:
            channel_id: ID канала
            invite_link: Ссылка для отзыва
            
        Returns:
            True если успешно
        """
        try:
            await self.bot.revoke_chat_invite_link(
                chat_id=channel_id,
                invite_link=invite_link,
            )
            logger.info(f"Revoked invite link for channel {channel_id}")
            return True
            
        except TelegramAPIError as e:
            logger.error(f"Error revoking invite link: {e}")
            return False
    
    async def get_invite_link(self, channel_id: int) -> Optional[str]:
        """
        Получение основной invite ссылки канала.
        
        Args:
            channel_id: ID канала
            
        Returns:
            Invite ссылка или None
        """
        try:
            link = await self.bot.export_chat_invite_link(channel_id)
            return link
        except TelegramAPIError as e:
            logger.error(f"Error exporting invite link: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════
    # УПРАВЛЕНИЕ ЧЛЕНСТВОМ
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_member_status(
        self,
        channel_id: int,
        user_id: int,
    ) -> MemberStatus:
        """
        Получение статуса пользователя в канале.
        
        Args:
            channel_id: ID канала
            user_id: ID пользователя
            
        Returns:
            Статус членства
        """
        try:
            member = await self.bot.get_chat_member(channel_id, user_id)
            
            if isinstance(member, ChatMemberOwner):
                return MemberStatus.OWNER
            elif isinstance(member, ChatMemberAdministrator):
                return MemberStatus.ADMIN
            elif isinstance(member, ChatMemberMember):
                return MemberStatus.MEMBER
            elif isinstance(member, ChatMemberRestricted):
                return MemberStatus.RESTRICTED
            elif isinstance(member, ChatMemberLeft):
                return MemberStatus.LEFT
            elif isinstance(member, ChatMemberBanned):
                return MemberStatus.BANNED
            else:
                return MemberStatus.UNKNOWN
                
        except TelegramAPIError as e:
            logger.error(f"Error getting member status: {e}")
            return MemberStatus.UNKNOWN
    
    async def is_member(self, channel_id: int, user_id: int) -> bool:
        """
        Проверка является ли пользователь участником.
        
        Args:
            channel_id: ID канала
            user_id: ID пользователя
            
        Returns:
            True если участник
        """
        status = await self.get_member_status(channel_id, user_id)
        return status in (
            MemberStatus.OWNER,
            MemberStatus.ADMIN,
            MemberStatus.MEMBER,
            MemberStatus.RESTRICTED,
        )
    
    async def kick_member(
        self,
        channel_id: int,
        user_id: int,
        until_date: Optional[datetime] = None,
        revoke_messages: bool = False,
    ) -> bool:
        """
        Кик пользователя из канала.
        
        Args:
            channel_id: ID канала
            user_id: ID пользователя
            until_date: Дата разбана (None = навсегда)
            revoke_messages: Удалить сообщения пользователя
            
        Returns:
            True если успешно
        """
        try:
            await self.bot.ban_chat_member(
                chat_id=channel_id,
                user_id=user_id,
                until_date=until_date,
                revoke_messages=revoke_messages,
            )
            
            # Сразу разбаниваем, чтобы пользователь мог вернуться по ссылке
            if until_date is None:
                await self.bot.unban_chat_member(
                    chat_id=channel_id,
                    user_id=user_id,
                    only_if_banned=True,
                )
            
            logger.info(f"Kicked user {user_id} from channel {channel_id}")
            return True
            
        except TelegramForbiddenError:
            logger.error(
                f"Bot cannot kick user {user_id} from channel {channel_id}: "
                "insufficient permissions"
            )
            return False
        except TelegramBadRequest as e:
            if "user not found" in str(e).lower():
                logger.warning(f"User {user_id} not found in channel {channel_id}")
                return True  # Считаем успехом - пользователя и так нет
            logger.error(f"Error kicking user: {e}")
            return False
        except TelegramAPIError as e:
            logger.error(f"Error kicking user: {e}")
            return False
    
    async def unban_member(self, channel_id: int, user_id: int) -> bool:
        """
        Разбан пользователя.
        
        Args:
            channel_id: ID канала
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        try:
            await self.bot.unban_chat_member(
                chat_id=channel_id,
                user_id=user_id,
                only_if_banned=True,
            )
            logger.info(f"Unbanned user {user_id} in channel {channel_id}")
            return True
            
        except TelegramAPIError as e:
            logger.error(f"Error unbanning user: {e}")
            return False
    
    async def kick_and_unban(self, channel_id: int, user_id: int) -> bool:
        """
        Кик с последующим разбаном (мягкое удаление).
        
        Пользователь удаляется, но может вернуться по ссылке.
        
        Args:
            channel_id: ID канала
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        kicked = await self.kick_member(channel_id, user_id)
        if kicked:
            await self.unban_member(channel_id, user_id)
        return kicked
    
    # ═══════════════════════════════════════════════════════════════════════
    # ПАКЕТНЫЕ ОПЕРАЦИИ
    # ═══════════════════════════════════════════════════════════════════════
    
    async def kick_from_multiple_channels(
        self,
        channel_ids: List[int],
        user_id: int,
    ) -> dict:
        """
        Кик из нескольких каналов.
        
        Args:
            channel_ids: Список ID каналов
            user_id: ID пользователя
            
        Returns:
            Словарь {channel_id: success}
        """
        results = {}
        
        for channel_id in channel_ids:
            results[channel_id] = await self.kick_and_unban(channel_id, user_id)
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(
            f"Kicked user {user_id} from {success_count}/{len(channel_ids)} channels"
        )
        
        return results
    
    async def create_links_for_multiple_channels(
        self,
        channel_ids: List[int],
        user_id: int,
        subscription_end: datetime,
    ) -> dict:
        """
        Создание ссылок для нескольких каналов.
        
        Args:
            channel_ids: Список ID каналов
            user_id: ID пользователя
            subscription_end: Дата окончания подписки
            
        Returns:
            Словарь {channel_id: invite_link или None}
        """
        results = {}
        
        for channel_id in channel_ids:
            try:
                link = await self.create_subscription_link(
                    channel_id=channel_id,
                    user_id=user_id,
                    subscription_end=subscription_end,
                )
                results[channel_id] = link
            except ChannelError as e:
                logger.error(f"Error creating link for channel {channel_id}: {e}")
                results[channel_id] = None
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(
            f"Created links for user {user_id}: "
            f"{success_count}/{len(channel_ids)} channels"
        )
        
        return results
    
    async def check_membership_multiple(
        self,
        channel_ids: List[int],
        user_id: int,
    ) -> dict:
        """
        Проверка членства в нескольких каналах.
        
        Args:
            channel_ids: Список ID каналов
            user_id: ID пользователя
            
        Returns:
            Словарь {channel_id: is_member}
        """
        results = {}
        
        for channel_id in channel_ids:
            results[channel_id] = await self.is_member(channel_id, user_id)
        
        return results
    
    # ═══════════════════════════════════════════════════════════════════════
    # УТИЛИТЫ
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_member_count(self, channel_id: int) -> int:
        """
        Получение количества участников канала.
        
        Args:
            channel_id: ID канала
            
        Returns:
            Количество участников
        """
        try:
            return await self.bot.get_chat_member_count(channel_id)
        except TelegramAPIError as e:
            logger.error(f"Error getting member count: {e}")
            return 0
    
    async def validate_channel(self, channel_id: int) -> Tuple[bool, str]:
        """
        Валидация канала для продажи.
        
        Args:
            channel_id: ID канала
            
        Returns:
            Tuple (valid, message)
        """
        try:
            # Проверяем существование
            info = await self.get_channel_info(channel_id)
            
            # Проверяем права бота
            is_admin, rights = await self.check_bot_admin(channel_id)
            
            if not is_admin:
                return False, "Bot is not an administrator"
            
            if "can_invite_users" not in rights and "owner" not in rights:
                return False, "Bot cannot create invite links"
            
            if info.is_private is False:
                return False, "Channel is public, should be private"
            
            return True, "Channel is valid"
            
        except ChannelNotFoundError:
            return False, "Channel not found"
        except BotNotAdminError:
            return False, "Bot is not in channel or not admin"
        except ChannelError as e:
            return False, str(e)
