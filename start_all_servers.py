#!/usr/bin/env python3
"""
Unified Server Launcher
=======================

Starts all messaging servers:
- LLM Server (AI backend)
- SMS Server (optional, requires Twilio)
- Telegram Bot (optional, 100% free)

Usage:
    python start_all_servers.py --all              # Start all configured services
    python start_all_servers.py --llm --telegram   # Start LLM + Telegram only
    python start_all_servers.py --llm --sms        # Start LLM + SMS only
    python start_all_servers.py --telegram         # Start Telegram only (needs LLM running)
"""

import sys
import argparse
import subprocess
import time
import json
import os
from pathlib import Path

# Windows-safe symbols
CHECK = "[OK]"
CROSS = "[X]"
ARROW = "-->"

def load_config():
    """Load configuration"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"{CROSS} Error loading config.json: {e}")
        return {}

def check_env_file():
    """Check if .env file exists"""
    return Path('.env').exists()

def check_twilio_config():
    """Check if Twilio is configured"""
    from dotenv import load_dotenv
    load_dotenv()

    config = load_config()

    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID') or config.get('twilio_account_sid')
    twilio_token = os.getenv('TWILIO_AUTH_TOKEN') or config.get('twilio_auth_token')
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER') or config.get('twilio_phone_number')

    return all([twilio_sid, twilio_token, twilio_phone])

def check_telegram_config():
    """Check if Telegram is configured"""
    from dotenv import load_dotenv
    load_dotenv()

    config = load_config()

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or config.get('telegram_bot_token')

    return bool(bot_token)

def print_header():
    """Print startup header"""
    print("="*70)
    print("Multi-Platform AI Chat Server Launcher")
    print("="*70)
    print("")

def print_service_status(service_name, configured, cost=""):
    """Print service configuration status"""
    if configured:
        status = f"{CHECK} {service_name} - Configured"
        if cost:
            status += f" ({cost})"
        print(status)
    else:
        print(f"{CROSS} {service_name} - Not configured (skipping)")

def start_llm_server():
    """Start LLM Server"""
    print(f"\n{ARROW} Starting LLM Server...")
    try:
        process = subprocess.Popen(
            [sys.executable, "llm_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        time.sleep(3)  # Wait for startup

        if process.poll() is None:
            print(f"{CHECK} LLM Server started (PID: {process.pid})")
            return process
        else:
            print(f"{CROSS} LLM Server failed to start")
            return None
    except Exception as e:
        print(f"{CROSS} Error starting LLM Server: {e}")
        return None

def start_sms_server():
    """Start SMS Server"""
    print(f"\n{ARROW} Starting SMS Server...")
    try:
        process = subprocess.Popen(
            [sys.executable, "sms_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        time.sleep(2)  # Wait for startup

        if process.poll() is None:
            print(f"{CHECK} SMS Server started (PID: {process.pid})")
            return process
        else:
            print(f"{CROSS} SMS Server failed to start")
            return None
    except Exception as e:
        print(f"{CROSS} Error starting SMS Server: {e}")
        return None

def start_telegram_server():
    """Start Telegram Bot Server"""
    print(f"\n{ARROW} Starting Telegram Bot...")
    try:
        process = subprocess.Popen(
            [sys.executable, "telegram_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        time.sleep(2)  # Wait for startup

        if process.poll() is None:
            print(f"{CHECK} Telegram Bot started (PID: {process.pid})")
            return process
        else:
            print(f"{CROSS} Telegram Bot failed to start")
            return None
    except Exception as e:
        print(f"{CROSS} Error starting Telegram Bot: {e}")
        return None

def print_summary(services):
    """Print running services summary"""
    print("\n" + "="*70)
    print("Services Running:")
    print("="*70)

    for service_name, process in services.items():
        if process:
            print(f"{CHECK} {service_name} (PID: {process.pid})")

    print("\n" + "="*70)
    print("Service URLs:")
    print("="*70)

    config = load_config()

    if 'LLM Server' in services and services['LLM Server']:
        port = config.get('llm_server_port', 8033)
        print(f"LLM Server:    http://localhost:{port}")
        print(f"  API Docs:    http://localhost:{port}/docs")

    if 'SMS Server' in services and services['SMS Server']:
        port = config.get('sms_server_port', 8040)
        print(f"SMS Server:    http://localhost:{port}")
        print(f"  Status:      http://localhost:{port}/sms/status")

    if 'Telegram Bot' in services and services['Telegram Bot']:
        port = config.get('telegram_server_port', 8041)
        print(f"Telegram Bot:  http://localhost:{port}")
        print(f"  Status:      http://localhost:{port}/telegram/status")

    print("\n" + "="*70)
    print("Press Ctrl+C to stop all services")
    print("="*70)

def main():
    """Main launcher"""
    parser = argparse.ArgumentParser(description="Start messaging servers")
    parser.add_argument('--all', action='store_true', help='Start all configured services')
    parser.add_argument('--llm', action='store_true', help='Start LLM Server')
    parser.add_argument('--sms', action='store_true', help='Start SMS Server')
    parser.add_argument('--telegram', action='store_true', help='Start Telegram Bot')

    args = parser.parse_args()

    # If no args, show help
    if not any([args.all, args.llm, args.sms, args.telegram]):
        parser.print_help()
        print("\n" + "="*70)
        print("Quick Start Examples:")
        print("="*70)
        print(f"  python {sys.argv[0]} --all              # Start all")
        print(f"  python {sys.argv[0]} --llm --telegram   # LLM + Telegram")
        print(f"  python {sys.argv[0]} --llm --sms        # LLM + SMS")
        return

    print_header()

    # Check configurations
    print("Checking Configuration:")
    print("-" * 70)

    has_env = check_env_file()
    if not has_env:
        print(f"{CROSS} .env file not found (optional)")
        print(f"  Create from: cp .env.example .env")
    else:
        print(f"{CHECK} .env file found")

    print("")

    twilio_configured = check_twilio_config()
    telegram_configured = check_telegram_config()

    print_service_status("LLM Server", True, "Required for AI")
    print_service_status("SMS Server", twilio_configured, "~$2-3/month")
    print_service_status("Telegram Bot", telegram_configured, "FREE!")

    # Determine which services to start
    start_llm = args.all or args.llm
    start_sms = (args.all and twilio_configured) or args.sms
    start_telegram_bot = (args.all and telegram_configured) or args.telegram

    # Validate configurations
    if start_sms and not twilio_configured:
        print(f"\n{CROSS} SMS Server requested but Twilio not configured")
        print("  Configure in .env or config.json")
        start_sms = False

    if start_telegram_bot and not telegram_configured:
        print(f"\n{CROSS} Telegram Bot requested but token not configured")
        print("  Get token from @BotFather and add to .env")
        start_telegram_bot = False

    if not any([start_llm, start_sms, start_telegram_bot]):
        print(f"\n{CROSS} No services to start. Exiting.")
        return

    print("\n" + "="*70)
    print("Starting Services...")
    print("="*70)

    # Start services
    services = {}

    try:
        if start_llm:
            services['LLM Server'] = start_llm_server()

        if start_sms:
            services['SMS Server'] = start_sms_server()

        if start_telegram_bot:
            services['Telegram Bot'] = start_telegram_server()

        # Remove failed services
        services = {k: v for k, v in services.items() if v is not None}

        if not services:
            print(f"\n{CROSS} No services started successfully. Exiting.")
            return

        # Print summary
        print_summary(services)

        # Wait for Ctrl+C
        try:
            while True:
                time.sleep(1)
                # Check if any process died
                for name, process in list(services.items()):
                    if process.poll() is not None:
                        print(f"\n{CROSS} {name} stopped unexpectedly")
                        del services[name]

                if not services:
                    print(f"\n{CROSS} All services stopped. Exiting.")
                    break

        except KeyboardInterrupt:
            print("\n\nShutting down...")

    finally:
        # Clean up
        for name, process in services.items():
            if process and process.poll() is None:
                print(f"Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()

        print(f"\n{CHECK} All services stopped")

if __name__ == "__main__":
    main()
