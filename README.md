# Telegram Agent Bot

Интеллектуальный личный помощник для Telegram с управлением задачами, напоминаниями и интеграцией с внешними сервисами.

## 🚀 Возможности

- 🤖 **Telegram Bot API** - полнофункциональный бот с командами и диалогами
- 📅 **Google Calendar** - создание событий и управление календарем
- 📧 **Gmail** - отправка email-уведомлений и напоминаний
- 🔍 **Web Search** - поиск актуальной информации через DuckDuckGo
- 🧠 **LLM Integration** - OpenAI GPT-3.5 для интеллектуальных ответов
- 💾 **SQLite Memory** - контекстная память диалогов (JSON per user)
- 🔍 **Vector Database** - FAISS с sentence-transformers для семантического поиска
- 🐳 **Docker Deployment** - контейнеризация для Ubuntu VPS
- 🔄 **Auto-restart** - systemd интеграция для автозапуска

## 📦 Установка

### Быстрый старт

1. **Клонируйте репозиторий:**
   ```bash
   git clone <repository-url>
   cd telegram-agent
   ```

2. **Скопируйте файл конфигурации:**
   ```bash
   cp .env.example .env
   ```

3. **Отредактируйте `.env` файл, добавив ваши API ключи:**
   - `TELEGRAM_TOKEN` - токен вашего Telegram бота
   - `GOOGLE_API_KEY` - ключ Google API
   - `OPENAI_API_KEY` - ключ OpenAI API
   - И другие необходимые переменные

4. **Запустите приложение:**
   ```bash
   docker-compose up -d
   ```

## 💬 Примеры использования

### Команды MCP

**Создание события в календаре:**
```bash
/calendar "добавить событие завтра встреча с клиентом"
/calendar "добавить событие 15.12.2024 презентация проекта"
```

**Отправка email-уведомления:**
```bash
/email "отправить reminder@example.com: встреча завтра в 10:00"
/email "отправить boss@company.com: отчет готов"
```

**Поиск информации:**
```bash
/search "погода в Москве"
/search "курс доллара"
/search "новости технологий"
```

### Интеллектуальные диалоги

**Пример 1: Напоминание о встрече**
```
Пользователь: Напомни о встрече с клиентом завтра
Бот: Я могу помочь с напоминанием! Используй команду:
     /calendar "добавить событие завтра встреча с клиентом"
     
     Или отправлю email-напоминание:
     /email "отправить your-email@example.com: встреча с клиентом завтра"
```

**Пример 2: Поиск информации**
```
Пользователь: Какая погода в Санкт-Петербурге?
Бот: Сейчас найду актуальную информацию о погоде в Санкт-Петербурге...
     /search "погода в Санкт-Петербурге"
```

**Пример 3: Организация дня**
```
Пользователь: Помоги организовать день
Бот: Я могу помочь организовать ваш день! Вот что я умею:
     📅 Создавать события в календаре
     📧 Отправлять напоминания на email
     🔍 Искать информацию в интернете
     💾 Запоминать наши разговоры для лучшего понимания
```

## 🔧 Настройка MCP инструментов

### Google Calendar & Gmail Setup

1. **Создайте проект в Google Cloud Console:**
   - Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
   - Создайте новый проект или выберите существующий

2. **Включите API:**
   - Google Calendar API
   - Gmail API

3. **Создайте OAuth 2.0 credentials:**
   - Перейдите в "Credentials"
   - Создайте "OAuth 2.0 Client IDs"
   - Выберите "Desktop application"
   - Скачайте файл `credentials.json`
   - Поместите в корень проекта

4. **Настройте scopes:**
   ```bash
   https://www.googleapis.com/auth/calendar
   https://www.googleapis.com/auth/gmail.send
   ```

5. **Авторизация:**
   - При первом запуске откроется браузер
   - Войдите в Google аккаунт
   - Разрешите доступ приложению
   - Токен сохранится в `token.json`

### OpenAI API Setup

