#!/usr/bin/env python3
"""
Middleware Service - Bridge Between CEREBRUM and LLM
=====================================================

This service acts as a bridge between CEREBRUM (port 8000) and LLM Server (port 8001).
Runs on port 8002.

NO CEREBRUM IMPORTS. NO SHARED CODE.
Pure HTTP communication only.
"""

import sys

# Check dependencies on startup
try:
    from check_dependencies import check_and_install_dependencies
    if not check_and_install_dependencies(auto_install=True):
        print("✗ Failed to install dependencies. Exiting.")
        sys.exit(1)
except ImportError:
    print("Warning: Dependency checker not available")

import json
import logging
import threading
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests

# Load configuration
# Reload to get dynamically assigned LLM server port
with open('config.json', 'r') as f:
    config = json.load(f)

# Wait for LLM server port to be set (if not yet set)
import time
max_wait = 30
waited = 0
while 'llm_server_port' not in config and waited < max_wait:
    time.sleep(1)
    with open('config.json', 'r') as f:
        config = json.load(f)
    waited += 1

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [MIDDLEWARE] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="CEREBRUM-LLM Middleware", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class TrainingStartRequest(BaseModel):
    max_exchanges: int = 100
    delay: float = 2.0
    topic_switch_interval: int = 10


class TrainingStatus(BaseModel):
    running: bool
    exchanges_completed: int
    current_topic: str
    started_at: Optional[str]
    cerebrum_connected: bool
    llm_connected: bool


class ConversationExchange(BaseModel):
    timestamp: str
    llm_to_cerebrum: str
    cerebrum_response: str
    cerebrum_emotions: Dict[str, float]


# Training state
class TrainingState:
    def __init__(self):
        self.running = False
        self.exchanges_completed = 0
        self.current_topic_index = 0
        self.messages_on_current_topic = 0
        self.started_at: Optional[str] = None
        self.conversation_log: List[ConversationExchange] = []
        self.current_topic = ""


training_state = TrainingState()
training_thread: Optional[threading.Thread] = None


def check_cerebrum_connection() -> bool:
    """Check if CEREBRUM is accessible"""
    try:
        response = requests.get(f"{config['cerebrum_url']}/api/status", timeout=5)
        return response.status_code == 200
    except:
        return False


def check_llm_connection() -> bool:
    """Check if LLM server is accessible"""
    try:
        response = requests.get(f"http://localhost:{config['llm_server_port']}/", timeout=5)
        return response.status_code == 200
    except:
        return False


