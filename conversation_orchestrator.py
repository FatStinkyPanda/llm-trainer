#!/usr/bin/env python3
"""
Conversation Orchestrator - CLI for Training Control
=====================================================

Simple command-line interface to start/stop/monitor training.
Communicates with middleware service.

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

import argparse
import json
import time
import requests
from datetime import datetime


def load_config():
    """Load configuration"""
    with open('config.json', 'r') as f:
        return json.load(f)


def check_services(config):
    """Check if all services are running"""
    print("Checking services...")

    # Check middleware
    try:
        response = requests.get(f"http://localhost:{config['middleware_port']}/api/status", timeout=5)
        if response.status_code == 200:
            print(f"{CHECK} Middleware is running")
            status = response.json()

            if status.get('cerebrum_connected'):
                print(f"{CHECK} CEREBRUM is accessible")
            else:
                print(f"{CROSS} CEREBRUM is not accessible")
                return False

            if status.get('llm_connected'):
                print(f"{CHECK} LLM Server is accessible")
            else:
                print(f"{CROSS} LLM Server is not accessible")
                return False

            return True
        else:
            print(f"{CROSS} Middleware returned error")
            return False
    except:
        print(f"{CROSS} Cannot connect to middleware")
        print(f"  Make sure middleware is running: python middleware.py")
        return False


def start_training(config, args):
    """Start conversation training"""
    print("\n" + "="*70)
    print("Starting Conversation Training")
    print("="*70)

    try:
        response = requests.post(
            f"http://localhost:{config['middleware_port']}/api/training/start",
            json={
                "max_exchanges": args.exchanges,
                "delay": args.delay,
                "topic_switch_interval": args.topic_interval
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print(f"{CHECK} Training started!")
            print(f"  Max exchanges: {args.exchanges}")
            print(f"  Delay: {args.delay}s")
            print(f"  Topic switch: every {args.topic_interval} messages")
            print(f"  Started at: {data.get('started_at')}")
            print("")
            print("Use Ctrl+C to stop monitoring (training continues in background)")
            print("")

            # Monitor progress
            try:
                while True:
                    time.sleep(5)

                    status_response = requests.get(
                        f"http://localhost:{config['middleware_port']}/api/training/status",
                        timeout=5
                    )

                    if status_response.status_code == 200:
                        status = status_response.json()

                        if not status.get('running'):
                            print("\n{CHECK} Training completed!")
                            print(f"  Total exchanges: {status.get('exchanges_completed')}")
                            break

                        print(f"Progress: {status.get('exchanges_completed')}/{args.exchanges} exchanges | "
                              f"Topic: {status.get('current_topic', 'N/A')[:40]}...")

            except KeyboardInterrupt:
                print("\n\nMonitoring stopped (training continues in background)")
                print("To stop training: python conversation_orchestrator.py --stop")

        elif response.status_code == 400:
            print(f"{CROSS} Training already running")
            print("  Stop it first: python conversation_orchestrator.py --stop")
        else:
            print(f"{CROSS} Error: {response.text}")

    except Exception as e:
        print(f"{CROSS} Error starting training: {e}")


def stop_training(config):
    """Stop conversation training"""
    print("\n" + "="*70)
    print("Stopping Training")
    print("="*70)

    try:
        response = requests.post(
            f"http://localhost:{config['middleware_port']}/api/training/stop",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print(f"{CHECK} Training stopped")
            print(f"  Exchanges completed: {data.get('exchanges_completed')}")
        elif response.status_code == 400:
            print(f"{CROSS} Training not running")
        else:
            print(f"{CROSS} Error: {response.text}")

    except Exception as e:
        print(f"{CROSS} Error stopping training: {e}")


def show_status(config):
    """Show training status"""
    try:
        response = requests.get(
            f"http://localhost:{config['middleware_port']}/api/training/status",
            timeout=5
        )

        if response.status_code == 200:
            status = response.json()

            print("\n" + "="*70)
            print("Training Status")
            print("="*70)
            print(f"Running: {status.get('running')}")
            print(f"Exchanges completed: {status.get('exchanges_completed')}")
            print(f"Current topic: {status.get('current_topic', 'N/A')}")
            print(f"Started at: {status.get('started_at', 'N/A')}")
            print(f"CEREBRUM connected: {status.get('cerebrum_connected')}")
            print(f"LLM connected: {status.get('llm_connected')}")
            print("="*70)

        else:
            print(f"{CROSS} Error getting status: {response.text}")

    except Exception as e:
        print(f"{CROSS} Error: {e}")


def show_log(config, limit):
    """Show conversation log"""
    try:
        response = requests.get(
            f"http://localhost:{config['middleware_port']}/api/training/log?limit={limit}",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()

            print("\n" + "="*70)
            print(f"Conversation Log (showing {data.get('showing')}/{data.get('total_exchanges')})")
            print("="*70)

            for i, exchange in enumerate(data.get('exchanges', []), 1):
                print(f"\n[{i}] {exchange.get('timestamp')}")
                print(f"LLM → CEREBRUM: {exchange.get('llm_to_cerebrum')}")
                print(f"CEREBRUM: {exchange.get('cerebrum_response')}")
                emotions = exchange.get('cerebrum_emotions', {})
                if emotions:
                    print(f"Emotions: {emotions}")
                print("-" * 70)

        else:
            print(f"{CROSS} Error getting log: {response.text}")

    except Exception as e:
        print(f"{CROSS} Error: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="CEREBRUM Conversation Training Orchestrator"
    )

    parser.add_argument('--start', action='store_true',
                       help='Start training')
    parser.add_argument('--stop', action='store_true',
                       help='Stop training')
    parser.add_argument('--status', action='store_true',
                       help='Show training status')
    parser.add_argument('--log', action='store_true',
                       help='Show conversation log')
    parser.add_argument('--exchanges', type=int, default=100,
                       help='Max exchanges (default: 100)')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between messages (default: 2.0s)')
    parser.add_argument('--topic-interval', type=int, default=10,
                       help='Messages before topic switch (default: 10)')
    parser.add_argument('--log-limit', type=int, default=20,
                       help='Number of log entries to show (default: 20)')

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Check services
    if not check_services(config):
        print("\n{CROSS} Services not ready. Please ensure:")
        print("  1. CEREBRUM is running (python launcher.py)")
        print("  2. LLM Server is running (python llm_server.py)")
        print("  3. Middleware is running (python middleware.py)")
        return

    # Execute command
    if args.start:
        start_training(config, args)
    elif args.stop:
        stop_training(config)
    elif args.status:
        show_status(config)
    elif args.log:
        show_log(config, args.log_limit)
    else:
        # Default: show status
        show_status(config)


if __name__ == "__main__":
    main()
