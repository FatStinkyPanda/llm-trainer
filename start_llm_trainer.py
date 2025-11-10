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
import traceback
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Windows-safe symbols
CHECK = "[OK]"
CROSS = "[X]"
ARROW = "-->"
WARN = "[!]"

# MCP Logging Configuration
MCP_LOGGING_ENABLED = True
MCP_LOG_FILE = "launcher_mcp_logs.jsonl"  # Structured logs for MCP ingestion

class LauncherLogger:
    """Integrated logging with MCP OpenMemory logging service

    This logger writes structured logs to a JSONL file that can be ingested
    by Claude's MCP tools. The logs follow the MCP autonomous naming system
    and can be imported into OpenMemory for analysis.

    Note: This is a standalone Python script, so it can't directly call MCP tools.
    Instead, it writes structured logs that Claude can import via MCP tools.
    """

    def __init__(self, project_name: str = "llm-trainer"):
        self.project_name = project_name
        self.source = "start_llm_trainer.py"
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.mcp_log_path = Path(MCP_LOG_FILE)

    def _log_to_mcp(self, level: str, category: str, message: str, context: Dict = None):
        """Write structured log entry for MCP ingestion

        Logs are written to a JSONL file (one JSON object per line) that can be
        easily parsed and imported by Claude's MCP tools for analysis.

        Args:
            level: trace, debug, info, warn, error, fatal
            category: main, error, ai-agent, api, debug, system, performance
            message: Log message
            context: Additional context data
        """
        if not MCP_LOGGING_ENABLED:
            return

        try:
            # Prepare log entry with full context
            log_entry = {
                "level": level,
                "category": category,
                "source": self.source,
                "message": message,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "project": self.project_name,
                "context": context or {}
            }

            # Write to JSONL file (one JSON object per line)
            # This format is easy to parse and can be ingested by MCP tools
            with open(self.mcp_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception:
            # Silent fail - don't disrupt launcher if logging fails
            pass

    def info(self, message: str, context: Dict = None, category: str = "system"):
        """Log info level message"""
        self._log_to_mcp("info", category, message, context)

    def warn(self, message: str, context: Dict = None, category: str = "system"):
        """Log warning level message"""
        self._log_to_mcp("warn", category, message, context)

    def error(self, message: str, context: Dict = None, category: str = "error"):
        """Log error level message"""
        self._log_to_mcp("error", category, message, context)

    def fatal(self, message: str, context: Dict = None, category: str = "error"):
        """Log fatal level message"""
        self._log_to_mcp("fatal", category, message, context)

    def debug(self, message: str, context: Dict = None, category: str = "debug"):
        """Log debug level message"""
        self._log_to_mcp("debug", category, message, context)

    def trace(self, message: str, context: Dict = None, category: str = "debug"):
        """Log trace level message"""
        self._log_to_mcp("trace", category, message, context)

    def performance(self, message: str, duration: float, context: Dict = None):
        """Log performance metric"""
        ctx = context or {}
        ctx["duration_ms"] = duration * 1000
        self._log_to_mcp("info", "performance", message, ctx)

    def exception(self, message: str, exc: Exception, context: Dict = None):
        """Log exception with full traceback"""
        ctx = context or {}
        ctx["exception_type"] = type(exc).__name__
        ctx["exception_message"] = str(exc)
        ctx["traceback"] = traceback.format_exc()
        self._log_to_mcp("error", "error", message, ctx)

# Initialize logger
logger = LauncherLogger()

# Load configuration
def load_config():
    """Load configuration"""
    start_time = time.time()
    try:
        logger.debug("Loading configuration from config.json")
        with open('config.json', 'r') as f:
            config_data = json.load(f)

        duration = time.time() - start_time
        logger.performance("Configuration loaded", duration, {"config_keys": list(config_data.keys())})
        logger.info("Configuration loaded successfully", {"num_keys": len(config_data)})
        return config_data
    except FileNotFoundError as e:
        logger.fatal("Configuration file not found", {"error": str(e), "file": "config.json"})
        print(f"{CROSS} Error loading config.json: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.fatal("Invalid JSON in configuration file", {"error": str(e), "file": "config.json"})
        print(f"{CROSS} Error loading config.json: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error loading configuration", e)
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
        'health_check': lambda port: check_http_service(f"http://localhost:{port}/health")
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

def check_http_service(url: str, timeout: int = 5) -> bool:
    """Check if HTTP service is responding

    Uses 5 second timeout to allow services time to fully start up.
    Returns True if service responds with any HTTP status (even 404).
    """
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

def install_dependencies():
    """Install missing dependencies automatically"""
    print(f"  {ARROW} Installing missing dependencies...")
    start_time = time.time()

    logger.info("Starting automatic dependency installation", {"source_file": "requirements.txt"})

    try:
        # Install all requirements from requirements.txt
        logger.debug("Running pip install command", {
            "command": f"{sys.executable} -m pip install -r requirements.txt",
            "timeout": 300
        })

        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--quiet'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"  {CHECK} Dependencies installed successfully")
            logger.performance("Dependencies installed successfully", duration, {
                "return_code": result.returncode,
                "stdout_length": len(result.stdout)
            })
            return True
        else:
            print(f"  {CROSS} Failed to install dependencies:")
            print(f"      {result.stderr}")
            logger.error("Dependency installation failed", {
                "return_code": result.returncode,
                "stderr": result.stderr,
                "stdout": result.stdout,
                "duration": duration
            })
            return False

    except subprocess.TimeoutExpired as e:
        print(f"  {CROSS} Installation timed out")
        logger.error("Dependency installation timed out", {
            "timeout": 300,
            "duration": time.time() - start_time
        })
        return False
    except Exception as e:
        print(f"  {CROSS} Error installing dependencies: {e}")
        logger.exception("Unexpected error during dependency installation", e, {
            "duration": time.time() - start_time
        })
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print_section("Checking Dependencies")
    start_time = time.time()

    logger.info("Starting dependency check", {"category": "system"})

    required = ['fastapi', 'uvicorn', 'requests', 'pydantic', 'python-dotenv', 'psutil']
    optional = ['twilio', 'python-telegram-bot']

    # Mapping of package names to import names (when they differ)
    import_names = {
        'python-dotenv': 'dotenv',
        'python-telegram-bot': 'telegram',
        'python-multipart': 'multipart'
    }

    missing_required = []
    missing_optional = []

    for package in required:
        try:
            # Get the correct import name
            import_name = import_names.get(package, package.replace('-', '_'))
            __import__(import_name)
            print(f"  {CHECK} {package}")
            logger.debug(f"Package {package} found", {"package": package, "import_name": import_name})
        except ImportError as e:
            print(f"  {CROSS} {package} (REQUIRED - missing)")
            missing_required.append(package)
            logger.warn(f"Required package {package} missing", {
                "package": package,
                "import_name": import_name,
                "error": str(e)
            })

    for package in optional:
        try:
            # Get the correct import name
            import_name = import_names.get(package, package.replace('-', '_'))
            __import__(import_name)
            print(f"  {CHECK} {package}")
            logger.debug(f"Optional package {package} found", {"package": package, "import_name": import_name})
        except ImportError as e:
            print(f"  {WARN} {package} (optional - missing)")
            missing_optional.append(package)
            logger.debug(f"Optional package {package} missing", {
                "package": package,
                "import_name": import_name,
                "error": str(e)
            })

    if missing_required or missing_optional:
        print()
        if missing_required:
            print(f"{WARN} Found {len(missing_required)} missing required dependencies")
            logger.warn("Missing required dependencies", {
                "missing_packages": missing_required,
                "count": len(missing_required)
            })
        if missing_optional:
            print(f"{WARN} Found {len(missing_optional)} missing optional dependencies")
            logger.info("Missing optional dependencies", {
                "missing_packages": missing_optional,
                "count": len(missing_optional)
            })

        print()
        print(f"{ARROW} Attempting automatic installation...")
        logger.info("Attempting automatic dependency installation")

        if install_dependencies():
            print(f"{CHECK} All dependencies installed!")
            print()

            # Verify installation
            print(f"{ARROW} Verifying installation...")
            logger.debug("Verifying installed dependencies")

            # Mapping of package names to import names
            import_names = {
                'python-dotenv': 'dotenv',
                'python-telegram-bot': 'telegram',
                'python-multipart': 'multipart'
            }

            all_good = True
            verified = []
            still_missing = []

            for package in missing_required:
                try:
                    import_name = import_names.get(package, package.replace('-', '_'))
                    __import__(import_name)
                    print(f"  {CHECK} {package} verified")
                    verified.append(package)
                    logger.debug(f"Package {package} verified after installation", {"package": package})
                except ImportError as e:
                    print(f"  {CROSS} {package} still missing")
                    still_missing.append(package)
                    logger.error(f"Package {package} still missing after installation", {
                        "package": package,
                        "error": str(e)
                    })
                    all_good = False

            duration = time.time() - start_time
            logger.performance("Dependency check completed", duration, {
                "verified": verified,
                "still_missing": still_missing,
                "success": all_good
            })

            if not all_good:
                print()
                print(f"{CROSS} Some dependencies failed to install!")
                print(f"  Please manually run: pip install -r requirements.txt")
                logger.fatal("Dependency installation verification failed", {
                    "still_missing": still_missing,
                    "duration": duration
                })
                sys.exit(1)
        else:
            print()
            print(f"{CROSS} Automatic installation failed!")
            print(f"  Please manually run: pip install -r requirements.txt")
            logger.fatal("Automatic dependency installation failed")
            sys.exit(1)
    else:
        duration = time.time() - start_time
        logger.performance("All dependencies satisfied", duration, {
            "required_count": len(required),
            "optional_count": len(optional)
        })

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
    start_time = time.time()

    print(f"  {ARROW} Starting {name} (port {port})...")
    logger.info(f"Starting service: {name}", {
        "service": service_name,
        "script": script,
        "port": port,
        "required": service_info['required']
    })

    try:
        # Start process
        logger.debug(f"Launching {name} process", {
            "command": f"{sys.executable} {script}",
            "service": service_name
        })

        process = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )

        logger.debug(f"{name} process created", {
            "pid": process.pid,
            "service": service_name
        })

        # Wait for startup
        startup_delay = service_info.get('startup_delay', 3)
        logger.trace(f"Waiting {startup_delay}s for {name} startup", {
            "delay": startup_delay,
            "service": service_name
        })
        time.sleep(startup_delay)

        # Check if process is still running
        if process.poll() is not None:
            print(f"  {CROSS} {name} failed to start")
            # Capture error output
            stdout, stderr = process.communicate(timeout=1)
            logger.error(f"Service {name} failed to start", {
                "service": service_name,
                "pid": process.pid,
                "return_code": process.returncode,
                "stdout": stdout[:500] if stdout else None,
                "stderr": stderr[:500] if stderr else None,
                "duration": time.time() - start_time
            })
            return None

        # Check health if available
        health_check = service_info.get('health_check')
        if health_check:
            logger.debug(f"Running health check for {name}", {"service": service_name, "port": port})
            health_ok = health_check(port)

            if health_ok:
                print(f"  {CHECK} {name} started successfully (PID {process.pid})")
                duration = time.time() - start_time
                logger.performance(f"Service {name} started successfully", duration, {
                    "service": service_name,
                    "pid": process.pid,
                    "port": port,
                    "health_check_passed": True
                })
            else:
                print(f"  {WARN} {name} started but health check failed (PID {process.pid})")
                logger.warn(f"Service {name} health check failed", {
                    "service": service_name,
                    "pid": process.pid,
                    "port": port,
                    "duration": time.time() - start_time
                })
        else:
            print(f"  {CHECK} {name} started (PID {process.pid})")
            duration = time.time() - start_time
            logger.performance(f"Service {name} started", duration, {
                "service": service_name,
                "pid": process.pid,
                "port": port,
                "health_check": False
            })

        return process

    except Exception as e:
        print(f"  {CROSS} Failed to start {name}: {e}")
        logger.exception(f"Exception starting service {name}", e, {
            "service": service_name,
            "script": script,
            "port": port,
            "duration": time.time() - start_time
        })
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

            # Special handling for LLM server: reload config to get dynamically assigned port
            if service_name == 'llm_server':
                logger.debug("Reloading config after LLM server startup to get assigned port")
                time.sleep(2)  # Give LLM server time to write config
                try:
                    with open('config.json', 'r') as f:
                        updated_config = json.load(f)
                    new_port = updated_config.get('llm_server_port')
                    if new_port and new_port != service_info['port']:
                        logger.info(f"LLM server port updated: {service_info['port']} -> {new_port}", {
                            "old_port": service_info['port'],
                            "new_port": new_port
                        })
                        # Update global config and service info
                        config['llm_server_port'] = new_port
                        SERVICES['llm_server']['port'] = new_port
                        print(f"  {ARROW} Port updated to {new_port}")
                except Exception as e:
                    logger.error(f"Failed to reload config after LLM server start: {e}")

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

    logger.info("Service monitoring started", {
        "monitoring_services": list(running_processes.keys()),
        "total_services": len(running_processes)
    })

    # Display web interface URL prominently
    if 'middleware' in running_processes:
        middleware_port = SERVICES['middleware']['port']
        print("=" * 70)
        print("WEB INTERFACE AVAILABLE")
        print("=" * 70)
        print()
        print(f"  Open your web browser and navigate to:")
        print()
        print(f"    http://localhost:{middleware_port}")
        print()
        print(f"  Complete control panel with:")
        print(f"    - System status monitoring")
        print(f"    - Training configuration")
        print(f"    - Messaging setup (Telegram/SMS)")
        print(f"    - User management")
        print()
        print("=" * 70)
        print()

        logger.info("Web interface available", {
            "url": f"http://localhost:{middleware_port}",
            "port": middleware_port
        })

    print("Press Ctrl+C to stop all services")
    print()

    monitor_start = time.time()
    health_check_count = 0

    try:
        while True:
            time.sleep(5)
            health_check_count += 1

            logger.trace(f"Health check #{health_check_count}", {
                "running_services": list(running_processes.keys()),
                "uptime": time.time() - monitor_start
            })

            # Check if any process died
            for service_name, process in list(running_processes.items()):
                if process.poll() is not None:
                    service_info = SERVICES[service_name]
                    print(f"\n{CROSS} {service_info['name']} stopped unexpectedly!")

                    # Get exit information
                    return_code = process.returncode
                    logger.error(f"Service {service_info['name']} crashed", {
                        "service": service_name,
                        "pid": process.pid,
                        "return_code": return_code,
                        "uptime": time.time() - monitor_start,
                        "health_checks_completed": health_check_count
                    })

                    if service_info['required']:
                        print(f"  Required service failed - stopping all services")
                        logger.fatal(f"Required service {service_info['name']} failed - shutting down", {
                            "service": service_name,
                            "return_code": return_code
                        })
                        cleanup_on_exit()
                        sys.exit(1)
                    else:
                        logger.warn(f"Optional service {service_info['name']} stopped", {
                            "service": service_name,
                            "continuing": True
                        })
                        del running_processes[service_name]

            # Exit if all processes are dead
            if not running_processes:
                print(f"\n{CROSS} All services stopped - exiting")
                logger.error("All services stopped unexpectedly", {
                    "uptime": time.time() - monitor_start,
                    "health_checks": health_check_count
                })
                break

    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
        logger.info("Monitoring interrupted by user", {
            "uptime": time.time() - monitor_start,
            "health_checks": health_check_count
        })

def cleanup_on_exit():
    """Cleanup function to stop all services"""
    print_section("Stopping Services")
    cleanup_start = time.time()

    logger.info("Starting cleanup process", {
        "services_to_stop": list(running_processes.keys()),
        "total_services": len(running_processes)
    })

    stopped_count = 0
    force_killed_count = 0
    errors = []

    for service_name, process in running_processes.items():
        service_info = SERVICES[service_name]
        if process.poll() is None:
            service_stop_start = time.time()
            print(f"  {ARROW} Stopping {service_info['name']}...")
            logger.debug(f"Stopping service {service_info['name']}", {
                "service": service_name,
                "pid": process.pid
            })

            try:
                if sys.platform == 'win32':
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    process.terminate()

                process.wait(timeout=5)
                stop_duration = time.time() - service_stop_start
                print(f"  {CHECK} {service_info['name']} stopped")
                logger.info(f"Service {service_info['name']} stopped gracefully", {
                    "service": service_name,
                    "pid": process.pid,
                    "stop_duration": stop_duration
                })
                stopped_count += 1

            except subprocess.TimeoutExpired:
                process.kill()
                stop_duration = time.time() - service_stop_start
                print(f"  {WARN} {service_info['name']} force killed")
                logger.warn(f"Service {service_info['name']} force killed after timeout", {
                    "service": service_name,
                    "pid": process.pid,
                    "timeout": 5,
                    "stop_duration": stop_duration
                })
                force_killed_count += 1

            except Exception as e:
                stop_duration = time.time() - service_stop_start
                print(f"  {CROSS} Error stopping {service_info['name']}: {e}")
                logger.error(f"Error stopping service {service_info['name']}", {
                    "service": service_name,
                    "pid": process.pid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "stop_duration": stop_duration
                })
                errors.append({"service": service_name, "error": str(e)})

    cleanup_duration = time.time() - cleanup_start
    print()
    print(f"{CHECK} All services stopped")

    logger.performance("Cleanup completed", cleanup_duration, {
        "total_services": len(running_processes),
        "stopped_gracefully": stopped_count,
        "force_killed": force_killed_count,
        "errors": len(errors),
        "error_details": errors if errors else None
    })
    logger.info("All services stopped", {
        "total_services": len(running_processes),
        "cleanup_duration": cleanup_duration
    })

def main():
    """Main launcher function"""
    launch_start_time = time.time()
    logger.info("=== LLM Trainer System Launcher Started ===", {
        "python_version": sys.version,
        "platform": sys.platform,
        "session_id": logger.session_id
    })

    print_header()

    try:
        # Step 1: Check dependencies
        logger.info("Step 1: Checking dependencies")
        check_dependencies()

        # Step 2: Check configuration
        logger.info("Step 2: Checking configuration")
        check_configuration()

        # Step 3: Cleanup existing processes
        logger.info("Step 3: Cleaning up existing processes")
        cleanup_existing_processes()

        # Step 4: Start all services
        logger.info("Step 4: Starting all services")
        start_all_services()

        # Step 5: Print status
        logger.info("Step 5: Displaying service status")
        print_status()
        print_urls()

        launch_duration = time.time() - launch_start_time
        logger.performance("System launcher completed", launch_duration, {
            "services_started": len(running_processes),
            "service_list": list(running_processes.keys())
        })
        logger.info("All services started successfully", {
            "total_services": len(running_processes),
            "startup_duration": launch_duration
        })

        # Step 6: Monitor services
        logger.info("Step 6: Starting service monitoring")
        monitor_services()

        # Step 7: Cleanup on exit
        logger.info("Step 7: Cleaning up")
        cleanup_on_exit()

        total_duration = time.time() - launch_start_time
        logger.info("=== LLM Trainer System Launcher Exited ===", {
            "total_duration": total_duration,
            "exit_reason": "normal"
        })

    except Exception as e:
        logger.exception("Fatal error in main launcher", e, {
            "duration": time.time() - launch_start_time
        })
        raise

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
        logger.info("Shutdown requested by user (Ctrl+C)", {"category": "system"})
        cleanup_on_exit()
        logger.info("=== LLM Trainer System Launcher Exited ===", {"exit_reason": "user_interrupt"})
    except Exception as e:
        print(f"\n{CROSS} Fatal error: {e}")
        logger.fatal("Fatal unhandled exception", {
            "error": str(e),
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc()
        })
        cleanup_on_exit()
        logger.info("=== LLM Trainer System Launcher Exited ===", {"exit_reason": "fatal_error"})
        sys.exit(1)
