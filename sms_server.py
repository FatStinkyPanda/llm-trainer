#!/usr/bin/env python3
"""
SMS Server - Twilio Webhook Integration
========================================

Provides SMS interface to the LLM Server:
- Receives SMS via Twilio webhooks
- Manages user registration and names
- Routes messages to AI and sends responses
- Maintains separate conversation contexts per user
"""

import sys
import json
import logging
import os
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import Response
import uvicorn
import requests
from dotenv import load_dotenv

from sms_database import SMSDatabase
from sms_service import SMSService

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
    format='%(asctime)s - [SMS-SERVER] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="SMS Server", version="1.0.0")

# Initialize database
db = SMSDatabase()

# Initialize SMS service (will be configured after startup)
sms_service: Optional[SMSService] = None


def init_sms_service() -> bool:
    """
    Initialize SMS service with Twilio credentials

    Returns:
        True if initialized successfully
    """
    global sms_service

    # Get Twilio credentials from environment or config
    account_sid = os.getenv('TWILIO_ACCOUNT_SID') or config.get('twilio_account_sid')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN') or config.get('twilio_auth_token')
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER') or config.get('twilio_phone_number')

    if not all([account_sid, auth_token, twilio_phone]):
        logger.error("Twilio credentials not configured")
        return False

    try:
        sms_service = SMSService(account_sid, auth_token, twilio_phone)

        # Validate connection
        is_valid, message = sms_service.validate_connection()
        if is_valid:
            logger.info(f"Twilio connection validated: {message}")
            return True
        else:
            logger.error(f"Twilio validation failed: {message}")
            return False

    except Exception as e:
        logger.error(f"Failed to initialize SMS service: {e}")
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
            "max_tokens": 300  # Longer responses for SMS
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


@app.on_event("startup")
async def startup_event():
    """Initialize SMS service on startup"""
    logger.info("Starting SMS Server...")
    if init_sms_service():
        logger.info(f"{CHECK} SMS Service initialized")
    else:
        logger.warning(f"{CROSS} SMS Service initialization failed - check credentials")


@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "SMS Server",
        "twilio_configured": sms_service is not None,
        "database": "connected",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/sms/webhook")
async def sms_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(None)
):
    """
    Twilio webhook endpoint for receiving SMS messages

    This endpoint is called by Twilio when an SMS is received.
    Configure this URL in your Twilio console:
    https://your-domain.com/sms/webhook (or use ngrok for local testing)

    Args:
        From: Sender's phone number (Twilio parameter)
        Body: Message text (Twilio parameter)
        MessageSid: Message ID (Twilio parameter)

    Returns:
        Empty TwiML response (200 OK)
    """
    if not sms_service:
        logger.error("SMS service not initialized")
        return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                       media_type="application/xml")

    phone_number = SMSService.normalize_phone_number(From)
    message = Body.strip()

    logger.info(f"Received SMS from {phone_number}: {message[:60]}...")

    try:
        # Check if this is a name command
        if SMSService.is_name_command(message):
            name = SMSService.parse_name_command(message)

            if not name:
                sms_service.send_sms(
                    phone_number,
                    "Please provide a valid name. Format: name=<your name>"
                )
                return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                               media_type="application/xml")

            # Check if user exists
            user = db.get_user(phone_number)

            if user:
                # Update existing name
                db.update_user_name(phone_number, name)
                response_text = SMSService.format_name_updated_message(name)
            else:
                # Create new user
                db.create_user(phone_number, name)
                response_text = SMSService.format_name_registered_message(name)

            sms_service.send_sms(phone_number, response_text)

        else:
            # Regular message - check if user is registered
            user = db.get_user(phone_number)

            if not user or not user['name']:
                # User not registered or no name
                response_text = SMSService.format_welcome_message()
                sms_service.send_sms(phone_number, response_text)

            else:
                # User is registered - process message with AI
                # Get conversation history
                conversation_history = db.get_conversation_history_formatted(
                    phone_number,
                    limit=5
                )

                # Save user message
                db.add_conversation_message(phone_number, 'user', message)

                # Get AI response
                ai_response = get_llm_response(message, conversation_history)

                if ai_response:
                    # Save AI response
                    db.add_conversation_message(phone_number, 'assistant', ai_response)

                    # Send response to user
                    sms_service.send_sms(phone_number, ai_response)
                else:
                    # AI failed - send error message
                    error_msg = SMSService.format_error_message()
                    sms_service.send_sms(phone_number, error_msg)

    except Exception as e:
        logger.error(f"Error processing SMS: {e}", exc_info=True)
        # Send error message to user
        try:
            sms_service.send_sms(
                phone_number,
                SMSService.format_error_message()
            )
        except:
            pass

    # Return empty TwiML response (required by Twilio)
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml"
    )


