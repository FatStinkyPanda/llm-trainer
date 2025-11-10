#!/usr/bin/env python3
"""
LLM Trainer - Complete System Launcher
=======================================

Automatically manages all llm-trainer services:
- Detects and kills existing processes on required ports
- Starts services in correct order
- Monitors service health
- Provides unified control

Usage:
    python start_llm_trainer.py
"""

import sys
import os
import subprocess
import time
import json
import psutil
import signal
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Windows-safe symbols
CHECK = "[OK]"
CROSS = "[X]"
ARROW = "-->"
WARN = "[!]"

# Load configuration
def load_config():
    """Load configuration"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"{CROSS} Error loading config.json: {e}")
        sys.exit(1)

config = load_config()

# Service definitions
SERVICES = {
    'llm_server': {
        'script': 'llm_server.py',
        'port': config.get('llm_server_port', 8030),
        'port_range': config.get('llm_server_port_range', [8030, 8035]),
        'name': 'LLM Server',
        'required': True,
        'startup_delay': 5,
        'health_check': lambda port: check_http_service(f"http://localhost:{port}/")
    },
    'middleware': {
        'script': 'middleware.py',
        'port': config.get('middleware_port', 8032),
        'name': 'Middleware Service',
        'required': True,
        'startup_delay': 3,
        'health_check': lambda port: check_http_service(f"http://localhost:{port}/api/status")
    },
    'telegram': {
        'script': 'telegram_server.py',
        'port': config.get('telegram_server_port', 8041),
        'name': 'Telegram Bot',
        'required': False,
        'startup_delay': 3,
        'health_check': lambda port: check_http_service(f"http://localhost:{port}/")
    },
    'sms': {
        'script': 'sms_server.py',
        'port': config.get('sms_server_port', 8040),
        'name': 'SMS Server',
        'required': False,
        'startup_delay': 3,
        'health_check': lambda port: check_http_service(f"http://localhost:{port}/")
    }
}

# Running processes
running_processes: Dict[str, subprocess.Popen] = {}

def print_header():
    """Print startup header"""
    print("=" * 70)
    print("LLM Trainer - Complete System Launcher")
    print("=" * 70)
    print()

def print_section(title: str):
    """Print section header"""
    print()
    print("-" * 70)
    print(title)
    print("-" * 70)

def check_http_service(url: str, timeout: int = 2) -> bool:
    """Check if HTTP service is responding"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code in [200, 404]  # 404 is ok, means server is running
    except:
        return False

def find_process_on_port(port: int) -> Optional[psutil.Process]:
    """Find process using a specific port"""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                try:
                    return psutil.Process(conn.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None
    except (psutil.AccessDenied, PermissionError):
        return None

def is_llm_trainer_process(process: psutil.Process) -> bool:
    """Check if process is part of llm-trainer"""
    try:
        cmdline = ' '.join(process.cmdline()).lower()
        llm_trainer_scripts = [
            'llm_server.py',
            'middleware.py',
            'telegram_server.py',
            'sms_server.py'
        ]
        return any(script.lower() in cmdline for script in llm_trainer_scripts)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def kill_process(process: psutil.Process) -> bool:
    """Kill a process gracefully, then forcefully if needed"""
    try:
        pid = process.pid
        name = process.name()

        # Try graceful termination first
        process.terminate()

        # Wait up to 5 seconds for graceful shutdown
        try:
            process.wait(timeout=5)
            print(f"  {CHECK} Stopped {name} (PID {pid})")
            return True
        except psutil.TimeoutExpired:
            # Force kill if still running
            process.kill()
            process.wait(timeout=2)
            print(f"  {WARN} Force killed {name} (PID {pid})")
            return True

    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"  {CROSS} Failed to stop process: {e}")
        return False

def cleanup_existing_processes():
    """Find and kill existing llm-trainer processes"""
    print_section("Cleaning Up Existing Processes")

    killed_any = False

    # Check each service port
    for service_name, service_info in SERVICES.items():
        port = service_info['port']
        process = find_process_on_port(port)

        if process:
            if is_llm_trainer_process(process):
                print(f"  {ARROW} Found {service_info['name']} on port {port}")
                if kill_process(process):
                    killed_any = True
                    time.sleep(0.5)
            else:
                print(f"  {WARN} Port {port} is used by non-llm-trainer process: {process.name()}")
                print(f"      You may need to manually stop it or change the port")

    # Also check for any Python processes running llm-trainer scripts
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                if is_llm_trainer_process(proc):
                    # Check if we already killed this one
                    if proc.pid not in [p.pid for p in [] if hasattr(p, 'pid')]:
                        print(f"  {ARROW} Found stray llm-trainer process (PID {proc.pid})")
                        if kill_process(proc):
                            killed_any = True
                            time.sleep(0.5)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not killed_any:
        print(f"  {CHECK} No existing processes found")
    else:
        print(f"  {CHECK} Cleanup complete")
        time.sleep(2)  # Give OS time to free ports

