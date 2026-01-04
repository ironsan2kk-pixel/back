# 🔗 Руководство по интеграции

## Сборка проекта из всех чатов

Этот документ описывает, как собрать полный проект из архивов всех чатов.

---

## 📦 Список архивов

| Чат | Архив | Содержимое |
|:---:|-------|------------|
| 2 | `chat2_core.zip` | Ядро: config, database, models, crud, i18n |
| 3 | `chat3_userbot.zip` | Пользовательские handlers, keyboards, states |
| 4 | `chat4_services.zip` | Services, middlewares, Crypto Bot API |
| 5.1 | `chat5_admin_part1.zip` | Админка: каналы, пакеты, тарифы |
| 5.2 | `chat5_2_admin_part2.zip` | Админка: промокоды, пользователи, статистика |
| 6 | `chat6_tui_admin.zip` | TUI админка для терминала |
| 7 | `chat7_deploy.zip` | Запуск: bot.py, BAT-файлы, планировщик |

---

## 🛠️ Порядок сборки

### 1. Создайте структуру папок

```
C:\ChannelAccessBot\
├── bat\
├── data\
├── logs\
├── backups\
├── tools\
├── database\
├── handlers\
│   ├── user\
│   └── admin\
├── keyboards\
├── states\
├── services\
├── middlewares\
├── scheduler\
├── tui\
├── utils\
└── locales\
```

### 2. Распакуйте архивы в следующем порядке:

#### Шаг 1: Chat 7 (база)
```cmd
:: Распаковать chat7_deploy.zip в C:\ChannelAccessBot\
```

Содержит:
- `bot.py`
- `config.py`
- `run_admin.py`
- `requirements.txt`
- `.env.example`
- `README.md`
- BAT-файлы
- `scheduler/`
- `utils/`

#### Шаг 2: Chat 2 (ядро)
```cmd
:: Распаковать chat2_core.zip
:: Скопировать в:
::   database/ → C:\ChannelAccessBot\database\
::   locales/ → C:\ChannelAccessBot\locales\
```

Содержит:
- `database/database.py`
- `database/models.py`
- `database/crud.py`
- `locales/ru.json`
- `locales/en.json`
- `utils/i18n.py`

#### Шаг 3: Chat 3 (пользовательский бот)
```cmd
:: Распаковать chat3_userbot.zip
:: Скопировать в:
::   handlers/user/ → C:\ChannelAccessBot\handlers\user\
::   keyboards/ → C:\ChannelAccessBot\keyboards\
::   states/ → C:\ChannelAccessBot\states\
```

Содержит:
- `handlers/user/*.py`
- `keyboards/user_kb.py`
- `states/user_states.py`

#### Шаг 4: Chat 4 (сервисы)
```cmd
:: Распаковать chat4_services.zip
:: Скопировать в:
::   services/ → C:\ChannelAccessBot\services\
::   middlewares/ → C:\ChannelAccessBot\middlewares\
```

Содержит:
- `services/crypto_bot.py`
- `services/channel_manager.py`
- `services/subscription_manager.py`
- `services/payment_processor.py`
- `middlewares/i18n.py`
- `middlewares/database.py`
- `middlewares/throttling.py`
- `middlewares/logging.py`

#### Шаг 5: Chat 5.1 (админка часть 1)
```cmd
:: Распаковать chat5_admin_part1.zip
:: Скопировать в:
::   handlers/admin/ → C:\ChannelAccessBot\handlers\admin\
```

Содержит:
- `handlers/admin/main.py`
- `handlers/admin/channels.py`
- `handlers/admin/packages.py`
- `handlers/admin/pricing.py`
- `keyboards/admin_kb.py` (частично)
- `states/admin_states.py` (частично)

#### Шаг 6: Chat 5.2 (админка часть 2)
```cmd
:: Распаковать chat5_2_admin_part2.zip
:: Скопировать в:
::   handlers/admin/ → C:\ChannelAccessBot\handlers\admin\
```

Содержит:
- `handlers/admin/promos.py`
- `handlers/admin/users.py`
- `handlers/admin/stats.py`
- `handlers/admin/broadcast.py`
- `handlers/admin/settings.py`
- `keyboards/admin_kb.py` (дополнение)
- `states/admin_states.py` (дополнение)

