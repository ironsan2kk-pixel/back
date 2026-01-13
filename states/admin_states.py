"""
FSM состояния для административной панели
Чат 5.2 - Telegram бот продажи доступов к каналам

Содержит классы состояний для:
- Промокодов
- Пользователей
- Статистики
- Рассылки
- Настроек
"""

from aiogram.fsm.state import State, StatesGroup


# ==================== ПРОМОКОДЫ ====================

class PromoAdminState(StatesGroup):
    """Состояния для управления промокодами."""
    
    # Создание
    selecting_create_type = State()      # Выбор типа создания (ручной/авто/массовый)
    entering_code = State()              # Ввод кода вручную
    entering_bulk_count = State()        # Ввод количества для массового создания
    entering_bulk_prefix = State()       # Ввод префикса для массового создания
    
    # Настройка скидки
    selecting_discount_type = State()    # Выбор типа скидки
    entering_discount_value = State()    # Ввод значения скидки
    
    # Настройка цели
    selecting_target = State()           # Выбор цели (все/канал/пакет)
    
    # Лимиты и срок действия
    entering_usage_limit = State()       # Ввод лимита использований
    entering_expiry_date = State()       # Ввод даты истечения
    
    # Подтверждение
    confirming_creation = State()        # Подтверждение создания
    confirming_bulk = State()            # Подтверждение массового создания
    
    # Просмотр и редактирование
    viewing_list = State()               # Просмотр списка
    viewing_promo = State()              # Просмотр промокода
    
    # Редактирование
    editing_code = State()               # Редактирование кода
    editing_discount = State()           # Редактирование скидки
    editing_limit = State()              # Редактирование лимита
    editing_expiry = State()             # Редактирование срока
    
    # Удаление
    confirming_delete = State()          # Подтверждение удаления
    
    # Статистика
    viewing_stats = State()              # Просмотр статистики


# ==================== ПОЛЬЗОВАТЕЛИ ====================

class UserAdminState(StatesGroup):
    """Состояния для управления пользователями."""
    
    # Просмотр
    viewing_list = State()               # Просмотр списка пользователей
    viewing_profile = State()            # Просмотр профиля пользователя
    
    # Поиск
    searching = State()                  # Ввод поискового запроса
    viewing_search_results = State()     # Просмотр результатов поиска
    
    # Бан
    confirming_ban = State()             # Подтверждение бана
    confirming_unban = State()           # Подтверждение разбана
    
    # Выдача доступа
    selecting_grant_type = State()       # Выбор типа (канал/пакет)
    selecting_grant_channel = State()    # Выбор канала
    selecting_grant_package = State()    # Выбор пакета
    selecting_grant_duration = State()   # Выбор длительности
    entering_custom_duration = State()   # Ввод кастомной длительности
    confirming_grant = State()           # Подтверждение выдачи
    
    # Подписки пользователя
    viewing_subscriptions = State()      # Просмотр подписок
    viewing_subscription = State()       # Просмотр конкретной подписки
    confirming_revoke = State()          # Подтверждение отзыва подписки
    
    # Платежи пользователя
    viewing_payments = State()           # Просмотр платежей
    
    # Экспорт
    exporting = State()                  # Процесс экспорта


# ==================== СТАТИСТИКА ====================

class StatsAdminState(StatesGroup):
    """Состояния для просмотра статистики."""
    
    # Выбор периода
    selecting_period = State()           # Выбор периода
    
    # Просмотр
    viewing_general = State()            # Общая статистика
    viewing_channel_stats = State()      # Статистика каналов
    viewing_package_stats = State()      # Статистика пакетов
    viewing_finance = State()            # Финансовая статистика
    
    # Экспорт
    selecting_export = State()           # Выбор типа экспорта
    exporting = State()                  # Процесс экспорта


# ==================== РАССЫЛКА ====================

class BroadcastAdminState(StatesGroup):
    """Состояния для рассылки сообщений."""
    
    # Выбор аудитории
    selecting_target = State()           # Выбор целевой аудитории
    selecting_channel = State()          # Выбор канала
    selecting_package = State()          # Выбор пакета
    
    # Создание сообщения
    entering_text = State()              # Ввод текста сообщения
    adding_media = State()               # Добавление медиа
    adding_buttons = State()             # Добавление кнопок (опционально)
    
    # Подтверждение
    confirming = State()                 # Предпросмотр и подтверждение
    
    # Отложенная рассылка
    scheduling = State()                 # Выбор времени
    entering_schedule_time = State()     # Ввод кастомного времени
    
    # Отправка
    sending = State()                    # Процесс отправки
    
    # История
    viewing_history = State()            # Просмотр истории
    viewing_scheduled = State()          # Просмотр отложенных


# ==================== НАСТРОЙКИ ====================

