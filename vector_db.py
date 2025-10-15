#!/usr/bin/env python3
"""
Упрощенная векторная база данных для Telegram Agent Bot
Использует простые текстовые поиски вместо ML эмбеддингов
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any
import sqlite3

logger = logging.getLogger(__name__)

class SimpleKnowledgeBase:
    """Простая база знаний на основе текстового поиска"""
    
    def __init__(self, db_path: str = "knowledge.db"):
        # Создаем директорию для данных если её нет
        data_dir = Path("/app/data") if Path("/app").exists() else Path("data")
        data_dir.mkdir(exist_ok=True)
        
        self.db_path = data_dir / db_path
        self.knowledge_path = Path("knowledge.json")
        
        # Инициализация SQLite базы данных
        self._init_database()
        
        logger.info("Simple knowledge base initialized")
    
    def _init_database(self):
        """Инициализация SQLite базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создание таблицы знаний
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создание индекса для полнотекстового поиска
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_text ON knowledge(text)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def add_knowledge(self, texts: List[str], metadata: List[Dict[str, Any]] = None) -> bool:
        """
        Добавить знания в базу данных
        
        Args:
            texts: Список текстовых документов
            metadata: Опциональные метаданные для каждого текста
            
        Returns:
            bool: True если успешно, False иначе
        """
        try:
            if not texts:
                logger.warning("No texts provided to add_knowledge")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for i, text in enumerate(texts):
                meta = metadata[i] if metadata and i < len(metadata) else {}
                meta_json = json.dumps(meta, ensure_ascii=False)
                
                cursor.execute(
                    'INSERT INTO knowledge (text, metadata) VALUES (?, ?)',
                    (text, meta_json)
                )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Added {len(texts)} knowledge items to database")
            return True
            
        except Exception as e:
            logger.error(f"Error adding knowledge: {e}")
            return False
    
    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Поиск релевантных знаний по запросу
        
        Args:
            query: Поисковый запрос
            top_k: Количество лучших результатов
            
        Returns:
            Список кортежей: (текст, оценка, метаданные)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Простой поиск по ключевым словам
            query_words = re.findall(r'\w+', query.lower())
            
            if not query_words:
                conn.close()
                return []
            
            # Поиск по ключевым словам
            search_conditions = []
            params = []
            
            for word in query_words:
                search_conditions.append("LOWER(text) LIKE ?")
                params.append(f"%{word}%")
            
            sql = f'''
                SELECT text, metadata, 
                       ({" + ".join([f"CASE WHEN LOWER(text) LIKE ? THEN 1 ELSE 0 END" for _ in query_words])}) as score
                FROM knowledge 
                WHERE {" OR ".join(search_conditions)}
                ORDER BY score DESC, LENGTH(text) ASC
                LIMIT ?
            '''
            
            # Добавляем параметры для подсчета очков
            params.extend([f"%{word}%" for word in query_words])
            params.append(top_k)
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
            conn.close()
            
            # Форматирование результатов
            formatted_results = []
            for text, meta_json, score in results:
                try:
                    metadata = json.loads(meta_json) if meta_json else {}
                except:
                    metadata = {}
                
                # Нормализация оценки (0-1)
                normalized_score = min(score / len(query_words), 1.0)
                formatted_results.append((text, normalized_score, metadata))
            
            logger.debug(f"Search query '{query}' returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return []
    
    def load_knowledge_from_json(self, json_path: str = None) -> bool:
        """
        Загрузить знания из JSON файла
        
        Args:
            json_path: Путь к JSON файлу с знаниями
            
        Returns:
            bool: True если успешно, False иначе
        """
        try:
            if json_path is None:
                json_path = self.knowledge_path
            
            json_path = Path(json_path)
            if not json_path.exists():
                logger.warning(f"Knowledge JSON file not found: {json_path}")
                return False
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                # Список строк
                texts = data
                metadata = [{}] * len(texts)
            elif isinstance(data, dict) and 'knowledge' in data:
                # Структурированный формат
                knowledge_items = data['knowledge']
                texts = [item.get('text', '') for item in knowledge_items]
                metadata = [item.get('metadata', {}) for item in knowledge_items]
            else:
                logger.error("Invalid JSON format for knowledge")
                return False
            
            # Фильтрация пустых текстов
            valid_items = [(text, meta) for text, meta in zip(texts, metadata) if text.strip()]
            if not valid_items:
                logger.warning("No valid knowledge items found in JSON")
                return False
            
            texts, metadata = zip(*valid_items)
            
            # Добавление в базу данных
            success = self.add_knowledge(list(texts), list(metadata))
            
            if success:
                logger.info(f"Loaded {len(texts)} knowledge items from {json_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error loading knowledge from JSON: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику базы знаний"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM knowledge')
            total_items = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_items': total_items,
                'model_name': 'Simple Text Search',
                'db_path': str(self.db_path),
                'knowledge_path': str(self.knowledge_path)
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_items': 0,
                'model_name': 'Simple Text Search',
                'db_path': str(self.db_path),
                'knowledge_path': str(self.knowledge_path)
            }
    
    def clear(self) -> bool:
        """Очистить всю базу знаний"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM knowledge')
            conn.commit()
            conn.close()
            
            logger.info("Cleared knowledge database")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            return False


# Глобальный экземпляр базы знаний
knowledge_db = SimpleKnowledgeBase()


def add_knowledge(texts: List[str], metadata: List[Dict[str, Any]] = None) -> bool:
    """Удобная функция для добавления знаний"""
    return knowledge_db.add_knowledge(texts, metadata)


def search_knowledge(query: str, top_k: int = 3) -> List[Tuple[str, float, Dict[str, Any]]]:
    """Удобная функция для поиска знаний"""
    return knowledge_db.search(query, top_k)


def load_knowledge_from_json(json_path: str = None) -> bool:
    """Удобная функция для загрузки знаний из JSON"""
    return knowledge_db.load_knowledge_from_json(json_path)


def get_vector_db_stats() -> Dict[str, Any]:
    """Удобная функция для получения статистики базы знаний"""
    return knowledge_db.get_stats()


def save_vector_db() -> bool:
    """Удобная функция для сохранения базы знаний (не нужно для SQLite)"""
    return True
