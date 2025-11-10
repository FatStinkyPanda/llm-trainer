#!/usr/bin/env python3
"""
Messaging Database - Unified SQLite Storage
============================================

Manages user data for both SMS and Telegram:
- User IDs (phone numbers or Telegram chat IDs)
- Names and platform info
- Conversation history per user
- Persistent storage across restarts
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MessagingDatabase:
    """Manages user data and conversation history for SMS and Telegram"""

    def __init__(self, db_path: str = "messaging_users.db"):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._init_db()

    def _init_db(self):
        """Create database tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries

        cursor = self.conn.cursor()

        # Users table - supports both SMS (phone) and Telegram (chat_id)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                name TEXT,
                username TEXT,
                ai_backend TEXT DEFAULT 'openrouter',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Conversation history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Create indexes for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user
            ON conversations (user_id, timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_platform
            ON users (platform)
        """)

        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def get_user(self, user_id: str, platform: str = None) -> Optional[Dict]:
        """
        Get user by ID

        Args:
            user_id: User identifier (phone number or Telegram chat ID)
            platform: Platform filter (optional)

        Returns:
            User dict or None if not found
        """
        cursor = self.conn.cursor()

        if platform:
            cursor.execute(
                "SELECT * FROM users WHERE user_id = ? AND platform = ?",
                (user_id, platform)
            )
        else:
            cursor.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )

        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def create_user(
        self,
        user_id: str,
        platform: str,
        name: Optional[str] = None,
        username: Optional[str] = None,
        ai_backend: str = 'openrouter'
    ) -> Dict:
        """
        Create new user

        Args:
            user_id: User identifier (phone number or Telegram chat ID)
            platform: 'sms' or 'telegram'
            name: User's display name (optional)
            username: Telegram username (optional, Telegram only)
            ai_backend: AI backend preference ('openrouter' or 'cerebrum')

        Returns:
            Created user dict
        """
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO users (user_id, platform, name, username, ai_backend, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, platform, name, username, ai_backend, now, now)
        )

        self.conn.commit()
        logger.info(f"Created {platform} user: {user_id} (name: {name}, AI: {ai_backend})")

        return {
            "user_id": user_id,
            "platform": platform,
            "name": name,
            "username": username,
            "ai_backend": ai_backend,
            "created_at": now,
            "updated_at": now
        }

    def update_user_name(self, user_id: str, name: str, platform: str = None) -> bool:
        """
        Update user's name

        Args:
            user_id: User identifier
            name: New name
            platform: Platform filter (optional)

        Returns:
            True if updated, False if user not found
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        if platform:
            cursor.execute(
                """
                UPDATE users
                SET name = ?, updated_at = ?
                WHERE user_id = ? AND platform = ?
                """,
                (name, now, user_id, platform)
            )
        else:
            cursor.execute(
                """
                UPDATE users
                SET name = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (name, now, user_id)
            )

        self.conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Updated name for {user_id}: {name}")
            return True
        return False

    def update_user_ai_backend(self, user_id: str, ai_backend: str, platform: str = None) -> bool:
        """
        Update user's AI backend preference

        Args:
            user_id: User identifier
            ai_backend: AI backend ('openrouter' or 'cerebrum')
            platform: Platform filter (optional)

        Returns:
            True if updated, False if user not found
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        if platform:
            cursor.execute(
                """
                UPDATE users
                SET ai_backend = ?, updated_at = ?
                WHERE user_id = ? AND platform = ?
                """,
                (ai_backend, now, user_id, platform)
            )
        else:
            cursor.execute(
                """
                UPDATE users
                SET ai_backend = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (ai_backend, now, user_id)
            )

        self.conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Updated AI backend for {user_id}: {ai_backend}")
            return True
        return False

    def add_conversation_message(
        self,
        user_id: str,
        platform: str,
        role: str,
        message: str
    ) -> int:
        """
        Add message to conversation history

        Args:
            user_id: User identifier
            platform: 'sms' or 'telegram'
            role: 'user' or 'assistant'
            message: Message text

        Returns:
            Message ID
        """
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO conversations (user_id, platform, role, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, platform, role, message, timestamp)
        )

        self.conn.commit()
        message_id = cursor.lastrowid

        logger.debug(f"Added {role} message for {user_id} ({platform}): {message[:50]}...")
        return message_id

    def get_conversation_history(
        self,
        user_id: str,
        platform: str = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get conversation history for user

        Args:
            user_id: User identifier
            platform: Platform filter (optional)
            limit: Max number of recent exchanges to return

        Returns:
            List of conversation messages
        """
        cursor = self.conn.cursor()

        if platform:
            cursor.execute(
                """
                SELECT role, message, timestamp
                FROM conversations
                WHERE user_id = ? AND platform = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (user_id, platform, limit * 2)
            )
        else:
            cursor.execute(
                """
                SELECT role, message, timestamp
                FROM conversations
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (user_id, limit * 2)
            )

        rows = cursor.fetchall()

        # Reverse to get chronological order
        messages = [dict(row) for row in reversed(rows)]

        return messages

    def get_conversation_history_formatted(
        self,
        user_id: str,
        platform: str = None,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Get conversation history formatted for LLM API

        Args:
            user_id: User identifier
            platform: Platform filter (optional)
            limit: Max number of recent exchanges

        Returns:
            List of dicts with 'user' and 'assistant' keys
        """
        messages = self.get_conversation_history(user_id, platform, limit)

        formatted = []
        current_exchange = {}

        for msg in messages:
            if msg['role'] == 'user':
                current_exchange = {'user': msg['message']}
            elif msg['role'] == 'assistant' and current_exchange:
                current_exchange['assistant'] = msg['message']
                formatted.append(current_exchange)
                current_exchange = {}

        return formatted

    def clear_conversation_history(self, user_id: str, platform: str = None) -> int:
        """
        Clear conversation history for user

        Args:
            user_id: User identifier
            platform: Platform filter (optional)

        Returns:
            Number of messages deleted
        """
        cursor = self.conn.cursor()

        if platform:
            cursor.execute(
                "DELETE FROM conversations WHERE user_id = ? AND platform = ?",
                (user_id, platform)
            )
        else:
            cursor.execute(
                "DELETE FROM conversations WHERE user_id = ?",
                (user_id,)
            )

        self.conn.commit()
        count = cursor.rowcount

        logger.info(f"Cleared {count} messages for {user_id}")
        return count

    def get_all_users(self, platform: str = None) -> List[Dict]:
        """
        Get all registered users

        Args:
            platform: Filter by platform (optional)

        Returns:
            List of user dicts
        """
        cursor = self.conn.cursor()

        if platform:
            cursor.execute(
                "SELECT * FROM users WHERE platform = ? ORDER BY created_at DESC",
                (platform,)
            )
        else:
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_user_count(self, platform: str = None) -> int:
        """
        Get total number of registered users

        Args:
            platform: Filter by platform (optional)

        Returns:
            User count
        """
        cursor = self.conn.cursor()

        if platform:
            cursor.execute(
                "SELECT COUNT(*) as count FROM users WHERE platform = ?",
                (platform,)
            )
        else:
            cursor.execute("SELECT COUNT(*) as count FROM users")

        return cursor.fetchone()['count']

    def get_statistics(self) -> Dict:
        """
        Get database statistics

        Returns:
            Stats dict with user counts and message counts per platform
        """
        cursor = self.conn.cursor()

        # Total users
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']

        # Users by platform
        cursor.execute("""
            SELECT platform, COUNT(*) as count
            FROM users
            GROUP BY platform
        """)
        users_by_platform = {row['platform']: row['count'] for row in cursor.fetchall()}

        # Total messages
        cursor.execute("SELECT COUNT(*) as count FROM conversations")
        total_messages = cursor.fetchone()['count']

        # Messages by platform
        cursor.execute("""
            SELECT platform, COUNT(*) as count
            FROM conversations
            GROUP BY platform
        """)
        messages_by_platform = {row['platform']: row['count'] for row in cursor.fetchall()}

        return {
            "total_users": total_users,
            "users_by_platform": users_by_platform,
            "total_messages": total_messages,
            "messages_by_platform": messages_by_platform
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Backward compatibility alias for SMS
SMSDatabase = MessagingDatabase