class SettingsAdminState(StatesGroup):
    """Состояния для настроек бота."""
    
    # Общие настройки
    viewing_general = State()            # Просмотр общих настроек
    editing_bot_name = State()           # Редактирование названия
    editing_welcome = State()            # Редактирование приветствия
    editing_support = State()            # Редактирование поддержки
    
    # Настройки оплаты
    viewing_payment = State()            # Просмотр настроек оплаты
    editing_crypto_token = State()       # Редактирование токена
    editing_timeout = State()            # Редактирование таймаута
    editing_min_amount = State()         # Редактирование мин. суммы
    
    # Настройки уведомлений
    viewing_notifications = State()      # Просмотр настроек уведомлений
    editing_notify_days = State()        # Редактирование дней уведомления
    editing_admin_chat = State()         # Редактирование чата админов
    
    # Управление администраторами
    viewing_admins = State()             # Просмотр списка админов
    adding_admin = State()               # Добавление админа
    removing_admin = State()             # Удаление админа
    confirming_admin_action = State()    # Подтверждение действия
    
    # Тексты
    viewing_texts = State()              # Просмотр текстов
    selecting_text = State()             # Выбор текста для редактирования
    editing_text = State()               # Редактирование текста
    
    # Резервное копирование
    viewing_backup = State()             # Меню бэкапа
    restoring_backup = State()           # Восстановление
    confirming_restore = State()         # Подтверждение восстановления


# ==================== КАНАЛЫ (дополнительно) ====================

class ChannelAdminState(StatesGroup):
    """Состояния для управления каналами."""

    # Просмотр
    viewing_list = State()               # Список каналов
    viewing_channel = State()            # Просмотр канала

    # Создание
    entering_channel_id = State()        # Ввод ID канала
    entering_channel_name = State()      # Ввод названия
    entering_channel_description = State()  # Ввод описания
    entering_prices = State()            # Ввод цен
    entering_price_30 = State()          # Цена за 30 дней
    entering_price_90 = State()          # Цена за 90 дней
    entering_price_365 = State()         # Цена за 365 дней
    confirming_creation = State()        # Подтверждение создания

    # Редактирование
    editing_name = State()               # Редактирование названия
    editing_description = State()        # Редактирование описания
    editing_prices = State()             # Редактирование цен

    # Удаление
    confirming_delete = State()          # Подтверждение удаления


class ChannelAddState(StatesGroup):
    """Состояния добавления канала (пошаговый визард)."""
    waiting_channel_id = State()         # Ожидание ID/username канала
    waiting_name_ru = State()            # Ввод названия RU
    waiting_name_en = State()            # Ввод названия EN
    waiting_description_ru = State()     # Ввод описания RU
    waiting_description_en = State()     # Ввод описания EN
    waiting_image = State()              # Загрузка изображения
    confirm = State()                    # Подтверждение


class ChannelEditState(StatesGroup):
    """Состояния редактирования канала."""
    waiting_new_value = State()          # Ожидание нового значения поля
    waiting_image = State()              # Ожидание нового изображения
    confirm_delete = State()             # Подтверждение удаления


class ChannelOrderState(StatesGroup):
    """Состояния изменения порядка каналов."""
    selecting_channel = State()          # Выбор канала
    selecting_position = State()         # Выбор позиции


class TrialSettingsState(StatesGroup):
    """Состояния настройки пробного периода."""
    waiting_days = State()               # Ввод количества дней


# ==================== ПАКЕТЫ (дополнительно) ====================

class PackageAdminState(StatesGroup):
    """Состояния для управления пакетами."""
    
    # Просмотр
    viewing_list = State()               # Список пакетов
    viewing_package = State()            # Просмотр пакета
    
    # Создание
    entering_name = State()              # Ввод названия
    entering_description = State()       # Ввод описания
    selecting_channels = State()         # Выбор каналов
    entering_prices = State()            # Ввод цен
    entering_price_30 = State()          # Цена за 30 дней
    entering_price_90 = State()          # Цена за 90 дней
    entering_price_365 = State()         # Цена за 365 дней
    confirming_creation = State()        # Подтверждение создания
    
    # Редактирование
    editing_name = State()               # Редактирование названия
    editing_description = State()        # Редактирование описания
    editing_channels = State()           # Редактирование каналов
    editing_prices = State()             # Редактирование цен
    
    # Удаление
    confirming_delete = State()          # Подтверждение удаления


# ==================== МЕНЮ КОНСТРУКТОР ====================

class MenuConstructorState(StatesGroup):
    """Состояния для конструктора меню."""
    
    # Просмотр
    viewing_menu = State()               # Просмотр структуры меню
    viewing_item = State()               # Просмотр элемента
    
    # Создание элемента
    selecting_type = State()             # Выбор типа элемента
    entering_text = State()              # Ввод текста кнопки
    entering_callback = State()          # Ввод callback_data
    entering_url = State()               # Ввод URL
    selecting_position = State()         # Выбор позиции
    
    # Редактирование
    editing_text = State()               # Редактирование текста
    editing_callback = State()           # Редактирование callback
    editing_position = State()           # Редактирование позиции
    
    # Удаление
    confirming_delete = State()          # Подтверждение удаления
    
    # Предпросмотр
    previewing = State()                 # Предпросмотр меню
