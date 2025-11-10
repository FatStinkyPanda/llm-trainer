#!/usr/bin/env python3
"""
Telegram Service - Telegram Bot API Integration
================================================

Handles Telegram messaging via Bot API:
- Send messages
- Parse name registration commands
- Message formatting
- Media handling
"""

import re
import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class TelegramService:
    """Handles Telegram operations via Bot API"""

    def __init__(self, bot_token: str):
        """
        Initialize Telegram Bot

        Args:
            bot_token: Telegram bot token from @BotFather
        """
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        logger.info("Telegram Service initialized")

    def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown"
    ) -> bool:
        """
        Send message to Telegram chat

        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: 'Markdown' or 'HTML' (default: Markdown)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Split long messages (Telegram limit is 4096 characters)
            if len(text) > 4000:
                # Send in chunks
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for chunk in chunks:
                    self._send_message_api(chat_id, chunk, parse_mode)
                return True
            else:
                return self._send_message_api(chat_id, text, parse_mode)

        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return False

    def _send_message_api(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = None
    ) -> bool:
        """Internal method to call Telegram API"""
        try:
            url = f"{self.api_url}/sendMessage"

            payload = {
                "chat_id": chat_id,
                "text": text
            }

            if parse_mode:
                payload["parse_mode"] = parse_mode

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"Message sent to {chat_id}")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error calling Telegram API: {e}")
            return False

    def get_me(self) -> Optional[Dict]:
        """
        Get bot information

        Returns:
            Bot info dict or None if failed
        """
        try:
            url = f"{self.api_url}/getMe"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result')

            return None

        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return None

    def set_webhook(self, webhook_url: str) -> bool:
        """
        Set webhook URL for receiving updates

        Args:
            webhook_url: Public HTTPS URL for webhook

        Returns:
            True if successful
        """
        try:
            url = f"{self.api_url}/setWebhook"
            payload = {"url": webhook_url}

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    logger.info(f"Webhook set to: {webhook_url}")
                    return True

            logger.error(f"Failed to set webhook: {response.text}")
            return False

        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False

    def delete_webhook(self) -> bool:
        """
        Delete webhook (for polling mode)

        Returns:
            True if successful
        """
        try:
            url = f"{self.api_url}/deleteWebhook"
            response = requests.post(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    logger.info("Webhook deleted")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False

    def get_updates(self, offset: int = None, timeout: int = 30) -> list:
        """
        Get updates (polling mode)

        Args:
            offset: Update ID offset
            timeout: Long polling timeout

        Returns:
            List of updates
        """
        try:
            url = f"{self.api_url}/getUpdates"
            params = {"timeout": timeout}

            if offset:
                params["offset"] = offset

            response = requests.get(url, params=params, timeout=timeout + 5)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result', [])

            return []

        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []

    @staticmethod
    def parse_name_command(message: str) -> Optional[str]:
        """
        Parse name registration command from message

        Looks for pattern: "name=<name>" or "/setname <name>"

        Args:
            message: Telegram message text

        Returns:
            Extracted name or None if not a name command
        """
        # Remove extra whitespace and normalize
        message = message.strip()

        # Pattern 1: name=<anything> (case insensitive)
        pattern1 = r'^name\s*=\s*(.+)$'
        match = re.match(pattern1, message, re.IGNORECASE)

        if match:
            name = match.group(1).strip()
            # Remove quotes if user added them
            name = name.strip('"').strip("'")
            return name if name else None

        # Pattern 2: /setname <name>
        pattern2 = r'^/setname\s+(.+)$'
        match = re.match(pattern2, message, re.IGNORECASE)

        if match:
            name = match.group(1).strip()
            name = name.strip('"').strip("'")
            return name if name else None

        return None

    @staticmethod
    def is_name_command(message: str) -> bool:
        """
        Check if message is a name registration command

        Args:
            message: Telegram message text

        Returns:
            True if message is name command
        """
        return TelegramService.parse_name_command(message) is not None

    @staticmethod
    def is_command(message: str) -> bool:
        """
        Check if message is a bot command

        Args:
            message: Message text

        Returns:
            True if message starts with /
        """
        return message.strip().startswith('/')

    @staticmethod
    def format_welcome_message(name: Optional[str] = None) -> str:
        """
        Format welcome message for new user

        Args:
            name: User's name (if already registered)

        Returns:
            Welcome message text
        """
        if name:
            return (
                f"Welcome back, *{name}*! 👋\n\n"
                f"Send me any message to chat with the AI.\n\n"
                f"Commands:\n"
                f"• `/setname <name>` - Change your name\n"
                f"• `/clear` - Clear conversation history\n"
                f"• `/help` - Show help"
            )
        else:
            return (
                "👋 Welcome! To get started, please tell me your name:\n\n"
                "`/setname <your name>`\n\n"
                "For example: `/setname John`"
            )

    @staticmethod
    def format_name_registered_message(name: str) -> str:
        """
        Format confirmation message after name registration

        Args:
            name: Registered name

        Returns:
            Confirmation message
        """
        return (
            f"✅ Thanks, *{name}*! Your name has been saved.\n\n"
            f"You can now chat with the AI by sending any message.\n\n"
            f"Commands:\n"
            f"• `/setname <name>` - Change your name\n"
            f"• `/clear` - Clear conversation history\n"
            f"• `/help` - Show help"
        )

    @staticmethod
    def format_name_updated_message(name: str) -> str:
        """
        Format confirmation message after name update

        Args:
            name: Updated name

        Returns:
            Confirmation message
        """
        return f"✅ Your name has been updated to: *{name}*"

    @staticmethod
    def format_history_cleared_message() -> str:
        """Format confirmation message after clearing history"""
        return "✅ Your conversation history has been cleared!"

    @staticmethod
    def format_help_message() -> str:
        """Format help message"""
        return (
            "🤖 *AI Chat Bot Help*\n\n"
            "*Available Commands:*\n"
            "• `/start` - Start conversation\n"
            "• `/setname <name>` - Set or change your name\n"
            "• `/clear` - Clear conversation history\n"
            "• `/help` - Show this help message\n\n"
            "*How to use:*\n"
            "Just send me any message and I'll respond with AI-generated answers. "
            "Your conversation history is saved, so I remember context from previous messages.\n\n"
            "*Features:*\n"
            "✅ Natural conversations with AI\n"
            "✅ Context-aware responses\n"
            "✅ Persistent conversation history\n"
            "✅ Free to use!"
        )

    @staticmethod
    def format_error_message() -> str:
        """Format generic error message"""
        return (
            "❌ Sorry, I encountered an error processing your message. "
            "Please try again or use /help for assistance."
        )

    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Escape special characters for Markdown

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        # Escape special Markdown characters
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

        for char in special_chars:
            text = text.replace(char, f'\\{char}')

        return text

    def validate_connection(self) -> tuple[bool, str]:
        """
        Validate Telegram bot connection

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            bot_info = self.get_me()

            if bot_info:
                username = bot_info.get('username', 'Unknown')
                first_name = bot_info.get('first_name', 'Unknown')
                return True, f"Connected to bot: {first_name} (@{username})"
            else:
                return False, "Failed to get bot information"

        except Exception as e:
            return False, f"Connection error: {e}"

    @staticmethod
    def extract_message_data(update: Dict) -> Optional[Dict[str, Any]]:
        """
        Extract relevant data from Telegram update

        Args:
            update: Telegram update object

        Returns:
            Dict with chat_id, user_id, text, username, first_name
        """
        try:
            message = update.get('message', {})

            if not message:
                return None

            chat_id = str(message.get('chat', {}).get('id'))
            user_id = str(message.get('from', {}).get('id'))
            text = message.get('text', '').strip()
            username = message.get('from', {}).get('username')
            first_name = message.get('from', {}).get('first_name')
            last_name = message.get('from', {}).get('last_name', '')

            # Combine first and last name
            full_name = f"{first_name} {last_name}".strip() if first_name else None

            return {
                'chat_id': chat_id,
                'user_id': user_id,
                'text': text,
                'username': username,
                'full_name': full_name
            }

        except Exception as e:
            logger.error(f"Error extracting message data: {e}")
            return None
