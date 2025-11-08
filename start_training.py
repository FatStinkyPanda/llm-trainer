#!/usr/bin/env python3
"""
Quick Start Script for Training
================================

Starts all services and begins training in one command.
"""

import subprocess
import sys
import time
import signal
from pathlib import Path

# Windows-safe check and cross marks
CHECK = "[OK]"
CROSS = "[X]"

# Check and install dependencies FIRST (before other imports)
try:
    from check_dependencies import check_and_install_dependencies

    print("Checking dependencies before starting...")
    print("")

    if not check_and_install_dependencies(auto_install=True):
        print(f"{CROSS} Dependency installation failed.")
        print("Please install manually: pip install -r requirements.txt")
        sys.exit(1)

except ImportError:
    print("Warning: Dependency checker not found, skipping auto-install")
    print("")

# Now import other required modules
import json
import requests

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)


class ServiceManager:
    """Manages lifecycle of all training services"""

    def __init__(self):
        self.processes = []
        self.log_files = []  # Track log files to close later

    def start_service(self, script_name, service_name):
        """Start a service subprocess"""
        print(f"Starting {service_name}...")

        try:
            # On Windows, use CREATE_NO_WINDOW and DETACHED_PROCESS
            # to allow the server to run independently
            if sys.platform == 'win32':
                CREATE_NO_WINDOW = 0x08000000
                DETACHED_PROCESS = 0x00000008
                flags = CREATE_NO_WINDOW | DETACHED_PROCESS
            else:
                flags = 0

            process = subprocess.Popen(
                [sys.executable, "-u", script_name],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags
            )

            self.processes.append((service_name, process))
            print(f"{CHECK} {service_name} started (PID: {process.pid})")
            return process

        except Exception as e:
            print(f"{CROSS} Failed to start {service_name}: {e}")
            return None

    def wait_for_service(self, url, timeout=30):
        """Wait for a service to become available"""
        start_time = time.time()
        attempt = 0

        while time.time() - start_time < timeout:
            try:
                attempt += 1
                # Increased from 2 to 10 seconds to accommodate LLM Server's Ollama health check (5s timeout)
                response = requests.get(url, timeout=10)
                print(f"  Attempt {attempt}: HTTP {response.status_code}")
                if response.status_code == 200:
                    return True
            except Exception as e:
                print(f"  Attempt {attempt}: Connection failed - {type(e).__name__}")

            time.sleep(1)

        return False

    def stop_all(self):
        """Stop all services"""
        print("\nStopping all services...")

        for service_name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"{CHECK} {service_name} stopped")
            except:
                process.kill()
                print(f"{CHECK} {service_name} killed")

        # Close log files
        for log_file in self.log_files:
            try:
                log_file.close()
            except:
                pass


def main():
    """Main entry point"""
    print("="*70)
    print("CEREBRUM LLM Training - Quick Start")
    print("="*70)
    print("")

    manager = ServiceManager()

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\n\nShutdown requested...")
        manager.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Check if CEREBRUM is running
        print("Checking CEREBRUM...")
        if not manager.wait_for_service(config['cerebrum_url'] + '/api/status', timeout=5):
            print(f"{CROSS} CEREBRUM is not running!")
            print(f"  Please start CEREBRUM first: python launcher.py")
            print(f"  Expected at: {config['cerebrum_url']}")
            return

        print(f"{CHECK} CEREBRUM is running")
        print("")

        # Clear old port from config before starting LLM Server
        # This prevents race condition with stale port values
        if 'llm_server_port' in config:
            del config['llm_server_port']
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)

        # Start LLM Server
        llm_process = manager.start_service('llm_server.py', 'LLM Server')
        if not llm_process:
            return

        # Wait for LLM Server to write port to config (with retry)
        print("Waiting for LLM Server to initialize and write port to config...")
        llm_port = None

        for attempt in range(10):  # Try for up to 10 seconds
            time.sleep(1)

            # Check if process is still running
            if llm_process.poll() is not None:
                print(f"{CROSS} LLM Server process exited unexpectedly with code {llm_process.returncode}")
                print("  Check llm_server.py logs for details")
                manager.stop_all()
                return

            # Try to reload config
            try:
                with open('config.json', 'r') as f:
                    updated_config = json.load(f)
                    llm_port = updated_config.get('llm_server_port')

                if llm_port:
                    config.update(updated_config)
                    print(f"{CHECK} LLM Server selected port: {llm_port}")
                    break
            except Exception as e:
                print(f"Warning: Could not read config on attempt {attempt + 1}: {e}")

        if not llm_port:
            print(f"{CROSS} LLM Server did not write port to config after 10 seconds")
            print("  Check if llm_server.py is running and has write access to config.json")
            manager.stop_all()
            return

        # Give uvicorn adequate time to initialize after port selection
        print("Giving LLM Server time to initialize uvicorn...")
        time.sleep(6)  # Increased to 6 seconds for reliability

        # Wait for LLM Server
        print("Waiting for LLM Server...")
        # Use 127.0.0.1 instead of localhost to avoid IPv6 issues
        if not manager.wait_for_service(f"http://127.0.0.1:{llm_port}/"):
            print(f"{CROSS} LLM Server failed to start")
            print("  Check llm_server.log for details")
            manager.stop_all()
            return

        print(f"{CHECK} LLM Server ready")
        print("")

        # Start Middleware
        middleware_process = manager.start_service('middleware.py', 'Middleware')
        if not middleware_process:
            manager.stop_all()
            return

        time.sleep(3)  # Give it time to initialize

        # Wait for Middleware
        print("Waiting for Middleware...")
        # Use 127.0.0.1 instead of localhost to avoid IPv6 issues
        if not manager.wait_for_service(f"http://127.0.0.1:{config['middleware_port']}/api/status"):
            print(f"{CROSS} Middleware failed to start")
            manager.stop_all()
            return

        print(f"{CHECK} Middleware ready")
        print("")

        # Start training
        print("="*70)
        print("All services ready! Starting training...")
        print("="*70)
        print("")

        # Start training via middleware API
        response = requests.post(
            f"http://127.0.0.1:{config['middleware_port']}/api/training/start",
            json={
                "max_exchanges": 100,
                "delay": config['conversation_delay'],
                "topic_switch_interval": config['topic_switch_interval']
            }
        )

        if response.status_code == 200:
            print(f"{CHECK} Training started!")
            print("")
            print("Monitoring progress (Ctrl+C to stop)...")
            print("")

            # Monitor training
            while True:
                time.sleep(5)

                status_response = requests.get(
                    f"http://127.0.0.1:{config['middleware_port']}/api/training/status"
                )

                if status_response.status_code == 200:
                    status = status_response.json()

                    if not status.get('running'):
                        print("\n{CHECK} Training completed!")
                        print(f"  Total exchanges: {status.get('exchanges_completed')}")
                        break

                    topic = status.get('current_topic', 'N/A')
                    topic_short = topic[:50] + '...' if len(topic) > 50 else topic

                    print(f"Progress: {status.get('exchanges_completed')} exchanges | "
                          f"Topic: {topic_short}")

        else:
            print(f"{CROSS} Failed to start training: {response.text}")

    except KeyboardInterrupt:
        print("\n\nShutdown requested by user...")
    except Exception as e:
        print(f"\n{CROSS} Error: {e}")
    finally:
        manager.stop_all()

    print("\nDone!")


if __name__ == "__main__":
    main()
