#!/usr/bin/env python3
"""
Agent module for Telegram Agent Bot
Handles LLM integration and response generation using OpenAI GPT-3.5-turbo
"""

import os
import logging
from typing import List, Dict, Any, Optional
import asyncio

try:
    import openai
except ImportError as e:
    logging.error(f"OpenAI package not installed: {e}")
    raise

logger = logging.getLogger(__name__)

class LLMAgent:
    """LLM Agent for generating intelligent responses"""
    
    def __init__(self, model: str = "gpt-3.5-turbo", max_tokens: int = 500, temperature: float = 0.7):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Initialize OpenAI client
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            logger.warning("OPENAI_API_KEY not found. LLM responses will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"LLM Agent initialized with model: {model}")
    
    async def generate_response(
        self, 
        context: List[Dict[str, Any]], 
        user_message: str, 
        knowledge: List[str]
    ) -> str:
        """
        Generate response using OpenAI GPT-3.5-turbo
        
        Args:
            context: Conversation history as list of dicts with 'role' and 'content'
            user_message: Current user message
            knowledge: List of relevant knowledge snippets
            
        Returns:
            Generated response string
        """
        if not self.enabled:
            return self._fallback_response(user_message, knowledge)
        
        try:
            # Check if message is about MCP tools
            if self._is_mcp_related(user_message):
                return await self._handle_mcp_request(user_message, context, knowledge)
            
            # Prepare system prompt
            system_prompt = self._create_system_prompt()
            
            # Prepare context for LLM
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation context
            if context:
                # Limit context to last 6 messages to avoid token limits
                recent_context = context[-6:]
                for msg in recent_context:
                    if msg['role'] in ['user', 'assistant']:
                        messages.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            response = await self._call_openai_api(messages)
            
            logger.info(f"Generated LLM response for message: {user_message[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._fallback_response(user_message, knowledge)
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for the LLM"""
        return """Ты - интеллектуальный личный помощник для Telegram. 

Твои возможности:
- Управление календарем через Google Calendar
- Отправка email-уведомлений через Gmail  
- Поиск информации в интернете
- Запоминание контекста разговоров
- Семантический поиск в базе знаний

Инструкции:
1. Отвечай на русском языке
2. Будь дружелюбным и полезным
3. Используй предоставленные знания для более точных ответов
4. Если пользователь просит создать событие, напомнить или отправить email - предложи соответствующие команды
5. Если нужно найти информацию - используй поиск
6. Помни контекст разговора и ссылайся на предыдущие сообщения

Команды MCP:
- /calendar "добавить событие дата название" - для создания событий
- /email "отправить email@example.com: тема" - для отправки email
- /search "запрос" - для поиска информации

Отвечай кратко, но информативно."""
    
    async def _call_openai_api(self, messages: List[Dict[str, str]]) -> str:
        """Call OpenAI API to generate response"""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _is_mcp_related(self, message: str) -> bool:
        """Check if message is related to MCP tools"""
        message_lower = message.lower()
        
        mcp_keywords = [
            'календарь', 'calendar', 'событие', 'встреча', 'напоминание',
            'email', 'почта', 'письмо', 'отправить', 'уведомление',
            'поиск', 'search', 'найти', 'информация', 'погода', 'курс'
        ]
        
        return any(keyword in message_lower for keyword in mcp_keywords)
    
    async def _handle_mcp_request(self, message: str, context: List[Dict[str, Any]], knowledge: List[str]) -> str:
        """Handle MCP-related requests"""
        message_lower = message.lower()
        
        # Calendar related
        if any(word in message_lower for word in ['календарь', 'calendar', 'событие', 'встреча', 'напоминание']):
            return (
                "Я могу помочь с управлением календарем! 📅\n\n"
                "Используй команду:\n"
                "/calendar \"добавить событие дата название\"\n\n"
                "Примеры:\n"
                "• /calendar \"добавить событие 10.10.2025 встреча с клиентом\"\n"
                "• /calendar \"добавить событие завтра совещание\"\n"
                "• /calendar \"добавить событие сегодня звонок\"\n\n"
                "Поддерживаемые форматы дат: DD.MM.YYYY, \"сегодня\", \"завтра\""
            )
        
        # Email related
        elif any(word in message_lower for word in ['email', 'почта', 'письмо', 'отправить', 'уведомление']):
            return (
                "Я могу отправлять email-уведомления! 📧\n\n"
                "Используй команду:\n"
                "/email \"отправить email@example.com: тема письма\"\n\n"
                "Примеры:\n"
                "• /email \"отправить reminder@example.com: встреча завтра\"\n"
                "• /email \"отправить boss@company.com: отчет готов\"\n"
                "• /email \"отправить friend@gmail.com: как дела?\"\n\n"
                "Я автоматически добавлю информацию о времени отправки."
            )
        
        # Search related
        elif any(word in message_lower for word in ['поиск', 'search', 'найти', 'информация', 'погода', 'курс']):
            return (
                "Я могу искать информацию в интернете! 🔍\n\n"
                "Используй команду:\n"
                "/search \"запрос для поиска\"\n\n"
                "Примеры:\n"
                "• /search \"погода в Москве\"\n"
                "• /search \"курс доллара\"\n"
                "• /search \"новости технологий\"\n"
                "• /search \"рецепт борща\"\n\n"
                "Я найду актуальную информацию и покажу результаты."
            )
        
        # General MCP suggestion
        else:
            return (
                "Я могу помочь с различными задачами! 🤖\n\n"
                "Доступные команды:\n"
                "📅 /calendar - управление календарем\n"
                "📧 /email - отправка уведомлений\n"
                "🔍 /search - поиск информации\n\n"
                "Или просто напиши мне что-нибудь - я запоминаю наш разговор и могу помочь!"
            )
    
    def _fallback_response(self, user_message: str, knowledge: List[str]) -> str:
        """Fallback response when LLM is not available"""
        message_lower = user_message.lower()
        
        # Simple keyword-based responses
        if any(word in message_lower for word in ['привет', 'hello', 'hi', 'здравствуй']):
            return "Привет! Рад тебя видеть! Как дела? Чем могу помочь?"
        
        elif any(word in message_lower for word in ['спасибо', 'thanks', 'thank you']):
            return "Пожалуйста! Всегда рад помочь! 😊"
        
        elif any(word in message_lower for word in ['календарь', 'calendar', 'событие']):
            return (
                "Я могу помочь с календарем! Используй команду:\n"
                "/calendar \"добавить событие дата название\""
            )
        
        elif any(word in message_lower for word in ['email', 'почта', 'письмо']):
            return (
                "Я могу отправлять email! Используй команду:\n"
                "/email \"отправить email@example.com: тема\""
            )
        
        elif any(word in message_lower for word in ['поиск', 'search', 'найти']):
            return (
                "Я могу искать информацию! Используй команду:\n"
                "/search \"запрос для поиска\""
            )
        
        else:
            return (
                "Понял! Я запоминаю наш разговор и готов помочь.\n\n"
                "Можешь использовать команды:\n"
                "• /calendar - для событий\n"
                "• /email - для уведомлений\n"
                "• /search - для поиска\n"
                "• /help - для справки"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get LLM agent statistics"""
        return {
            'enabled': self.enabled,
            'model': self.model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'api_key_configured': bool(openai.api_key)
        }


# Global LLM agent instance
llm_agent = LLMAgent()


# Convenience function
async def generate_response(
    context: List[Dict[str, Any]], 
    user_message: str, 
    knowledge: List[str]
) -> str:
    """Convenience function to generate response"""
    return await llm_agent.generate_response(context, user_message, knowledge)


def get_llm_stats() -> Dict[str, Any]:
    """Convenience function to get LLM stats"""
    return llm_agent.get_stats()
