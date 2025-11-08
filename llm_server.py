#!/usr/bin/env python3
"""
LLM Server - Isolated Ollama Interface
=======================================

Serves the local Ollama gemma3:1b model via HTTP API.
Runs on port 8001, completely separate from CEREBRUM.

NO CEREBRUM IMPORTS. NO SHARED CODE.
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
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests
from dotenv import load_dotenv

from port_utils import find_free_port

# Load environment variables from .env file
load_dotenv()

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Override API key from environment if available (more secure)
if os.getenv('OPENROUTER_API_KEY'):
    config['openrouter_api_key'] = os.getenv('OPENROUTER_API_KEY')

# Find free port in configured range
port_range = config.get('llm_server_port_range', [8030, 8035])
LLM_SERVER_PORT = find_free_port(port_range[0], port_range[1])

if LLM_SERVER_PORT is None:
    raise RuntimeError(f"No free port available in range {port_range[0]}-{port_range[1]}")

# Save the selected port for other services to use
config['llm_server_port'] = LLM_SERVER_PORT
with open('config.json', 'w') as f:
    json.dump(config, f, indent=2)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [LLM-SERVER] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Server", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    temperature: float = 0.8
    max_tokens: int = 150


class ChatResponse(BaseModel):
    response: str
    timestamp: str
    model: str
    tokens_used: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    model: str
    timestamp: str


# Conversation history storage (in-memory)
conversation_contexts: Dict[str, List[Dict[str, str]]] = {}


def check_ollama_connection() -> bool:
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get(f"{config['ollama_url']}/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False


def check_openrouter_connection() -> bool:
    """Check if OpenRouter API key is configured"""
    return bool(config.get('openrouter_api_key', '').strip())


def generate_ollama_response(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: float = 0.8,
    max_tokens: int = 150
) -> Optional[str]:
    """
    Generate response using Ollama API

    Args:
        message: The user message
        conversation_history: Previous conversation context
        temperature: Sampling temperature
        max_tokens: Max tokens in response

    Returns:
        Generated response text or None if failed
    """
    try:
        # Build prompt with conversation history
        prompt = ""

        if conversation_history:
            for exchange in conversation_history[-5:]:  # Last 5 exchanges
                prompt += f"User: {exchange.get('user', '')}\n"
                prompt += f"Assistant: {exchange.get('assistant', '')}\n"

        prompt += f"User: {message}\nAssistant:"

        # Call Ollama API
        payload = {
            "model": config['ollama_model'],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        logger.info(f"Calling Ollama with model: {config['ollama_model']}")

        response = requests.post(
            f"{config['ollama_url']}/api/generate",
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            generated_text = data.get('response', '').strip()

            logger.info(f"Generated response: {generated_text[:60]}...")
            return generated_text
        else:
            logger.error(f"Ollama returned status {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error calling Ollama: {e}", exc_info=True)
        return None


def generate_openrouter_response(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: float = 0.8,
    max_tokens: int = 150
) -> Optional[str]:
    """
    Generate response using OpenRouter API

    Args:
        message: The user message
        conversation_history: Previous conversation context
        temperature: Sampling temperature
        max_tokens: Max tokens in response

    Returns:
        Generated response text or None if failed
    """
    try:
        api_key = config.get('openrouter_api_key', '').strip()
        if not api_key:
            logger.error("OpenRouter API key not configured")
            return None

        # Build messages array with conversation history
        messages = []

        if conversation_history:
            for exchange in conversation_history[-5:]:  # Last 5 exchanges
                messages.append({"role": "user", "content": exchange.get('user', '')})
                messages.append({"role": "assistant", "content": exchange.get('assistant', '')})

        messages.append({"role": "user", "content": message})

        # Call OpenRouter API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",  # Required by OpenRouter
            "X-Title": "CEREBRUM LLM Trainer"  # Optional
        }

        payload = {
            "model": config.get('openrouter_model', 'anthropic/claude-3.5-sonnet'),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        logger.info(f"Calling OpenRouter with model: {payload['model']}")

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            generated_text = data['choices'][0]['message']['content'].strip()

            logger.info(f"Generated response: {generated_text[:60]}...")
            return generated_text
        else:
            logger.error(f"OpenRouter returned status {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error calling OpenRouter: {e}", exc_info=True)
        return None


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    ollama_connected = check_ollama_connection()

    return HealthResponse(
        status="running" if ollama_connected else "ollama_disconnected",
        ollama_connected=ollama_connected,
        model=config['ollama_model'],
        timestamp=datetime.now().isoformat()
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the LLM

    This is the ONLY interface to the LLM.
    Accepts a message, returns a response.
    Supports both Ollama (local) and OpenRouter (API).
    """
    logger.info(f"Received chat request: {request.message[:60]}...")

    # Reload config to get latest settings
    with open('config.json', 'r') as f:
        current_config = json.load(f)

    llm_source = current_config.get('llm_source', 'ollama')
    response_text = None
    model_used = None

    if llm_source == 'openrouter':
        # Use OpenRouter
        if not check_openrouter_connection():
            raise HTTPException(
                status_code=503,
                detail="OpenRouter API key not configured"
            )

        response_text = generate_openrouter_response(
            message=request.message,
            conversation_history=request.conversation_history,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        model_used = current_config.get('openrouter_model', 'unknown')

    else:  # Default to Ollama
        # Use Ollama (local)
        if not check_ollama_connection():
            raise HTTPException(
                status_code=503,
                detail="Ollama is not running or not accessible"
            )

        response_text = generate_ollama_response(
            message=request.message,
            conversation_history=request.conversation_history,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        model_used = current_config.get('ollama_model', 'unknown')

    if not response_text:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response from {llm_source}"
        )

    return ChatResponse(
        response=response_text,
        timestamp=datetime.now().isoformat(),
        model=model_used,
        tokens_used=None
    )


@app.get("/api/status")
async def get_status():
    """Get detailed server status"""
    ollama_connected = check_ollama_connection()

    # Get available models from Ollama
    models = []
    if ollama_connected:
        try:
            response = requests.get(f"{config['ollama_url']}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
        except:
            pass

    return {
        "server": "running",
        "ollama_url": config['ollama_url'],
        "ollama_connected": ollama_connected,
        "configured_model": config['ollama_model'],
        "available_models": models,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/reset")
async def reset_conversation():
    """Reset conversation history"""
    conversation_contexts.clear()
    logger.info("Conversation history cleared")
    return {"status": "reset", "timestamp": datetime.now().isoformat()}


def run_server(host: str = "0.0.0.0", port: int = None):
    """Run the LLM server"""
    port = port or LLM_SERVER_PORT

    print("="*70, flush=True)
    print("LLM Server (Isolated from CEREBRUM)", flush=True)
    print("="*70, flush=True)
    print(f"Port Range: {port_range[0]}-{port_range[1]}", flush=True)
    print(f"Selected Port: {port}", flush=True)
    print(f"Server: http://{host}:{port}", flush=True)
    print(f"Ollama URL: {config['ollama_url']}", flush=True)
    print(f"Model: {config['ollama_model']}", flush=True)
    print(f"API Docs: http://{host}:{port}/docs", flush=True)
    print("="*70, flush=True)
    print("", flush=True)

    # Test Ollama connection
    if check_ollama_connection():
        print(f"{CHECK} Ollama is running and accessible", flush=True)
    else:
        print(f"{CROSS} WARNING: Cannot connect to Ollama", flush=True)
        print(f"  Make sure Ollama is running and accessible at {config['ollama_url']}", flush=True)
        print(f"  Run: ollama serve", flush=True)
        print(f"  And: ollama pull {config['ollama_model']}", flush=True)

    print("", flush=True)
    print(f"{CHECK} Starting uvicorn server...", flush=True)

    # Configure uvicorn for subprocess execution
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    run_server()