def send_to_cerebrum(message: str) -> Optional[Dict[str, Any]]:
    """
    Send message to CEREBRUM via its /api/chat endpoint

    Args:
        message: Message to send

    Returns:
        Response dict from CEREBRUM or None if failed
    """
    try:
        logger.info(f"→ CEREBRUM: {message[:60]}...")

        response = requests.post(
            f"{config['cerebrum_url']}/api/chat",
            json={
                "message": message,
                "user_id": "llm_trainer"
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            cerebrum_response = data.get('response', '')
            logger.info(f"← CEREBRUM: {cerebrum_response[:60]}...")
            return data
        else:
            logger.error(f"CEREBRUM returned {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error sending to CEREBRUM: {e}")
        return None


def send_to_llm(message: str, conversation_history: List[Dict[str, str]] = None) -> Optional[str]:
    """
    Send message to LLM server

    Args:
        message: Message to send
        conversation_history: Recent conversation context

    Returns:
        Response from LLM or None if failed
    """
    try:
        logger.info(f"→ LLM: {message[:60]}...")

        response = requests.post(
            f"http://localhost:{config['llm_server_port']}/api/chat",
            json={
                "message": message,
                "conversation_history": conversation_history,
                "temperature": 0.8,
                "max_tokens": 150
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            llm_response = data.get('response', '')
            logger.info(f"← LLM: {llm_response[:60]}...")
            return llm_response
        else:
            logger.error(f"LLM server returned {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error sending to LLM: {e}")
        return None


def get_next_topic(topics: List[str]) -> str:
    """Get next conversation topic"""
    topic = topics[training_state.current_topic_index]
    training_state.current_topic_index = (training_state.current_topic_index + 1) % len(topics)
    return topic


def save_conversation_log():
    """Save conversation log to file"""
    if not training_state.conversation_log:
        return

    # Create logs directory
    log_dir = Path("training_logs")
    log_dir.mkdir(exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = log_dir / f"session_{timestamp}.json"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'session_info': {
                    'started_at': training_state.started_at,
                    'exchanges_completed': training_state.exchanges_completed,
                    'duration': 'session'
                },
                'conversation': [ex.dict() for ex in training_state.conversation_log]
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Conversation log saved: {filename}")
    except Exception as e:
        logger.error(f"Failed to save log: {e}")


def training_loop(max_exchanges: int, delay: float, topic_switch_interval: int):
    """
    Main training loop that facilitates conversation between CEREBRUM and LLM

    Args:
        max_exchanges: Maximum number of exchanges
        delay: Delay between messages in seconds
        topic_switch_interval: Messages before switching topics
    """
    logger.info("="*70)
    logger.info("Starting conversation training loop")
    logger.info(f"Max exchanges: {max_exchanges}")
    logger.info(f"Delay: {delay}s")
    logger.info(f"Topic switch interval: {topic_switch_interval}")
    logger.info("="*70)

    topics = config['conversation_topics']
    conversation_history = []

    try:
        # Initial greeting from LLM
        greeting = "Hello CEREBRUM! I'm here to have a conversation with you and help you learn language."
        cerebrum_data = send_to_cerebrum(greeting)

        if not cerebrum_data:
            logger.error("Failed to start conversation with CEREBRUM")
            training_state.running = False
            return

        cerebrum_response = cerebrum_data.get('response', '')

        # Log exchange
        exchange = ConversationExchange(
            timestamp=datetime.now().isoformat(),
            llm_to_cerebrum=greeting,
            cerebrum_response=cerebrum_response,
            cerebrum_emotions=cerebrum_data.get('emotions', {})
        )
        training_state.conversation_log.append(exchange)
        training_state.exchanges_completed += 1
        training_state.messages_on_current_topic += 1

        # Update conversation history
        conversation_history.append({
            'user': greeting,
            'assistant': cerebrum_response
        })

        time.sleep(delay)

        # Main loop
        while training_state.running and training_state.exchanges_completed < max_exchanges:
            # Check if we should switch topics
            if training_state.messages_on_current_topic >= topic_switch_interval:
                logger.info(f"\n{'='*70}")
                logger.info("Switching to new topic...")
                logger.info(f"{'='*70}\n")

                training_state.messages_on_current_topic = 0
                new_topic = get_next_topic(topics)
                training_state.current_topic = new_topic

                # Send new topic to CEREBRUM
                cerebrum_data = send_to_cerebrum(new_topic)
                cerebrum_response = cerebrum_data.get('response', '') if cerebrum_data else ""
            else:
                # Generate LLM response to CEREBRUM's last message
                llm_response = send_to_llm(
                    cerebrum_response,
                    conversation_history[-config['max_conversation_history']:]
                )

                if not llm_response:
                    logger.warning("No LLM response, skipping...")
                    time.sleep(delay)
                    continue

                time.sleep(delay)

                # Send LLM's response to CEREBRUM
                cerebrum_data = send_to_cerebrum(llm_response)

                if not cerebrum_data:
                    logger.warning("No CEREBRUM response, skipping...")
                    time.sleep(delay)
                    continue

                cerebrum_response = cerebrum_data.get('response', '')

                # Log exchange
                exchange = ConversationExchange(
                    timestamp=datetime.now().isoformat(),
                    llm_to_cerebrum=llm_response,
                    cerebrum_response=cerebrum_response,
                    cerebrum_emotions=cerebrum_data.get('emotions', {})
                )
                training_state.conversation_log.append(exchange)
                training_state.exchanges_completed += 1
                training_state.messages_on_current_topic += 1

                # Update conversation history
                conversation_history.append({
                    'user': llm_response,
                    'assistant': cerebrum_response
                })

                # Keep history bounded
                if len(conversation_history) > config['max_conversation_history'] * 2:
                    conversation_history = conversation_history[-config['max_conversation_history'] * 2:]

            # Progress logging
            if training_state.exchanges_completed % 10 == 0:
                logger.info(f"\n{'='*70}")
                logger.info(f"Progress: {training_state.exchanges_completed}/{max_exchanges} exchanges")
                logger.info(f"Current topic: {training_state.current_topic_index}/{len(topics)}")
                logger.info(f"{'='*70}\n")

            time.sleep(delay)

    except Exception as e:
        logger.error(f"Error in training loop: {e}", exc_info=True)
    finally:
        training_state.running = False
        save_conversation_log()
        logger.info("Training loop stopped")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CEREBRUM-LLM Middleware",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/status")
async def get_status():
    """Get middleware status"""
    return {
        "middleware": "running",
        "cerebrum_url": config['cerebrum_url'],
        "llm_port": config['llm_server_port'],
        "cerebrum_connected": check_cerebrum_connection(),
        "llm_connected": check_llm_connection(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/cerebrum/status")
async def get_cerebrum_status():
    """Proxy to CEREBRUM status endpoint"""
    try:
        response = requests.get(f"{config['cerebrum_url']}/api/status", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail="CEREBRUM unreachable")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to CEREBRUM: {str(e)}")


@app.get("/api/llm/status")
async def get_llm_status():
    """Proxy to LLM server status endpoint"""
    try:
        response = requests.get(f"http://localhost:{config['llm_server_port']}/api/status", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail="LLM server unreachable")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to LLM server: {str(e)}")


@app.post("/api/training/start")
async def start_training(request: TrainingStartRequest, background_tasks: BackgroundTasks):
    """Start conversation training"""
    global training_thread

    if training_state.running:
        raise HTTPException(status_code=400, detail="Training already running")

    # Check connections
    if not check_cerebrum_connection():
        raise HTTPException(status_code=503, detail="CEREBRUM is not accessible")

    if not check_llm_connection():
        raise HTTPException(status_code=503, detail="LLM server is not accessible")

    # Reset state
    training_state.running = True
    training_state.exchanges_completed = 0
    training_state.current_topic_index = 0
    training_state.messages_on_current_topic = 0
    training_state.started_at = datetime.now().isoformat()
    training_state.conversation_log = []
    training_state.current_topic = ""

    # Start training thread
    training_thread = threading.Thread(
        target=training_loop,
        args=(request.max_exchanges, request.delay, request.topic_switch_interval),
        daemon=True
    )
    training_thread.start()

    logger.info("Training started")

    return {
        "status": "started",
        "max_exchanges": request.max_exchanges,
        "delay": request.delay,
        "started_at": training_state.started_at
    }


@app.post("/api/training/stop")
async def stop_training():
    """Stop conversation training"""
    if not training_state.running:
        raise HTTPException(status_code=400, detail="Training not running")

    training_state.running = False
    logger.info("Training stop requested")

    return {
        "status": "stopped",
        "exchanges_completed": training_state.exchanges_completed
    }


@app.get("/api/training/status", response_model=TrainingStatus)
async def get_training_status():
    """Get current training status"""
    return TrainingStatus(
        running=training_state.running,
        exchanges_completed=training_state.exchanges_completed,
        current_topic=training_state.current_topic,
        started_at=training_state.started_at,
        cerebrum_connected=check_cerebrum_connection(),
        llm_connected=check_llm_connection()
    )


@app.get("/api/training/log")
async def get_conversation_log(limit: int = 100):
    """Get conversation log"""
    log_entries = training_state.conversation_log[-limit:]
    return {
        "total_exchanges": len(training_state.conversation_log),
        "showing": len(log_entries),
        "exchanges": [ex.dict() for ex in log_entries]
    }


def run_server(host: str = "0.0.0.0", port: int = None):
    """Run the middleware server"""
    port = port or config['middleware_port']

    print("="*70)
    print("🌉 Middleware Service (CEREBRUM ↔ LLM Bridge)")
    print("="*70)
    print(f"Server: http://{host}:{port}")
    print(f"CEREBRUM: {config['cerebrum_url']}")
    print(f"LLM Server: http://localhost:{config['llm_server_port']}")
    print(f"API Docs: http://{host}:{port}/docs")
    print("="*70)
    print("")

    # Test connections
    if check_cerebrum_connection():
        print("✓ CEREBRUM is accessible")
    else:
        print("✗ WARNING: Cannot connect to CEREBRUM")
        print(f"  Make sure CEREBRUM is running at {config['cerebrum_url']}")

    if check_llm_connection():
        print("✓ LLM Server is accessible")
    else:
        print("✗ WARNING: Cannot connect to LLM Server")
        print(f"  Make sure LLM server is running on port {config['llm_server_port']}")

    print("")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
