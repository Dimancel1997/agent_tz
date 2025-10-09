#!/usr/bin/env python3
"""
Memory module for Telegram Agent Bot
Handles conversation context storage using SQLite
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConversationMemory:
    """Handles conversation memory storage and retrieval"""
    
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = Path(db_path)
        self.max_messages = 10  # Keep last 10 messages per user
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with conversations table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create conversations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        user_id INTEGER PRIMARY KEY,
                        session_history TEXT NOT NULL DEFAULT '[]',
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create index for better performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_id 
                    ON conversations(user_id)
                """)
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def save_message(self, user_id: int, message: str, response: str) -> bool:
        """
        Save user message and bot response to database
        
        Args:
            user_id: Telegram user ID
            message: User's message
            response: Bot's response
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get existing conversation history
                cursor.execute(
                    "SELECT session_history FROM conversations WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Update existing conversation
                    history = json.loads(result[0])
                else:
                    # Create new conversation
                    history = []
                
                # Add new messages to history
                history.append({
                    "role": "user",
                    "content": message,
                    "timestamp": self._get_timestamp()
                })
                
                history.append({
                    "role": "assistant", 
                    "content": response,
                    "timestamp": self._get_timestamp()
                })
                
                # Keep only last max_messages
                if len(history) > self.max_messages:
                    history = history[-self.max_messages:]
                
                # Save to database
                cursor.execute("""
                    INSERT OR REPLACE INTO conversations (user_id, session_history, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (user_id, json.dumps(history)))
                
                conn.commit()
                logger.debug(f"Saved message for user {user_id}")
                return True
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Error saving message for user {user_id}: {e}")
            return False
    
    def get_context(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get conversation context for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of conversation messages with role and content
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT session_history FROM conversations WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    history = json.loads(result[0])
                    logger.debug(f"Retrieved {len(history)} messages for user {user_id}")
                    return history
                else:
                    logger.debug(f"No conversation history found for user {user_id}")
                    return []
                    
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Error retrieving context for user {user_id}: {e}")
            return []
    
    def clear_context(self, user_id: int) -> bool:
        """
        Clear conversation history for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "DELETE FROM conversations WHERE user_id = ?",
                    (user_id,)
                )
                
                conn.commit()
                logger.info(f"Cleared conversation history for user {user_id}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error clearing context for user {user_id}: {e}")
            return False
    
    def get_all_users(self) -> List[int]:
        """
        Get list of all user IDs with conversation history
        
        Returns:
            List of user IDs
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT user_id FROM conversations")
                results = cursor.fetchall()
                
                return [row[0] for row in results]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting user list: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Dictionary with database stats
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count total users
                cursor.execute("SELECT COUNT(*) FROM conversations")
                total_users = cursor.fetchone()[0]
                
                # Count total messages
                cursor.execute("SELECT session_history FROM conversations")
                results = cursor.fetchall()
                
                total_messages = 0
                for result in results:
                    history = json.loads(result[0])
                    total_messages += len(history)
                
                return {
                    "total_users": total_users,
                    "total_messages": total_messages,
                    "database_path": str(self.db_path),
                    "max_messages_per_user": self.max_messages
                }
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def close(self):
        """Close database connection (if needed)"""
        # SQLite connections are automatically closed, but this method
        # can be used for cleanup if needed in the future
        pass


# Global memory instance
memory = ConversationMemory()


def save_message(user_id: int, message: str, response: str) -> bool:
    """Convenience function to save message"""
    return memory.save_message(user_id, message, response)


def get_context(user_id: int) -> List[Dict[str, Any]]:
    """Convenience function to get context"""
    return memory.get_context(user_id)


def clear_context(user_id: int) -> bool:
    """Convenience function to clear context"""
    return memory.clear_context(user_id)


def get_memory_stats() -> Dict[str, Any]:
    """Convenience function to get memory stats"""
    return memory.get_stats()
