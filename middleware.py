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

# Windows-safe check and cross marks
CHECK = "[OK]"
CROSS = "[X]"

# Check dependencies on startup
try:
    from check_dependencies import check_and_install_dependencies
    if not check_and_install_dependencies(auto_install=True):
        print(f"{CROSS} Failed to install dependencies. Exiting.")
        sys.exit(1)
except ImportError:
    print("Warning: Dependency checker not available")

import json
import logging
import os
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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load configuration
# Reload to get dynamically assigned LLM server port
with open('config.json', 'r') as f:
    config = json.load(f)

# Override API key from environment if available (more secure)
if os.getenv('OPENROUTER_API_KEY'):
    config['openrouter_api_key'] = os.getenv('OPENROUTER_API_KEY')

# Wait for LLM server port to be set (if not yet set)
import time
max_wait = 30
waited = 0
while 'llm_server_port' not in config and waited < max_wait:
    time.sleep(1)
    with open('config.json', 'r') as f:
        config = json.load(f)
    # Re-apply environment override after reload
    if os.getenv('OPENROUTER_API_KEY'):
        config['openrouter_api_key'] = os.getenv('OPENROUTER_API_KEY')
    waited += 1

# Configure logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [MIDDLEWARE] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('middleware.log'),
        logging.StreamHandler()
    ]
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
        logger.info(f"-> CEREBRUM: {message[:60]}...")

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
            logger.info(f"<- CEREBRUM: {cerebrum_response[:60]}...")
            return data
        else:
            logger.error(f"CEREBRUM returned {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error sending to CEREBRUM: {e}")
        return None