@app.get("/sms/status")
async def get_sms_status():
    """Get SMS service status and statistics"""
    user_count = db.get_user_count()
    users = db.get_all_users()

    twilio_status = "disconnected"
    if sms_service:
        is_valid, message = sms_service.validate_connection()
        twilio_status = "connected" if is_valid else f"error: {message}"

    return {
        "twilio_status": twilio_status,
        "twilio_phone": config.get('twilio_phone_number'),
        "total_users": user_count,
        "users": [
            {
                "phone": user['phone_number'],
                "name": user['name'],
                "registered": user['created_at']
            }
            for user in users
        ],
        "timestamp": datetime.now().isoformat()
    }


@app.post("/sms/send")
async def send_sms_manual(phone_number: str, message: str):
    """
    Manually send SMS (for testing or admin use)

    Args:
        phone_number: Recipient phone number
        message: Message text

    Returns:
        Status response
    """
    if not sms_service:
        raise HTTPException(status_code=503, detail="SMS service not initialized")

    phone_number = SMSService.normalize_phone_number(phone_number)

    success = sms_service.send_sms(phone_number, message)

    if success:
        return {"status": "sent", "to": phone_number}
    else:
        raise HTTPException(status_code=500, detail="Failed to send SMS")


@app.delete("/sms/user/{phone_number}/history")
async def clear_user_history(phone_number: str):
    """
    Clear conversation history for a user

    Args:
        phone_number: User's phone number

    Returns:
        Status response
    """
    phone_number = SMSService.normalize_phone_number(phone_number)
    count = db.clear_conversation_history(phone_number)

    return {
        "status": "cleared",
        "phone_number": phone_number,
        "messages_deleted": count
    }


def run_server(host: str = "0.0.0.0", port: int = 8040):
    """Run the SMS server"""
    print("="*70, flush=True)
    print("SMS Server - Twilio Integration", flush=True)
    print("="*70, flush=True)
    print(f"Server: http://{host}:{port}", flush=True)
    print(f"Webhook URL: http://{host}:{port}/sms/webhook", flush=True)
    print(f"Status: http://{host}:{port}/sms/status", flush=True)
    print(f"API Docs: http://{host}:{port}/docs", flush=True)
    print("="*70, flush=True)
    print("", flush=True)
    print("IMPORTANT: Configure webhook URL in Twilio console", flush=True)
    print("For local testing, use ngrok to expose this server", flush=True)
    print("", flush=True)

    # Check if Twilio credentials are configured
    if not all([
        os.getenv('TWILIO_ACCOUNT_SID') or config.get('twilio_account_sid'),
        os.getenv('TWILIO_AUTH_TOKEN') or config.get('twilio_auth_token'),
        os.getenv('TWILIO_PHONE_NUMBER') or config.get('twilio_phone_number')
    ]):
        print(f"{CROSS} WARNING: Twilio credentials not configured!", flush=True)
        print("  Set environment variables or add to config.json:", flush=True)
        print("  - TWILIO_ACCOUNT_SID", flush=True)
        print("  - TWILIO_AUTH_TOKEN", flush=True)
        print("  - TWILIO_PHONE_NUMBER", flush=True)
        print("", flush=True)

    print(f"{CHECK} Starting server...", flush=True)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
