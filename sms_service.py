#!/usr/bin/env python3
"""
SMS Service - Twilio Integration
=================================

Handles SMS messaging via Twilio:
- Send SMS messages
- Parse name registration commands
- Message formatting
"""

import re
import logging
from typing import Optional, Tuple
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class SMSService:
    """Handles SMS operations via Twilio"""

    def __init__(self, account_sid: str, auth_token: str, twilio_phone: str):
        """
        Initialize Twilio client

        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            twilio_phone: Your Twilio phone number (format: +1234567890)
        """
        self.client = Client(account_sid, auth_token)
        self.twilio_phone = twilio_phone
        logger.info(f"SMS Service initialized with number: {twilio_phone}")

    def send_sms(self, to_number: str, message: str) -> bool:
        """
        Send SMS message

        Args:
            to_number: Recipient phone number (format: +1234567890)
            message: Message text

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Split long messages if needed (SMS limit is 160 chars)
            if len(message) > 1600:  # Allow up to 10 segments
                message = message[:1597] + "..."

            msg = self.client.messages.create(
                body=message,
                from_=self.twilio_phone,
                to=to_number
            )

            logger.info(f"SMS sent to {to_number}: {msg.sid}")
            return True

        except TwilioRestException as e:
            logger.error(f"Twilio error sending to {to_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending SMS to {to_number}: {e}")
            return False

    @staticmethod
    def parse_name_command(message: str) -> Optional[str]:
        """
        Parse name registration command from message

        Looks for pattern: "name=<name>" or "name= <name>"

        Args:
            message: SMS message text

        Returns:
            Extracted name or None if not a name command
        """
        # Remove extra whitespace and normalize
        message = message.strip()

        # Pattern: name=<anything> (case insensitive)
        pattern = r'^name\s*=\s*(.+)$'
        match = re.match(pattern, message, re.IGNORECASE)

        if match:
            name = match.group(1).strip()
            # Remove quotes if user added them
            name = name.strip('"').strip("'")
            return name if name else None

        return None

    @staticmethod
    def is_name_command(message: str) -> bool:
        """
        Check if message is a name registration command

        Args:
            message: SMS message text

        Returns:
            True if message is name command
        """
        return SMSService.parse_name_command(message) is not None

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
                f"Welcome back, {name}! Send me any message to chat with the AI. "
                f"To change your name, text: name=<new name>"
            )
        else:
            return (
                "Welcome! To get started, please tell me your name by texting: "
                "name=<your name>\n\n"
                "For example: name=John"
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
            f"Thanks, {name}! Your name has been saved. "
            f"You can now chat with the AI by sending any message. "
            f"To change your name later, text: name=<new name>"
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
        return f"Your name has been updated to: {name}"

    @staticmethod
    def format_error_message() -> str:
        """Format generic error message"""
        return (
            "Sorry, I encountered an error processing your message. "
            "Please try again or contact support if the problem persists."
        )

    @staticmethod
    def normalize_phone_number(phone: str) -> str:
        """
        Normalize phone number to E.164 format

        Args:
            phone: Phone number in various formats

        Returns:
            Normalized phone number (e.g., +1234567890)
        """
        # Remove all non-digit characters except leading +
        if phone.startswith('+'):
            digits = '+' + re.sub(r'\D', '', phone[1:])
        else:
            digits = re.sub(r'\D', '', phone)
            # Add +1 for US numbers if not present
            if len(digits) == 10:
                digits = '+1' + digits
            elif not digits.startswith('+'):
                digits = '+' + digits

        return digits

    def validate_connection(self) -> Tuple[bool, str]:
        """
        Validate Twilio connection and credentials

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Try to fetch account info
            account = self.client.api.accounts(self.client.account_sid).fetch()

            if account.status == 'active':
                return True, f"Connected to Twilio account: {account.friendly_name}"
            else:
                return False, f"Twilio account status: {account.status}"

        except TwilioRestException as e:
            return False, f"Twilio authentication failed: {e}"
        except Exception as e:
            return False, f"Connection error: {e}"