1. **Получите API ключ:**
   - Перейдите в [OpenAI Platform](https://platform.openai.com/)
   - Создайте API ключ
   - Добавьте в `.env`: `OPENAI_API_KEY=your_key_here`

### Telegram Bot Setup

1. **Создайте бота:**
   - Напишите [@BotFather](https://t.me/botfather) в Telegram
   - Используйте команду `/newbot`
   - Получите токен бота
   - Добавьте в `.env`: `TELEGRAM_TOKEN=your_token_here`

## 🚀 Развертывание на Ubuntu 22.04 VPS

### Быстрый старт

```bash
# Подключитесь к VPS
ssh user@your-vps-ip

# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите Docker и Docker Compose
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# Клонируйте репозиторий
git clone <repository-url>
cd telegram-agent

# Настройте переменные окружения
cp .env.example .env
nano .env  # Заполните ваши секреты

# Запустите сервис
docker-compose up -d
```

### Автозапуск с systemd

```bash
# Скопируйте systemd unit файл
sudo cp agent.service /etc/systemd/system/

# Включите автозапуск
sudo systemctl enable agent

# Запустите сервис
sudo systemctl start agent

# Проверьте статус
sudo systemctl status agent
```

### Мониторинг и логи

```bash
# Проверка логов systemd
journalctl -u agent -f

# Проверка логов Docker
docker-compose logs -f

# Проверка статуса контейнеров
docker-compose ps

# Проверка health check
curl http://localhost:8000/health
curl http://localhost:8000/status
```

### Тестирование перезапуска

```bash
# Перезагрузите сервер
sudo reboot

# После перезагрузки подключитесь и проверьте логи
ssh user@your-vps-ip
journalctl -u agent -f
```

### Управление сервисом

```bash
# Остановить сервис
sudo systemctl stop agent

# Перезапустить сервис
sudo systemctl restart agent

# Отключить автозапуск
sudo systemctl disable agent

# Обновить код
git pull
docker-compose down
docker-compose up -d --build
```

## 📁 Структура проекта

```
├── main.py              # Основной файл приложения
├── agent.py             # LLM агент с OpenAI
├── tools.py             # MCP инструменты (Calendar, Gmail, Search)
├── memory.py            # SQLite память диалогов
├── vector_db.py         # FAISS векторная база знаний
├── knowledge.json       # База знаний
├── tests.py             # Unit-тесты
├── docker-compose.yml   # Docker конфигурация
├── Dockerfile          # Docker образ
├── agent.service       # systemd unit файл
├── .env.example        # Пример переменных окружения
├── requirements.txt    # Python зависимости
├── .gitignore          # Git исключения
├── .github/
│   └── workflows/
│       └── ci.yml      # CI/CD pipeline
├── reports/            # Папка для отчётов
├── conversations/      # Папка для логов
└── README.md          # Этот файл
```

## 📋 Требования

- **Python 3.10+** - основная версия языка
- **Docker и Docker Compose** - для контейнеризации
- **Ubuntu 22.04** - для развертывания на VPS

## 🛠️ MCP Инструменты

Проект использует следующие MCP (Model Context Protocol) инструменты:

### 📅 Google Calendar
- **API**: Google Calendar API v3
- **Функции**: Создание событий, управление календарем
- **Команда**: `/calendar "добавить событие 10.10.2025 встреча"`
- **Поддерживаемые форматы дат**: DD.MM.YYYY, "сегодня", "завтра"
- **Scopes**: `https://www.googleapis.com/auth/calendar`

### 📧 Gmail
- **API**: Gmail API v1
- **Функции**: Отправка email-уведомлений
- **Команда**: `/email "отправить email@example.com: тема письма"`
- **Scopes**: `https://www.googleapis.com/auth/gmail.send`

### 🔍 Web Search
- **API**: DuckDuckGo Instant Answer API (бесплатный)
- **Функции**: Поиск информации в интернете
- **Команда**: `/search "погода в Москве"`
- **Возвращает**: Snippets с результатами поиска

### 🧠 LLM Integration
- **Модель**: OpenAI GPT-3.5-turbo
- **Функции**: Генерация интеллектуальных ответов
- **Контекст**: Использует историю диалога и найденные знания
- **Fallback**: Работает без API ключа с базовыми ответами

### 💾 SQLite Memory
- **Технология**: SQLite база данных
- **Структура**: Таблица `conversations` с JSON полем `session_history`
- **Функции**: Сохранение и загрузка контекста диалогов
- **Ограничения**: Последние 10 сообщений на пользователя

### 🧠 Vector Database
- **Технология**: FAISS + Sentence Transformers
- **Модель**: all-MiniLM-L6-v2
- **Функции**: Семантический поиск в базе знаний
- **Интеграция**: Автоматический поиск для каждого сообщения

## 💾 База данных

- **SQLite** - для хранения памяти и контекста диалогов
- **FAISS** - для векторного поиска и семантического анализа

## ⚙️ Настройка Google API

### 1. Создание проекта в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите следующие API:
   - Google Calendar API
   - Gmail API

### 2. Создание OAuth 2.0 credentials

1. Перейдите в раздел "Credentials"
2. Нажмите "Create Credentials" → "OAuth 2.0 Client IDs"
3. Выберите "Desktop application"
4. Скачайте файл `credentials.json`
5. Поместите файл в корень проекта

### 3. Первая авторизация

1. Запустите приложение: `python main.py`
2. Откроется браузер для авторизации
3. Войдите в Google аккаунт
4. Разрешите доступ приложению
5. Токен сохранится в `token.json`

## 🔧 Разработка

Для разработки локально:

```bash
# Установите зависимости
pip install -r requirements.txt

# Настройте Google API (см. раздел выше)
# Поместите credentials.json в корень проекта

# Запустите приложение
python main.py
```

## 🧪 Тестирование

Запуск unit-тестов:

```bash
# Установите pytest
pip install pytest pytest-asyncio

# Запустите тесты
python -m pytest tests.py -v
```

## 📄 Лицензия

MIT License