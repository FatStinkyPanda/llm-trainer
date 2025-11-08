"""
Port Utilities - Helper functions for port management
======================================================
"""

import socket


def is_port_available(port: int, host: str = '0.0.0.0') -> bool:
    """
    Check if a port is available for binding

    Args:
        port: Port number to check
        host: Host address to check

    Returns:
        True if port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return True
    except OSError:
        return False


def find_free_port(start_port: int, end_port: int, host: str = '0.0.0.0') -> int:
    """
    Find a free port in the given range

    Args:
        start_port: Start of port range (inclusive)
        end_port: End of port range (inclusive)
        host: Host address to check

    Returns:
        Free port number, or None if no free port found
    """
    for port in range(start_port, end_port + 1):
        if is_port_available(port, host):
            return port

    return None