#### Шаг 7: Chat 6 (TUI)
```cmd
:: Распаковать chat6_tui_admin.zip
:: Скопировать в:
::   tui/ → C:\ChannelAccessBot\tui\
```

Содержит:
- `tui/app.py`
- `tui/components/`
- `tui/widgets/`
- `tui/styles/`

---

## ✅ Проверка сборки

После сборки структура должна выглядеть так:

```
C:\ChannelAccessBot\
│
├── bot.py                     ✓ (Chat 7)
├── config.py                  ✓ (Chat 7)
├── run_admin.py               ✓ (Chat 7)
├── requirements.txt           ✓ (Chat 7)
├── .env.example               ✓ (Chat 7)
├── .env                       ← Создайте вручную
│
├── bat\
│   ├── install.bat            ✓ (Chat 7)
│   ├── start_bot.bat          ✓ (Chat 7)
│   └── ...
│
├── database\
│   ├── __init__.py            ✓ (Chat 7)
│   ├── database.py            ✓ (Chat 2)
│   ├── models.py              ✓ (Chat 2)
│   └── crud.py                ✓ (Chat 2)
│
├── handlers\
│   ├── __init__.py            ✓ (Chat 7)
│   ├── user\
│   │   ├── __init__.py        ✓ (Chat 7)
│   │   ├── start.py           ✓ (Chat 3)
│   │   ├── menu.py            ✓ (Chat 3)
│   │   └── ...
│   └── admin\
│       ├── __init__.py        ✓ (Chat 7)
│       ├── main.py            ✓ (Chat 5.1)
│       ├── channels.py        ✓ (Chat 5.1)
│       ├── promos.py          ✓ (Chat 5.2)
│       └── ...
│
├── services\
│   ├── __init__.py            ✓ (Chat 7)
│   ├── crypto_bot.py          ✓ (Chat 4)
│   └── ...
│
├── middlewares\
│   ├── __init__.py            ✓ (Chat 7)
│   ├── i18n.py                ✓ (Chat 4)
│   └── ...
│
├── scheduler\
│   ├── __init__.py            ✓ (Chat 7)
│   └── tasks.py               ✓ (Chat 7)
│
├── tui\
│   ├── __init__.py            ✓ (Chat 7)
│   └── app.py                 ✓ (Chat 6)
│
├── keyboards\
│   ├── __init__.py            ✓ (Chat 7)
│   ├── user_kb.py             ✓ (Chat 3)
│   └── admin_kb.py            ✓ (Chat 5.1 + 5.2)
│
├── states\
│   ├── __init__.py            ✓ (Chat 7)
│   ├── user_states.py         ✓ (Chat 3)
│   └── admin_states.py        ✓ (Chat 5.1 + 5.2)
│
├── utils\
│   ├── __init__.py            ✓ (Chat 7)
│   ├── helpers.py             ✓ (Chat 7)
│   └── i18n.py                ✓ (Chat 2)
│
└── locales\
    ├── ru.json                ✓ (Chat 2)
    └── en.json                ✓ (Chat 2)
```

---

## 🚀 Запуск

1. Скопируйте `.env.example` в `.env`
2. Заполните токены в `.env`
3. Запустите `bat\install.bat`
4. Запустите `bat\start_bot.bat`

---

## ⚠️ Важные замечания

1. **Объединение файлов**: Файлы `admin_kb.py` и `admin_states.py` из Chat 5.1 и 5.2 нужно объединить вручную (добавить содержимое 5.2 к 5.1)

2. **Проверка импортов**: После сборки убедитесь, что все импорты работают корректно

3. **Порядок важен**: Распаковывайте архивы в указанном порядке, чтобы более новые файлы перезаписывали старые `__init__.py`

---

## 📞 Поддержка

Если возникли проблемы со сборкой, проверьте:
1. Все ли архивы распакованы
2. Правильная ли структура папок
3. Заполнен ли файл `.env`
4. Установлены ли зависимости (`bat\install.bat`)