def check_port_availability(port: int) -> bool:
    """Check if port is available"""
    process = find_process_on_port(port)
    return process is None

def check_dependencies():
    """Check if required dependencies are installed"""
    print_section("Checking Dependencies")

    required = ['fastapi', 'uvicorn', 'requests', 'pydantic', 'python-dotenv', 'psutil']
    optional = ['twilio', 'python-telegram-bot']

    all_good = True

    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"  {CHECK} {package}")
        except ImportError:
            print(f"  {CROSS} {package} (REQUIRED)")
            all_good = False

    for package in optional:
        try:
            __import__(package.replace('-', '_'))
            print(f"  {CHECK} {package}")
        except ImportError:
            print(f"  {WARN} {package} (optional)")

    if not all_good:
        print()
        print(f"{CROSS} Missing required dependencies!")
        print(f"  Run: pip install -r requirements.txt")
        sys.exit(1)

def check_configuration():
    """Check if services are configured"""
    print_section("Checking Configuration")

    # Check for .env file
    if Path('.env').exists():
        print(f"  {CHECK} .env file found")
    else:
        print(f"  {WARN} .env file not found (optional)")

    # Check Telegram configuration
    from dotenv import load_dotenv
    load_dotenv()

    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN') or config.get('telegram_bot_token')
    if telegram_token:
        print(f"  {CHECK} Telegram bot configured")
    else:
        print(f"  {WARN} Telegram bot not configured (will skip)")
        SERVICES['telegram']['required'] = False

    # Check SMS configuration
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID') or config.get('twilio_account_sid')
    twilio_token = os.getenv('TWILIO_AUTH_TOKEN') or config.get('twilio_auth_token')
    if twilio_sid and twilio_token:
        print(f"  {CHECK} SMS server configured")
    else:
        print(f"  {WARN} SMS server not configured (will skip)")
        SERVICES['sms']['required'] = False

    # Check OpenRouter/Ollama
    openrouter_key = os.getenv('OPENROUTER_API_KEY') or config.get('openrouter_api_key')
    if openrouter_key:
        print(f"  {CHECK} OpenRouter API key configured")
    else:
        print(f"  {WARN} OpenRouter API key not configured")

def start_service(service_name: str, service_info: Dict) -> Optional[subprocess.Popen]:
    """Start a service"""
    script = service_info['script']
    name = service_info['name']
    port = service_info['port']

    print(f"  {ARROW} Starting {name} (port {port})...")

    try:
        # Start process
        process = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )

        # Wait for startup
        startup_delay = service_info.get('startup_delay', 3)
        time.sleep(startup_delay)

        # Check if process is still running
        if process.poll() is not None:
            print(f"  {CROSS} {name} failed to start")
            return None

        # Check health if available
        health_check = service_info.get('health_check')
        if health_check:
            if health_check(port):
                print(f"  {CHECK} {name} started successfully (PID {process.pid})")
            else:
                print(f"  {WARN} {name} started but health check failed (PID {process.pid})")
        else:
            print(f"  {CHECK} {name} started (PID {process.pid})")

        return process

    except Exception as e:
        print(f"  {CROSS} Failed to start {name}: {e}")
        return None

def start_all_services():
    """Start all services in correct order"""
    print_section("Starting Services")

    # Start order: LLM Server -> Middleware -> Telegram/SMS (parallel)
    start_order = ['llm_server', 'middleware', 'telegram', 'sms']

    for service_name in start_order:
        service_info = SERVICES[service_name]

        # Skip if not required and not configured
        if not service_info['required']:
            # Double check configuration
            if service_name == 'telegram':
                from dotenv import load_dotenv
                load_dotenv()
                if not (os.getenv('TELEGRAM_BOT_TOKEN') or config.get('telegram_bot_token')):
                    print(f"  {WARN} Skipping {service_info['name']} (not configured)")
                    continue
            elif service_name == 'sms':
                from dotenv import load_dotenv
                load_dotenv()
                twilio_sid = os.getenv('TWILIO_ACCOUNT_SID') or config.get('twilio_account_sid')
                twilio_token = os.getenv('TWILIO_AUTH_TOKEN') or config.get('twilio_auth_token')
                if not (twilio_sid and twilio_token):
                    print(f"  {WARN} Skipping {service_info['name']} (not configured)")
                    continue

        # Check port availability
        port = service_info['port']
        if not check_port_availability(port):
            print(f"  {CROSS} Port {port} is still in use!")
            if service_info['required']:
                print(f"      Cannot start {service_info['name']} - exiting")
                cleanup_on_exit()
                sys.exit(1)
            else:
                print(f"      Skipping {service_info['name']}")
                continue

        # Start service
        process = start_service(service_name, service_info)
        if process:
            running_processes[service_name] = process
        elif service_info['required']:
            print(f"  {CROSS} Required service {service_info['name']} failed to start - exiting")
            cleanup_on_exit()
            sys.exit(1)

