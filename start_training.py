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

# Check and install dependencies FIRST (before other imports)
try:
    from check_dependencies import check_and_install_dependencies

    print("Checking dependencies before starting...")
    print("")

    if not check_and_install_dependencies(auto_install=True):
        print("✗ Dependency installation failed.")
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

    def start_service(self, script_name, service_name):
        """Start a service subprocess"""
        print(f"Starting {service_name}...")

        try:
            process = subprocess.Popen(
                [sys.executable, script_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            self.processes.append((service_name, process))
            print(f"✓ {service_name} started (PID: {process.pid})")
            return process

        except Exception as e:
            print(f"✗ Failed to start {service_name}: {e}")
            return None

    def wait_for_service(self, url, timeout=30):
        """Wait for a service to become available"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    return True
            except:
                pass

            time.sleep(1)

        return False

    def stop_all(self):
        """Stop all services"""
        print("\nStopping all services...")

        for service_name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✓ {service_name} stopped")
            except:
                process.kill()
                print(f"✓ {service_name} killed")


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
            print("✗ CEREBRUM is not running!")
            print(f"  Please start CEREBRUM first: python launcher.py")
            print(f"  Expected at: {config['cerebrum_url']}")
            return

        print("✓ CEREBRUM is running")
        print("")

        # Start LLM Server
        llm_process = manager.start_service('llm_server.py', 'LLM Server')
        if not llm_process:
            return

        time.sleep(3)  # Give it time to initialize

        # Wait for LLM Server
        print("Waiting for LLM Server...")
        if not manager.wait_for_service(f"http://localhost:{config['llm_server_port']}/"):
            print("✗ LLM Server failed to start")
            manager.stop_all()
            return

        print("✓ LLM Server ready")
        print("")

        # Start Middleware
        middleware_process = manager.start_service('middleware.py', 'Middleware')
        if not middleware_process:
            manager.stop_all()
            return

        time.sleep(3)  # Give it time to initialize

        # Wait for Middleware
        print("Waiting for Middleware...")
        if not manager.wait_for_service(f"http://localhost:{config['middleware_port']}/api/status"):
            print("✗ Middleware failed to start")
            manager.stop_all()
            return

        print("✓ Middleware ready")
        print("")

        # Start training
        print("="*70)
        print("All services ready! Starting training...")
        print("="*70)
        print("")

        # Start training via middleware API
        response = requests.post(
            f"http://localhost:{config['middleware_port']}/api/training/start",
            json={
                "max_exchanges": 100,
                "delay": config['conversation_delay'],
                "topic_switch_interval": config['topic_switch_interval']
            }
        )

        if response.status_code == 200:
            print("✓ Training started!")
            print("")
            print("Monitoring progress (Ctrl+C to stop)...")
            print("")

            # Monitor training
            while True:
                time.sleep(5)

                status_response = requests.get(
                    f"http://localhost:{config['middleware_port']}/api/training/status"
                )

                if status_response.status_code == 200:
                    status = status_response.json()

                    if not status.get('running'):
                        print("\n✓ Training completed!")
                        print(f"  Total exchanges: {status.get('exchanges_completed')}")
                        break

                    topic = status.get('current_topic', 'N/A')
                    topic_short = topic[:50] + '...' if len(topic) > 50 else topic

                    print(f"Progress: {status.get('exchanges_completed')} exchanges | "
                          f"Topic: {topic_short}")

        else:
            print(f"✗ Failed to start training: {response.text}")

    except KeyboardInterrupt:
        print("\n\nShutdown requested by user...")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        manager.stop_all()

    print("\nDone!")


if __name__ == "__main__":
    main()
