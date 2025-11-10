#!/usr/bin/env python3
"""
Telegram Bot Server
===================

Provides Telegram interface to the LLM Server:
- Receives messages via webhook or polling
- Manages user registration and names
- Routes messages to AI and sends responses
- Maintains separate conversation contexts per user
- 100% FREE - no costs!
"""

import sys
import json
import logging
import os
import threading
import time
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import requests
from dotenv import load_dotenv

from messaging_database import MessagingDatabase
from telegram_service import TelegramService

# Load environment variables
load_dotenv()

# Windows-safe symbols
CHECK = "[OK]"
CROSS = "[X]"

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [TELEGRAM-BOT] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Telegram Bot Server", version="1.0.0")

# Initialize database (shared with SMS)
db = MessagingDatabase()

# Initialize Telegram service (will be configured after startup)
telegram_service: Optional[TelegramService] = None

# Polling state
polling_active = False
polling_thread = None


def init_telegram_service() -> bool:
    """
    Initialize Telegram service with bot token

    Returns:
        True if initialized successfully
    """
    global telegram_service

    # Get bot token from environment or config
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or config.get('telegram_bot_token')

    if not bot_token:
        logger.error("Telegram bot token not configured")
        return False

    try:
        telegram_service = TelegramService(bot_token)

        # Validate connection
        is_valid, message = telegram_service.validate_connection()
        if is_valid:
            logger.info(f"Telegram connection validated: {message}")
            return True
        else:
            logger.error(f"Telegram validation failed: {message}")
            return False

    except Exception as e:
        logger.error(f"Failed to initialize Telegram service: {e}")
        return False


def get_llm_response(user_message: str, conversation_history: list) -> Optional[str]:
    """
    Get response from LLM Server

    Args:
        user_message: User's message
        conversation_history: Previous conversation context

    Returns:
        AI response or None if failed
    """
    try:
        llm_server_port = config.get('llm_server_port', 8033)
        llm_url = f"http://localhost:{llm_server_port}/api/chat"

        payload = {
            "message": user_message,
            "conversation_history": conversation_history,
            "temperature": 0.8,
            "max_tokens": 500  # Longer responses for Telegram
        }

        logger.info(f"Calling LLM Server at {llm_url}")

        response = requests.post(llm_url, json=payload, timeout=60)

        if response.status_code == 200:
            data = response.json()
            ai_response = data.get('response', '')
            logger.info(f"Got AI response: {ai_response[:60]}...")
            return ai_response
        else:
            logger.error(f"LLM Server returned {response.status_code}: {response.text}")
            return None

    except requests.exceptions.Timeout:
        logger.error("LLM Server request timed out")
        return None
    except Exception as e:
        logger.error(f"Error calling LLM Server: {e}")
        return None


def process_telegram_message(chat_id: str, text: str, username: str = None, full_name: str = None):
    """
    Process incoming Telegram message

    Args:
        chat_id: Telegram chat ID
        text: Message text
        username: Telegram username (optional)
        full_name: User's full name from Telegram (optional)
    """
    if not telegram_service:
        logger.error("Telegram service not initialized")
        return

    logger.info(f"Processing message from {chat_id}: {text[:60]}...")

    try:
        # Handle commands
        if text.startswith('/'):
            handle_command(chat_id, text, username, full_name)
            return

        # Check if this is a name command
        if TelegramService.is_name_command(text):
            name = TelegramService.parse_name_command(text)

            if not name:
                telegram_service.send_message(
                    chat_id,
                    "Please provide a valid name. Use: `/setname <your name>`"
                )
                return

            # Check if user exists
            user = db.get_user(chat_id, 'telegram')

            if user:
                # Update existing name
                db.update_user_name(chat_id, name, 'telegram')
                response_text = TelegramService.format_name_updated_message(name)
            else:
                # Create new user
                db.create_user(chat_id, 'telegram', name, username)
                response_text = TelegramService.format_name_registered_message(name)

            telegram_service.send_message(chat_id, response_text)

        else:
            # Regular message - check if user is registered
            user = db.get_user(chat_id, 'telegram')

            if not user or not user['name']:
                # User not registered or no name
                # Use Telegram first name if available
                if full_name:
                    db.create_user(chat_id, 'telegram', full_name, username)
                    response_text = TelegramService.format_name_registered_message(full_name)
                    telegram_service.send_message(chat_id, response_text)
                else:
                    response_text = TelegramService.format_welcome_message()
                    telegram_service.send_message(chat_id, response_text)
                    return

            # User is registered - process message with AI
            # Get conversation history
            conversation_history = db.get_conversation_history_formatted(
                chat_id,
                'telegram',
                limit=5
            )

            # Save user message
            db.add_conversation_message(chat_id, 'telegram', 'user', text)

            # Send "typing" indicator (optional - requires webhook mode)
            # telegram_service.send_chat_action(chat_id, 'typing')

            # Get AI response
            ai_response = get_llm_response(text, conversation_history)

            if ai_response:
                # Save AI response
                db.add_conversation_message(chat_id, 'telegram', 'assistant', ai_response)

                # Send response to user
                telegram_service.send_message(chat_id, ai_response, parse_mode=None)
            else:
                # AI failed - send error message
                error_msg = TelegramService.format_error_message()
                telegram_service.send_message(chat_id, error_msg)

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        # Send error message to user
        try:
            telegram_service.send_message(
                chat_id,
                TelegramService.format_error_message()
            )
        except:
            pass