def print_status():
    """Print status of all services"""
    print_section("Service Status")

    for service_name, service_info in SERVICES.items():
        name = service_info['name']
        port = service_info['port']

        if service_name in running_processes:
            process = running_processes[service_name]
            if process.poll() is None:
                print(f"  {CHECK} {name:20} - Running (PID {process.pid}, Port {port})")
            else:
                print(f"  {CROSS} {name:20} - Stopped unexpectedly")
        else:
            print(f"  {WARN} {name:20} - Not started")

def print_urls():
    """Print service URLs"""
    print_section("Service URLs")

    if 'llm_server' in running_processes:
        port = SERVICES['llm_server']['port']
        print(f"  LLM Server:        http://localhost:{port}")
        print(f"    API Docs:        http://localhost:{port}/docs")

    if 'middleware' in running_processes:
        port = SERVICES['middleware']['port']
        print(f"  Middleware:        http://localhost:{port}")
        print(f"    Status:          http://localhost:{port}/api/status")
        print(f"    API Docs:        http://localhost:{port}/docs")

    if 'telegram' in running_processes:
        port = SERVICES['telegram']['port']
        print(f"  Telegram Bot:      http://localhost:{port}")
        print(f"    Status:          http://localhost:{port}/telegram/status")

    if 'sms' in running_processes:
        port = SERVICES['sms']['port']
        print(f"  SMS Server:        http://localhost:{port}")
        print(f"    Status:          http://localhost:{port}/sms/status")

def monitor_services():
    """Monitor running services and handle crashes"""
    print()
    print("=" * 70)
    print("All services started successfully!")
    print("=" * 70)
    print()
    print("Press Ctrl+C to stop all services")
    print()

    try:
        while True:
            time.sleep(5)

            # Check if any process died
            for service_name, process in list(running_processes.items()):
                if process.poll() is not None:
                    service_info = SERVICES[service_name]
                    print(f"\n{CROSS} {service_info['name']} stopped unexpectedly!")

                    if service_info['required']:
                        print(f"  Required service failed - stopping all services")
                        cleanup_on_exit()
                        sys.exit(1)
                    else:
                        del running_processes[service_name]

            # Exit if all processes are dead
            if not running_processes:
                print(f"\n{CROSS} All services stopped - exiting")
                break

    except KeyboardInterrupt:
        print("\n\nShutdown requested...")

def cleanup_on_exit():
    """Cleanup function to stop all services"""
    print_section("Stopping Services")

    for service_name, process in running_processes.items():
        service_info = SERVICES[service_name]
        if process.poll() is None:
            print(f"  {ARROW} Stopping {service_info['name']}...")
            try:
                if sys.platform == 'win32':
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    process.terminate()

                process.wait(timeout=5)
                print(f"  {CHECK} {service_info['name']} stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"  {WARN} {service_info['name']} force killed")
            except Exception as e:
                print(f"  {CROSS} Error stopping {service_info['name']}: {e}")

    print()
    print(f"{CHECK} All services stopped")

def main():
    """Main launcher function"""
    print_header()

    # Step 1: Check dependencies
    check_dependencies()

    # Step 2: Check configuration
    check_configuration()

    # Step 3: Cleanup existing processes
    cleanup_existing_processes()

    # Step 4: Start all services
    start_all_services()

    # Step 5: Print status
    print_status()
    print_urls()

    # Step 6: Monitor services
    monitor_services()

    # Step 7: Cleanup on exit
    cleanup_on_exit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
        cleanup_on_exit()
    except Exception as e:
        print(f"\n{CROSS} Fatal error: {e}")
        cleanup_on_exit()
        sys.exit(1)