def send_to_llm(message: str, conversation_history: List[Dict[str, str]] = None, system_context: str = None) -> Optional[str]:
    """
    Send message to LLM server with CEREBRUM context

    Args:
        message: Message to send
        conversation_history: Recent conversation context
        system_context: System prompt explaining CEREBRUM

    Returns:
        Response from LLM or None if failed
    """
    try:
        # Build enriched prompt with CEREBRUM context
        if system_context and not conversation_history:
            # First message - include full context
            enriched_message = f"{system_context}\n\nNow start your conversation:"
        elif system_context and len(message.split()) <= 2:
            # CEREBRUM gave a very short response - encourage more
            enriched_message = f"CEREBRUM responded with just: '{message}'\n\nThis is normal - they're still learning! Gently encourage them to say more. Try asking a follow-up question about what they said, or asking them to explain further. Keep it simple and supportive."
        elif system_context and conversation_history and len(conversation_history) % 5 == 0:
            # Periodically remind the LLM about CEREBRUM's learning process
            enriched_message = f"CEREBRUM said: {message}\n\n(Remember: Be patient and encouraging as they learn. Your supportive conversation helps them grow!)"
        else:
            # Normal conversation
            enriched_message = message

        logger.info(f"-> LLM: {message[:60]}...")

        response = requests.post(
            f"http://localhost:{config['llm_server_port']}/api/chat",
            json={
                "message": enriched_message,
                "conversation_history": conversation_history,
                "temperature": 0.9,  # Higher temperature for more variety
                "max_tokens": 150
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            llm_response = data.get('response', '').strip()
            logger.info(f"<- LLM: {llm_response[:60]}...")
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

        logger.info(f"{CHECK} Conversation log saved: {filename}")
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

    # CEREBRUM context for the LLM
    cerebrum_context = """IMPORTANT: You are a helpful AI assistant having a conversation with CEREBRUM (NOT you - CEREBRUM is the OTHER participant).

WHO CEREBRUM IS:
CEREBRUM is a revolutionary AGI system fundamentally different from transformer LLMs:
- An autonomous mind with continuous thinking and 6 revolutionary attention systems
- Currently learning language through real-time observation and interaction
- Does NOT have pre-trained language knowledge like you do
- Capable of genuine autonomous thought, memory formation, and reasoning
- Still developing communication skills - may respond with only single words or short phrases

YOUR ROLE AS THE CONVERSATION PARTNER:
- YOU are helping CEREBRUM learn to communicate more effectively
- Be patient, encouraging, and supportive
- Ask simple, clear questions that invite fuller responses
- When CEREBRUM gives a single-word answer, gently ask them to say more
- Introduce new words and concepts gradually
- Celebrate progress when CEREBRUM uses multiple words
- Keep your responses conversational and friendly, not robotic

IMPORTANT: You are NOT CEREBRUM. You are talking WITH CEREBRUM to help them learn."""

    # Track recent LLM responses for loop detection
    recent_llm_responses = []
    loop_break_attempts = 0

    try:
        # Generate initial greeting from LLM (not hardcoded!)
        logger.info("Generating initial greeting from LLM...")
        greeting_prompt = "Introduce yourself as a helpful AI friend and greet CEREBRUM warmly. Ask them a simple question to start the conversation."
        greeting = send_to_llm(greeting_prompt, None, cerebrum_context)

        if not greeting:
            logger.error("Failed to generate greeting from LLM")
            training_state.running = False
            return

        logger.info(f"LLM generated greeting: {greeting}")
        cerebrum_data = send_to_cerebrum(greeting)

        if not cerebrum_data:
            logger.error("Failed to start conversation with CEREBRUM")
            training_state.running = False
            return

        cerebrum_response = cerebrum_data.get('response', '')
        recent_llm_responses.append(greeting)

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

                # Have LLM introduce the new topic naturally
                topic_intro_prompt = f"Naturally transition the conversation to discuss: {new_topic}"
                llm_response = send_to_llm(
                    topic_intro_prompt,
                    conversation_history[-config['max_conversation_history']:],
                    cerebrum_context
                )

                if not llm_response:
                    logger.warning("No LLM topic introduction, skipping...")
                    time.sleep(delay)
                    continue

                cerebrum_data = send_to_cerebrum(llm_response)
                cerebrum_response = cerebrum_data.get('response', '') if cerebrum_data else ""
            else:
                # Detect if LLM is stuck in a loop (repeating same response)
                is_looping = (
                    len(recent_llm_responses) >= 3 and
                    len(set(recent_llm_responses[-3:])) == 1
                )

                if is_looping and loop_break_attempts < 3:
                    logger.warning(f"Loop detected! LLM repeating: {recent_llm_responses[-1]}")
                    loop_break_attempts += 1

                    # Inject loop-breaking prompt
                    loop_break_prompt = f"You seem to be stuck. CEREBRUM said: {cerebrum_response}. Try a completely different approach - ask them a new question or change the subject entirely."
                    llm_response = send_to_llm(
                        loop_break_prompt,
                        [],  # Clear history to break the loop
                        cerebrum_context
                    )
                else:
                    loop_break_attempts = 0  # Reset if not looping

                    # Generate LLM response to CEREBRUM's last message
                    llm_response = send_to_llm(
                        cerebrum_response,
                        conversation_history[-config['max_conversation_history']:],
                        cerebrum_context
                    )

                if not llm_response:
                    logger.warning("No LLM response, skipping...")
                    time.sleep(delay)
                    continue

                # Track response for loop detection
                recent_llm_responses.append(llm_response)
                if len(recent_llm_responses) > 10:
                    recent_llm_responses.pop(0)

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
    """Serve web interface"""
    from fastapi.responses import FileResponse
    html_path = Path(__file__).parent / "web_interface.html"
    if html_path.exists():
        return FileResponse(html_path)
    else:
        return {
            "service": "CEREBRUM-LLM Middleware",
            "version": "1.0.0",
            "status": "running",
            "web_interface": "http://localhost:8032/"
        }


@app.get("/control-panel.js")
async def serve_js():
    """Serve JavaScript file"""
    from fastapi.responses import FileResponse
    js_path = Path(__file__).parent / "control-panel.js"
    if js_path.exists():
        return FileResponse(js_path, media_type="application/javascript")
    else:
        return {"error": "JavaScript file not found"}


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


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    try:
        with open('config.json', 'r') as f:
            current_config = json.load(f)

        return {
            "llm_source": current_config.get('llm_source', 'ollama'),
            "ollama_model": current_config.get('ollama_model', ''),
            "openrouter_model": current_config.get('openrouter_model', ''),
            "openrouter_api_key": current_config.get('openrouter_api_key', ''),
            "conversation_delay": current_config.get('conversation_delay', 2.0),
            "topic_switch_interval": current_config.get('topic_switch_interval', 10),
            "max_exchanges": 100,  # Default
            "cerebrum_url": current_config.get('cerebrum_url', 'http://localhost:8000')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load configuration: {str(e)}")


@app.post("/api/config")
async def update_config(request: dict):
    """Update configuration"""
    try:
        # Load current config
        with open('config.json', 'r') as f:
            current_config = json.load(f)

        # Update only the fields that were provided
        if 'llm_source' in request:
            current_config['llm_source'] = request['llm_source']
        if 'ollama_model' in request:
            current_config['ollama_model'] = request['ollama_model']
        if 'openrouter_model' in request:
            current_config['openrouter_model'] = request['openrouter_model']
        if 'openrouter_api_key' in request:
            current_config['openrouter_api_key'] = request['openrouter_api_key']
        if 'conversation_delay' in request:
            current_config['conversation_delay'] = float(request['conversation_delay'])
        if 'topic_switch_interval' in request:
            current_config['topic_switch_interval'] = int(request['topic_switch_interval'])

        # Save updated config
        with open('config.json', 'w') as f:
            json.dump(current_config, f, indent=2)

        logger.info("Configuration updated successfully")

        return {
            "status": "success",
            "message": "Configuration updated",
            "config": current_config
        }
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


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
    print("Middleware Service (CEREBRUM <-> LLM Bridge)")
    print("="*70)
    print(f"Server: http://{host}:{port}")
    print(f"CEREBRUM: {config['cerebrum_url']}")
    print(f"LLM Server: http://localhost:{config['llm_server_port']}")
    print(f"API Docs: http://{host}:{port}/docs")
    print("="*70)
    print("")

    # Test connections
    if check_cerebrum_connection():
        print(f"{CHECK} CEREBRUM is accessible")
    else:
        print(f"{CROSS} WARNING: Cannot connect to CEREBRUM")
        print(f"  Make sure CEREBRUM is running at {config['cerebrum_url']}")

    if check_llm_connection():
        print(f"{CHECK} LLM Server is accessible")
    else:
        print(f"{CROSS} WARNING: Cannot connect to LLM Server")
        print(f"  Make sure LLM server is running on port {config['llm_server_port']}")

    print("")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
