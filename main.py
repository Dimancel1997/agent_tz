#!/usr/bin/env python3
"""
Telegram Agent Bot - Intelligent Personal Assistant
Main application entry point with Telegram Bot implementation
"""

import os
import sys
import logging
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ConversationHandler,
    ContextTypes
)
from dotenv import load_dotenv

# For health endpoint
try:
    from aiohttp import web
    import aiohttp
except ImportError:
    aiohttp = None

# Import memory functions
from memory import save_message, get_context, get_memory_stats

# Import vector database functions
from vector_db import (
    search_knowledge, 
    load_knowledge_from_json, 
    get_vector_db_stats,
    save_vector_db
)

# Import OpenAI
import openai

# Import MCP tools
from tools import (
    create_calendar_event,
    send_email_notification, 
    search_web,
    check_all_mcp_health
)

# Import LLM agent
from agent import generate_response, get_llm_stats

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_MESSAGE = 1

class TelegramAgentBot:
    """Main Telegram Bot class for the intelligent personal assistant"""
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN not found in environment variables")
        
        self.application = Application.builder().token(self.token).build()
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        
        # Initialize OpenAI
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        # Initialize MCP status (placeholders)
        self.mcp_status = {
            'calendar': 'OK',
            'gmail': 'OK', 
            'search': 'OK',
            'vector_db': 'OK'
        }
        
        # Initialize vector database
        self._initialize_vector_db()

        # Initialize health endpoint
        self._setup_health_endpoint()

        self._setup_handlers()
    
    def _initialize_vector_db(self):
        """Initialize vector database with sample knowledge"""
        try:
            # Load knowledge from JSON file
            success = load_knowledge_from_json("knowledge.json")
            if success:
                logger.info("Vector database initialized with sample knowledge")
                self.mcp_status['vector_db'] = 'OK'
            else:
                logger.warning("Failed to load sample knowledge")
                self.mcp_status['vector_db'] = 'WARNING'
        except Exception as e:
            logger.error(f"Error initializing vector database: {e}")
            self.mcp_status['vector_db'] = 'ERROR'
    
    def _setup_health_endpoint(self):
        """Setup HTTP health endpoint for Docker healthcheck"""
        if aiohttp is None:
            logger.warning("aiohttp not available, health endpoint disabled")
            return
        
        try:
            self.app = web.Application()
            self.app.router.add_get('/health', self._health_endpoint)
            self.app.router.add_get('/status', self._status_endpoint)
            
            # Start HTTP server in background
            asyncio.create_task(self._start_http_server())
            logger.info("Health endpoint initialized on port 8000")
            
        except Exception as e:
            logger.error(f"Error setting up health endpoint: {e}")
    
    async def _start_http_server(self):
        """Start HTTP server for health checks"""
        try:
            runner = web.AppRunner(self.app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', 8000)
            await site.start()
            logger.info("HTTP server started on port 8000")
        except Exception as e:
            logger.error(f"Error starting HTTP server: {e}")
    
    async def _health_endpoint(self, request):
        """Health check endpoint for Docker"""
        try:
            # Basic health check
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "telegram-agent-bot",
                "version": "1.0.0"
            }
            
            return web.json_response(health_data)
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return web.json_response(
                {"status": "unhealthy", "error": str(e)}, 
                status=500
            )
    
    async def _status_endpoint(self, request):
        """Detailed status endpoint"""
        try:
            # Get system status
            memory_stats = get_memory_stats()
            vector_stats = get_vector_db_stats()
            llm_stats = get_llm_stats()
            
            status_data = {
                "status": "running",
                "timestamp": datetime.now().isoformat(),
                "service": "telegram-agent-bot",
                "version": "1.0.0",
                "components": {
                    "memory": {
                        "total_users": memory_stats.get('total_users', 0),
                        "total_messages": memory_stats.get('total_messages', 0)
                    },
                    "vector_db": {
                        "total_items": vector_stats.get('total_items', 0),
                        "model": vector_stats.get('model_name', 'N/A')
                    },
                    "llm": {
                        "enabled": llm_stats.get('enabled', False),
                        "model": llm_stats.get('model', 'N/A')
                    },
                    "mcp_tools": self.mcp_status
                }
            }
            
            return web.json_response(status_data)
            
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return web.json_response(
                {"status": "error", "error": str(e)}, 
                status=500
            )
    
    def _setup_handlers(self):
        """Setup all bot handlers"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("health", self.health_command))
        
        # MCP command handlers
        self.application.add_handler(CommandHandler("calendar", self.calendar_command))
        self.application.add_handler(CommandHandler("email", self.email_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        
        # Conversation handler for contextual sessions
        conversation_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)],
            states={
                WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)],
            per_user=True,
            per_chat=True
        )
        
        self.application.add_handler(conversation_handler)
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "пользователь"
        
        # Initialize user session
        self.user_sessions[user_id] = {
            'context': [],
            'last_interaction': update.message.date,
            'message_count': 0
        }
        
        welcome_message = (
            f"Привет, {username}! Я твой личный помощник для задач и напоминаний.\n\n"
            "Я могу помочь тебе с:\n"
            "• Управлением календарем через Google Calendar\n"
            "• Отправкой email-уведомлений через Gmail\n"
            "• Поиском информации в интернете\n"
            "• Запоминанием контекста наших разговоров\n\n"
            "Используй /help для списка команд или просто напиши мне что-нибудь!"
        )
        
        await update.message.reply_text(welcome_message)
        logger.info(f"User {user_id} ({username}) started the bot")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "Доступные команды:\n\n"
            "📅 /calendar \"добавить событие дата название\"\n"
            "📧 /email \"отправить email@example.com: тема\"\n"
            "🔍 /search \"запрос для поиска\"\n"
            "💚 /health - Проверка статуса агента\n"
            "❓ /help - Показать это сообщение\n\n"
            "Примеры:\n"
            "• /calendar \"добавить событие 10.10.2025 встреча\"\n"
            "• /email \"отправить reminder@example.com: встреча завтра\"\n"
            "• /search \"погода в Москве\"\n\n"
            "Также можешь просто писать мне сообщения - я запоминаю контекст наших разговоров!\n"
            "+ Поиск в знаниях: спроси о задачах/напоминаниях.\n"
            "+ LLM: использую OpenAI GPT-3.5 для умных ответов."
        )
        
        await update.message.reply_text(help_message)
        logger.info(f"User {update.effective_user.id} requested help")
    
    async def health_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /health command"""
        # Get memory statistics
        memory_stats = get_memory_stats()
        test_user_id = 12345  # Test user for demonstration
        
        # Get vector database statistics
        vector_stats = get_vector_db_stats()
        
        # Get LLM agent statistics
        llm_stats = get_llm_stats()
        
        # Check MCP tools health
        mcp_health = await check_all_mcp_health()
        
        # Format MCP status
        calendar_status = mcp_health['calendar']['status']
        gmail_status = mcp_health['gmail']['status']
        search_status = mcp_health['search']['status']
        
        health_message = (
            f"Агент онлайн!\n\n"
            f"MCP Calendar: {calendar_status}\n"
            f"MCP Gmail: {gmail_status}\n"
            f"MCP Search: {search_status}\n"
            f"MCP Vector DB: {self.mcp_status['vector_db']}\n"
            f"LLM Agent: {'✅' if llm_stats['enabled'] else '❌'} {llm_stats['model']}\n\n"
            f"Память: {len(get_context(test_user_id))} сообщений (тест)\n"
            f"Всего пользователей: {memory_stats.get('total_users', 0)}\n"
            f"Всего сообщений: {memory_stats.get('total_messages', 0)}\n"
            f"База знаний: {vector_stats.get('total_items', 0)} фактов\n"
            f"База данных: SQLite + FAISS готовы"
        )
        
        # Add detailed MCP info if available
        if calendar_status == 'healthy':
            health_message += f"\n📅 Календарей: {mcp_health['calendar'].get('calendars_count', 0)}"
        if gmail_status == 'healthy':
            health_message += f"\n📧 Email: {mcp_health['gmail'].get('email', 'N/A')}"
        if search_status == 'healthy':
            health_message += f"\n🔍 Поиск: {mcp_health['search'].get('test_results', 0)} результатов"
        
        await update.message.reply_text(health_message)
        logger.info(f"Health check requested by user {update.effective_user.id}")
    
    async def calendar_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /calendar command"""
        try:
            # Get command arguments
            args = context.args
            if not args:
                await update.message.reply_text(
                    "Использование: /calendar \"добавить событие 10.10.2025 meeting\"\n"
                    "Примеры дат: 10.10.2025, завтра, сегодня"
                )
                return
            
            # Parse command
            command_text = " ".join(args)
            
            # Extract event details
            if "добавить событие" in command_text.lower():
                # Parse: "добавить событие DATE SUMMARY"
                parts = command_text.split()
                if len(parts) < 4:
                    await update.message.reply_text("Формат: /calendar \"добавить событие дата название\"")
                    return
                
                date_str = parts[2]  # Date
                summary = " ".join(parts[3:])  # Event title
                
                # Create event
                result = await create_calendar_event(summary, date_str)
                
                if result['success']:
                    response = (
                        f"✅ Событие создано!\n\n"
                        f"📅 Название: {result['summary']}\n"
                        f"📆 Дата: {result['date']}\n"
                        f"🔗 Ссылка: {result.get('link', 'Недоступна')}"
                    )
                else:
                    response = f"❌ Ошибка MCP: {result['error']}"
                
                await update.message.reply_text(response)
                logger.info(f"Calendar command executed by user {update.effective_user.id}")
                
            else:
                await update.message.reply_text(
                    "Поддерживаемые команды:\n"
                    "• добавить событие [дата] [название]"
                )
                
        except Exception as e:
            logger.error(f"Calendar command error: {e}")
            await update.message.reply_text(f"❌ Ошибка MCP: {str(e)}")
    
    async def email_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /email command"""
        try:
            # Get command arguments
            args = context.args
            if not args:
                await update.message.reply_text(
                    "Использование: /email \"отправить email@example.com: тема письма\"\n"
                    "Пример: /email \"отправить reminder@example.com: встреча завтра\""
                )
                return
            
            # Parse command
            command_text = " ".join(args)
            
            if "отправить" in command_text.lower():
                # Parse: "отправить EMAIL: SUBJECT"
                if ":" not in command_text:
                    await update.message.reply_text("Формат: /email \"отправить email@example.com: тема письма\"")
                    return
                
                parts = command_text.split(":", 1)
                if len(parts) != 2:
                    await update.message.reply_text("Формат: /email \"отправить email@example.com: тема письма\"")
                    return
                
                email_part = parts[0].replace("отправить", "").strip()
                subject = parts[1].strip()
                
                # Extract email address
                import re
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', email_part)
                if not email_match:
                    await update.message.reply_text("Неверный формат email адреса")
                    return
                
                to_email = email_match.group()
                
                # Create email body
                body = f"Это автоматическое уведомление от Telegram Agent Bot.\n\n{subject}\n\nОтправлено: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                
                # Send email
                result = await send_email_notification(to_email, subject, body)
                
                if result['success']:
                    response = (
                        f"✅ Email отправлен!\n\n"
                        f"📧 Получатель: {result['to']}\n"
                        f"📝 Тема: {result['subject']}\n"
                        f"⏰ Время: {result['timestamp']}"
                    )
                else:
                    response = f"❌ Ошибка MCP: {result['error']}"
                
                await update.message.reply_text(response)
                logger.info(f"Email command executed by user {update.effective_user.id}")
                
            else:
                await update.message.reply_text(
                    "Поддерживаемые команды:\n"
                    "• отправить [email]: [тема]"
                )
                
        except Exception as e:
            logger.error(f"Email command error: {e}")
            await update.message.reply_text(f"❌ Ошибка MCP: {str(e)}")
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        try:
            # Get command arguments
            args = context.args
            if not args:
                await update.message.reply_text(
                    "Использование: /search \"погода в Москве\"\n"
                    "Пример: /search \"курс доллара\""
                )
                return
            
            # Parse query
            query = " ".join(args)
            
            # Perform search
            result = await search_web(query, max_results=3)
            
            if result['success']:
                response = f"🔍 Результаты поиска для \"{query}\":\n\n"
                
                for i, search_result in enumerate(result['results'], 1):
                    response += f"{i}. **{search_result['title']}**\n"
                    response += f"   {search_result['snippet'][:200]}...\n"
                    if search_result.get('url'):
                        response += f"   🔗 {search_result['url']}\n"
                    response += "\n"
                
                # Limit response length
                if len(response) > 4000:
                    response = response[:4000] + "\n\n... (результаты обрезаны)"
                
            else:
                response = f"❌ Ошибка MCP: {result['error']}"
            
            await update.message.reply_text(response)
            logger.info(f"Search command executed by user {update.effective_user.id}")
            
        except Exception as e:
            logger.error(f"Search command error: {e}")
            await update.message.reply_text(f"❌ Ошибка MCP: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages with context awareness"""
        user_id = update.effective_user.id
        message_text = update.message.text
        username = update.effective_user.username or "пользователь"
        
        # Load conversation context from database
        conversation_context = get_context(user_id)
        
        # Generate contextual response based on history
        response = await self._generate_response(user_id, message_text, conversation_context)
        
        # Save the conversation to database
        save_message(user_id, message_text, response)
        
        await update.message.reply_text(response)
        logger.info(f"User {user_id} ({username}) sent message: {message_text[:50]}...")
    
    async def _generate_response(self, user_id: int, message: str, conversation_context: List[Dict[str, Any]]) -> str:
        """Generate contextual response using LLM agent with knowledge and context"""

        try:
            # Search in vector database for relevant knowledge
            search_results = search_knowledge(message, top_k=3)
            
            # Extract knowledge snippets
            knowledge = []
            if search_results:
                for text, score, metadata in search_results:
                    knowledge.append(text)
            
            # Generate response using LLM agent
            response = await generate_response(conversation_context, message, knowledge)
            
            logger.info(f"Generated LLM response for user {user_id}")
            return response

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            
            # Fallback to simple response
            message_count = len([msg for msg in conversation_context if msg['role'] == 'user'])
            context_info = f"Это сообщение #{message_count + 1} в нашей беседе."

            return (
                f"Понял! {context_info}\n\n"
                "Я помню наш разговор и готов помочь. "
                "Можешь спросить про календарь, email, поиск или просто поболтать!"
            )
    
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command"""
        await update.message.reply_text("Операция отменена. Чем еще могу помочь?")
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка. Попробуйте еще раз или используйте /help."
            )
    
    def run(self):
        """Run the bot"""
        logger.info("Starting Telegram Agent Bot...")
        logger.info(f"MCP Status: {self.mcp_status}")
        
        # Start the bot
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

def test_dialogue():
    """Test dialogue simulation to demonstrate memory and vector DB functionality"""
    print("\n" + "="*50)
    print("TESTING DIALOGUE MEMORY & VECTOR DB FUNCTIONALITY")
    print("="*50)
    
    test_user_id = 12345
    
    # Test vector database
    print("--- Vector Database Test ---")
    try:
        # Load knowledge
        success = load_knowledge_from_json("knowledge.json")
        if success:
            print("+ Knowledge loaded successfully")
            
            # Test search
            test_queries = [
                "задачи и напоминания",
                "email уведомления", 
                "календарь события"
            ]
            
            for query in test_queries:
                results = search_knowledge(query, top_k=2)
                print(f"\nQuery: '{query}'")
                print(f"Found {len(results)} results:")
                for i, (text, score, metadata) in enumerate(results, 1):
                    print(f"  {i}. Score: {score:.3f}")
                    print(f"     Text: {text[:80]}...")
                    if metadata:
                        print(f"     Category: {metadata.get('category', 'N/A')}")
        else:
            print("- Failed to load knowledge")
    except Exception as e:
        print(f"- Vector DB error: {e}")
    
    # Simulate a conversation
    print(f"\n--- Conversation Test ---")
    test_messages = [
        "Привет! Как дела?",
        "Можешь помочь с календарем?",
        "Расскажи про задачи и напоминания",
        "Спасибо за помощь!",
        "А что насчет email уведомлений?"
    ]
    
    print(f"Simulating conversation for user {test_user_id}")
    print(f"Initial context: {len(get_context(test_user_id))} messages")
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Message {i} ---")
        print(f"User: {message}")
        
        # Get current context
        context = get_context(test_user_id)
        print(f"Context before: {len(context)} messages")
        
        # Test vector search for this message
        if i > 1:  # Skip first message
            search_results = search_knowledge(message, top_k=2)
            if search_results:
                print(f"Vector search found {len(search_results)} relevant facts")
                for text, score, metadata in search_results:
                    print(f"  - {text[:60]}... (score: {score:.3f})")
        
        # Generate response (simplified)
        if "календарь" in message.lower():
            response = "Я могу помочь с управлением календарем! Создавать события, просматривать расписание."
        elif "задачи" in message.lower() or "напоминания" in message.lower():
            response = "Я могу создавать напоминания о встречах и важных событиях через Google Calendar!"
        elif "email" in message.lower():
            response = "Отлично! Я могу отправлять email-уведомления через Gmail."
        elif "спасибо" in message.lower():
            response = "Пожалуйста! Всегда рад помочь!"
        else:
            response = f"Понял! Это сообщение #{i} в нашей беседе. Чем еще могу помочь?"
        
        print(f"Bot: {response}")
        
        # Save to memory
        save_message(test_user_id, message, response)
        
        # Check updated context
        updated_context = get_context(test_user_id)
        print(f"Context after: {len(updated_context)} messages")
    
    # Final statistics
    print(f"\n--- Final Statistics ---")
    memory_stats = get_memory_stats()
    vector_stats = get_vector_db_stats()
    
    print(f"Memory Database:")
    print(f"  Total users: {memory_stats.get('total_users', 0)}")
    print(f"  Total messages: {memory_stats.get('total_messages', 0)}")
    print(f"  Max messages per user: {memory_stats.get('max_messages_per_user', 0)}")

    print(f"Vector Database:")
    print(f"  Total knowledge items: {vector_stats.get('total_items', 0)}")
    print(f"  Model: {vector_stats.get('model_name', 'N/A')}")
    print(f"  Embedding dimension: {vector_stats.get('embedding_dimension', 'N/A')}")

    # Test LLM Agent
    print(f"\n--- LLM Agent Test ---")
    try:
        llm_stats = get_llm_stats()
        print(f"LLM Agent Status:")
        print(f"  Enabled: {llm_stats.get('enabled', False)}")
        print(f"  Model: {llm_stats.get('model', 'N/A')}")
        print(f"  API Key Configured: {llm_stats.get('api_key_configured', False)}")
        
        if llm_stats.get('enabled'):
            print("+ LLM Agent is ready for intelligent responses!")
        else:
            print("- LLM Agent disabled (no API key)")
    except Exception as e:
        print(f"- LLM Agent error: {e}")

    print("\n" + "="*50)
    print("DIALOGUE TEST COMPLETED")
    print("="*50)


def main():
    """Main application entry point"""
    print("Agent starting...")
    print("Project root:", project_root)
    print("Python version:", sys.version)
    
    # Check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("Warning: .env file not found!")
        print("Please copy env.example to .env and configure your API keys")
        return
    
    print("Environment file found")
    
    # Test dialogue functionality
    test_dialogue()
    
    try:
        # Create and run the bot
        bot = TelegramAgentBot()
        print("Bot initialized successfully!")
        print("Starting polling...")
        
        # Run the bot
        bot.run()
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please check your .env file and ensure TELEGRAM_TOKEN is set")
    except Exception as e:
        print(f"Error starting bot: {e}")
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()