def handle_command(chat_id: str, command: str, username: str = None, full_name: str = None):
    """
    Handle bot commands

    Args:
        chat_id: Telegram chat ID
        command: Command text
        username: Telegram username
        full_name: User's full name
    """
    command_lower = command.lower().strip()

    if command_lower == '/start':
        # Check if user exists
        user = db.get_user(chat_id, 'telegram')

        if user and user['name']:
            response = TelegramService.format_welcome_message(user['name'])
        else:
            # Auto-register with Telegram name if available
            if full_name:
                db.create_user(chat_id, 'telegram', full_name, username)
                response = TelegramService.format_name_registered_message(full_name)
            else:
                response = TelegramService.format_welcome_message()

        telegram_service.send_message(chat_id, response)

    elif command_lower == '/help':
        response = TelegramService.format_help_message()
        telegram_service.send_message(chat_id, response)

    elif command_lower == '/clear':
        count = db.clear_conversation_history(chat_id, 'telegram')
        response = TelegramService.format_history_cleared_message()
        telegram_service.send_message(chat_id, response)

    elif command_lower.startswith('/setname'):
        # Let process_telegram_message handle it
        process_telegram_message(chat_id, command, username, full_name)

    else:
        telegram_service.send_message(
            chat_id,
            f"Unknown command. Use /help to see available commands."
        )


@app.on_event("startup")
async def startup_event():
    """Initialize Telegram service on startup"""
    logger.info("Starting Telegram Bot Server...")
    if init_telegram_service():
        logger.info(f"{CHECK} Telegram Service initialized")
    else:
        logger.warning(f"{CROSS} Telegram Service initialization failed - check bot token")


