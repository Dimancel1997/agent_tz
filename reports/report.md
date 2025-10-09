# Telegram Agent Bot - Технический отчет

## Назначение

Личный помощник для управления задачами и напоминаниями через Telegram с интеграцией внешних сервисов и интеллектуальными возможностями.

## Архитектура системы

### MCP (Model Context Protocol) инструменты

1. **Google Calendar**
   - Создание событий и управление календарем
   - OAuth 2.0 авторизация
   - Поддержка различных форматов дат (DD.MM.YYYY, "сегодня", "завтра")
   - API: Google Calendar API v3

2. **Gmail**
   - Отправка email-уведомлений и напоминаний
   - Автоматическое создание MIME сообщений
   - OAuth 2.0 авторизация
   - API: Gmail API v1

3. **Web Search**
   - Поиск актуальной информации в интернете
   - Использование DuckDuckGo Instant Answer API (бесплатный)
   - Парсинг JSON ответов и возврат snippets
   - Поддержка различных типов запросов

### Система памяти

**SQLite Database**
- Хранение контекста диалогов в формате JSON
- Таблица `conversations` с полями:
  - `user_id` (INTEGER PRIMARY KEY)
  - `session_history` (TEXT JSON)
  - `last_updated` (TIMESTAMP)
- Ограничение: последние 10 сообщений на пользователя
- Автоматическая инициализация при первом запуске

### Векторная база знаний

**FAISS + Sentence Transformers**
- Модель: `all-MiniLM-L6-v2` (384 измерения)
- Семантический поиск по базе знаний
- Хранение фактов о задачах, напоминаниях, календаре, email
- Автоматическая загрузка из `knowledge.json`
- Сохранение индекса на диск для быстрого восстановления

### LLM интеграция

**OpenAI GPT-3.5-turbo**
- Интеллектуальная генерация ответов
- Использование контекста диалога и найденных знаний
- Fallback система при отсутствии API ключа
- Настраиваемые параметры (токены, температура)

## Развертывание

### Docker контейнеризация

**Dockerfile**
- Базовый образ: Python 3.10-slim
- Установка системных зависимостей (curl для healthcheck)
- Копирование requirements.txt для кэширования слоев
- Создание необходимых директорий
- Healthcheck endpoint на порт 8000

**docker-compose.yml**
- Сервис `agent` с build из Dockerfile
- Redis для кэширования
- Volumes для данных, логов, отчетов
- Healthcheck с curl на порт 8000
- Автоматический перезапуск при сбоях
- Логирование в JSON формате

### Ubuntu VPS развертывание

**systemd интеграция**
- Unit файл `agent.service` для автозапуска
- Зависимость от Docker сервиса
- Управление через docker-compose команды
- Логирование в journald
- Restart policy для надежности

**Мониторинг**
- HTTP endpoints: `/health` и `/status`
- Docker healthcheck каждые 30 секунд
- Логи через `journalctl -u agent`
- Docker logs через `docker-compose logs`

## Технические детали

### Зависимости

**Основные библиотеки:**
- `python-telegram-bot==20.7` - Telegram Bot API
- `google-api-python-client==2.108.0` - Google APIs
- `openai==1.3.7` - OpenAI GPT-3.5
- `faiss-cpu==1.7.4` - Векторный поиск
- `sentence-transformers==2.2.2` - Эмбеддинги текста
- `aiohttp==3.9.1` - HTTP сервер для healthcheck
- `pytest==7.4.3` - Тестирование

### Структура проекта

```
├── main.py              # Основное приложение (30.4KB)
├── agent.py             # LLM агент (12.4KB)
├── tools.py             # MCP инструменты (15.9KB)
├── memory.py            # SQLite память (9.1KB)
├── vector_db.py         # FAISS векторная БД (10.7KB)
├── tests.py             # Unit-тесты (10.1KB)
├── knowledge.json       # База знаний (3.9KB)
├── docker-compose.yml   # Docker конфигурация (1.4KB)
├── Dockerfile           # Docker образ (806B)
├── agent.service        # systemd unit (692B)
└── requirements.txt     # Зависимости (646B)
```

### Безопасность

- Все секреты в `.env` файле (не коммитится в Git)
- Google credentials в `credentials.json` (исключен из Git)
- OAuth токены в `token.json` (исключен из Git)
- Healthcheck без аутентификации (только статус)

### Производительность

- Векторный поиск: ~100ms для 10 фактов
- SQLite память: мгновенный доступ
- Docker healthcheck: 30s интервал
- LLM ответы: ~2-5 секунд (зависит от OpenAI API)

## Заключение

Система представляет собой полнофункционального интеллектуального помощника с:
- Интеграцией с внешними сервисами (Google, OpenAI)
- Контекстной памятью и семантическим поиском
- Готовностью к промышленному развертыванию
- Автоматическим мониторингом и восстановлением
- Масштабируемой архитектурой для множества пользователей
