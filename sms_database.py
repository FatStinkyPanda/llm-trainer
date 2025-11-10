#!/usr/bin/env python3
"""
SMS User Database - SQLite Storage
===================================

Manages user data for SMS integration:
- Phone numbers and names
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

class SMSDatabase:
    """Manages SMS user data and conversation history"""

    def __init__(self, db_path: str = "sms_users.db"):
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

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                phone_number TEXT PRIMARY KEY,
                name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Conversation history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (phone_number) REFERENCES users (phone_number)
            )
        """)

        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_phone
            ON conversations (phone_number, timestamp)
        """)

        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def get_user(self, phone_number: str) -> Optional[Dict]:
        """
        Get user by phone number

        Args:
            phone_number: User's phone number

        Returns:
            User dict or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE phone_number = ?",
            (phone_number,)
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def create_user(self, phone_number: str, name: Optional[str] = None) -> Dict:
        """
        Create new user

        Args:
            phone_number: User's phone number
            name: User's name (optional)

        Returns:
            Created user dict
        """
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO users (phone_number, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (phone_number, name, now, now)
        )

        self.conn.commit()
        logger.info(f"Created user: {phone_number} (name: {name})")

        return {
            "phone_number": phone_number,
            "name": name,
            "created_at": now,
            "updated_at": now
        }

    def update_user_name(self, phone_number: str, name: str) -> bool:
        """
        Update user's name

        Args:
            phone_number: User's phone number
            name: New name

        Returns:
            True if updated, False if user not found
        """
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE users
            SET name = ?, updated_at = ?
            WHERE phone_number = ?
            """,
            (name, now, phone_number)
        )

        self.conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Updated name for {phone_number}: {name}")
            return True
        return False

    def add_conversation_message(
        self,
        phone_number: str,
        role: str,
        message: str
    ) -> int:
        """
        Add message to conversation history

        Args:
            phone_number: User's phone number
            role: 'user' or 'assistant'
            message: Message text

        Returns:
            Message ID
        """
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO conversations (phone_number, role, message, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (phone_number, role, message, timestamp)
        )

        self.conn.commit()
        message_id = cursor.lastrowid

        logger.debug(f"Added {role} message for {phone_number}: {message[:50]}...")
        return message_id

    def get_conversation_history(
        self,
        phone_number: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get conversation history for user

        Args:
            phone_number: User's phone number
            limit: Max number of recent exchanges to return

        Returns:
            List of conversation messages
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT role, message, timestamp
            FROM conversations
            WHERE phone_number = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (phone_number, limit * 2)  # *2 because each exchange has 2 messages
        )

        rows = cursor.fetchall()

        # Reverse to get chronological order
        messages = [dict(row) for row in reversed(rows)]

        return messages

    def get_conversation_history_formatted(
        self,
        phone_number: str,
        limit: int = 5
    ) -> List[Dict[str, str]]:
        """
        Get conversation history formatted for LLM API

        Args:
            phone_number: User's phone number
            limit: Max number of recent exchanges

        Returns:
            List of dicts with 'user' and 'assistant' keys
        """
        messages = self.get_conversation_history(phone_number, limit)

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

    def clear_conversation_history(self, phone_number: str) -> int:
        """
        Clear conversation history for user

        Args:
            phone_number: User's phone number

        Returns:
            Number of messages deleted
        """
        cursor = self.conn.cursor()

        cursor.execute(
            "DELETE FROM conversations WHERE phone_number = ?",
            (phone_number,)
        )

        self.conn.commit()
        count = cursor.rowcount

        logger.info(f"Cleared {count} messages for {phone_number}")
        return count

    def get_all_users(self) -> List[Dict]:
        """Get all registered users"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_user_count(self) -> int:
        """Get total number of registered users"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        return cursor.fetchone()['count']

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