@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Telegram Bot Server",
        "telegram_configured": telegram_service is not None,
        "database": "connected",
        "polling": polling_active,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint for receiving updates

    Configure this URL in BotFather:
    https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-domain.com/telegram/webhook

    Args:
        request: FastAPI request with Telegram update

    Returns:
        OK response
    """
    if not telegram_service:
        logger.error("Telegram service not initialized")
        return JSONResponse({"ok": True})

    try:
        update = await request.json()
        logger.debug(f"Received webhook update: {update}")

        # Extract message data
        msg_data = TelegramService.extract_message_data(update)

        if msg_data and msg_data['text']:
            # Process message in background
            threading.Thread(
                target=process_telegram_message,
                args=(
                    msg_data['chat_id'],
                    msg_data['text'],
                    msg_data.get('username'),
                    msg_data.get('full_name')
                ),
                daemon=True
            ).start()

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)

    # Always return OK to Telegram
    return JSONResponse({"ok": True})


@app.get("/telegram/status")
async def get_telegram_status():
    """Get Telegram bot status and statistics"""
    user_count = db.get_user_count('telegram')
    users = db.get_all_users('telegram')

    bot_status = "disconnected"
    bot_info = None

    if telegram_service:
        is_valid, message = telegram_service.validate_connection()
        bot_status = "connected" if is_valid else f"error: {message}"
        if is_valid:
            bot_info = telegram_service.get_me()

    return {
        "bot_status": bot_status,
        "bot_info": bot_info,
        "polling_active": polling_active,
        "total_users": user_count,
        "users": [
            {
                "chat_id": user['user_id'],
                "name": user['name'],
                "username": user['username'],
                "registered": user['created_at']
            }
            for user in users
        ],
        "timestamp": datetime.now().isoformat()
    }


@app.post("/telegram/send")
async def send_telegram_message(chat_id: str, message: str):
    """
    Manually send Telegram message (for testing or admin use)

    Args:
        chat_id: Recipient chat ID
        message: Message text

    Returns:
        Status response
    """
    if not telegram_service:
        raise HTTPException(status_code=503, detail="Telegram service not initialized")

    success = telegram_service.send_message(chat_id, message, parse_mode=None)

    if success:
        return {"status": "sent", "to": chat_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to send message")


@app.post("/telegram/polling/start")
async def start_polling():
    """Start polling mode (alternative to webhook)"""
    global polling_active, polling_thread

    if polling_active:
        return {"status": "already_running"}

    if not telegram_service:
        raise HTTPException(status_code=503, detail="Telegram service not initialized")

    # Delete webhook first
    telegram_service.delete_webhook()

    polling_active = True
    polling_thread = threading.Thread(target=polling_loop, daemon=True)
    polling_thread.start()

    return {"status": "started"}


@app.post("/telegram/polling/stop")
async def stop_polling():
    """Stop polling mode"""
    global polling_active

    if not polling_active:
        return {"status": "not_running"}

    polling_active = False
    return {"status": "stopped"}


def polling_loop():
    """Main polling loop for receiving updates"""
    logger.info("Starting polling loop...")
    offset = None

    while polling_active:
        try:
            updates = telegram_service.get_updates(offset=offset, timeout=30)

            for update in updates:
                # Update offset
                update_id = update.get('update_id')
                if update_id:
                    offset = update_id + 1

                # Extract and process message
                msg_data = TelegramService.extract_message_data(update)

                if msg_data and msg_data['text']:
                    process_telegram_message(
                        msg_data['chat_id'],
                        msg_data['text'],
                        msg_data.get('username'),
                        msg_data.get('full_name')
                    )

        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            time.sleep(5)  # Wait before retrying

    logger.info("Polling loop stopped")


def run_server(host: str = "0.0.0.0", port: int = 8041, use_polling: bool = True):
    """
    Run the Telegram bot server

    Args:
        host: Host to bind to
        port: Port to bind to
        use_polling: If True, use polling mode; if False, use webhook mode
    """
    print("="*70, flush=True)
    print("Telegram Bot Server - FREE AI Chat", flush=True)
    print("="*70, flush=True)
    print(f"Server: http://{host}:{port}", flush=True)
    print(f"Status: http://{host}:{port}/telegram/status", flush=True)
    print(f"API Docs: http://{host}:{port}/docs", flush=True)
    print("="*70, flush=True)
    print("", flush=True)

    # Check if bot token is configured
    if not (os.getenv('TELEGRAM_BOT_TOKEN') or config.get('telegram_bot_token')):
        print(f"{CROSS} WARNING: Telegram bot token not configured!", flush=True)
        print("  Set environment variable or add to config.json:", flush=True)
        print("  - TELEGRAM_BOT_TOKEN", flush=True)
        print("  Get a token from @BotFather on Telegram", flush=True)
        print("", flush=True)

    print(f"Mode: {'POLLING' if use_polling else 'WEBHOOK'}", flush=True)

    if use_polling:
        print(f"{CHECK} Using polling mode (no webhook needed)", flush=True)
        print("  Bot will automatically check for new messages", flush=True)

        # Start polling in a separate thread after server starts
        def delayed_start_polling():
            time.sleep(2)  # Wait for server to start
            if telegram_service:
                telegram_service.delete_webhook()
                global polling_active, polling_thread
                polling_active = True
                polling_thread = threading.Thread(target=polling_loop, daemon=True)
                polling_thread.start()
                print(f"{CHECK} Polling started", flush=True)

        threading.Thread(target=delayed_start_polling, daemon=True).start()
    else:
        print("  Webhook mode - configure webhook URL:", flush=True)
        print("  POST to /telegram/webhook", flush=True)

    print("", flush=True)
    print(f"{CHECK} Starting server...", flush=True)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    # Default to polling mode for easy local testing
    run_server(use_polling=True)
