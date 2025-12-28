"""
AquaBrain pyRevit Routes Server Manager
=======================================
Starts and manages the pyRevit Routes HTTP server for remote Revit control.

The Routes API runs INSIDE Revit and exposes HTTP endpoints for:
- Script execution (/v1/execute)
- Model queries
- Element manipulation
- Transaction management

Usage:
    python start_routes.py [--host 0.0.0.0] [--port 31987]
"""

import subprocess
import sys
import time
import socket
import platform
from typing import Optional, Tuple
import threading


# Configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 31987
ROUTES_TIMEOUT = 30  # seconds to wait for server startup


def is_wsl() -> bool:
    """Check if running inside WSL."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except:
        return False


def get_windows_host() -> str:
    """Get Windows host IP from WSL."""
    if is_wsl():
        try:
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Extract gateway IP (Windows host)
            for line in result.stdout.split("\n"):
                if "default via" in line:
                    return line.split()[2]
        except:
            pass
    return "localhost"


def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is open and responding."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def start_routes_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    detached: bool = True
) -> Tuple[bool, str]:
    """
    Start the pyRevit Routes server via PowerShell.

    Args:
        host: Bind address (0.0.0.0 for all interfaces)
        port: HTTP port (default 31987)
        detached: Run in background process

    Returns:
        (success, message)
    """
    windows_host = get_windows_host()

    # Check if already running
    if check_port(windows_host, port):
        return True, f"Routes server already running on {windows_host}:{port}"

    # Build pyRevit command
    # Note: pyrevit routes requires Revit to be running with pyRevit loaded
    cmd = f"pyrevit routes start --host {host} --port {port} --all"

    if is_wsl():
        # Execute via PowerShell from WSL
        if detached:
            # Start as detached background process
            ps_cmd = f"""
            Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c', 'pyrevit routes start --host {host} --port {port} --all'
            """
            full_cmd = ["powershell.exe", "-Command", ps_cmd]
        else:
            full_cmd = ["powershell.exe", "-Command", cmd]
    else:
        # Direct execution on Windows
        if detached:
            full_cmd = f'start /b {cmd}'
        else:
            full_cmd = cmd

    try:
        if detached:
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                shell=isinstance(full_cmd, str)
            )

            # Wait for server to start
            for i in range(ROUTES_TIMEOUT):
                time.sleep(1)
                if check_port(windows_host, port):
                    return True, f"Routes server started on {windows_host}:{port}"

            return False, f"Routes server failed to start within {ROUTES_TIMEOUT}s (is Revit running with pyRevit?)"
        else:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=ROUTES_TIMEOUT,
                shell=isinstance(full_cmd, str)
            )
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr

    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def stop_routes_server() -> Tuple[bool, str]:
    """Stop the pyRevit Routes server."""
    cmd = "pyrevit routes stop"

    if is_wsl():
        full_cmd = ["powershell.exe", "-Command", cmd]
    else:
        full_cmd = cmd

    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=10,
            shell=isinstance(full_cmd, str)
        )
        return result.returncode == 0, result.stdout or result.stderr
    except Exception as e:
        return False, str(e)


def get_routes_status() -> dict:
    """Get current Routes server status."""
    windows_host = get_windows_host()
    port = DEFAULT_PORT

    is_running = check_port(windows_host, port)

    return {
        "running": is_running,
        "host": windows_host,
        "port": port,
        "endpoint": f"http://{windows_host}:{port}" if is_running else None,
        "wsl_mode": is_wsl()
    }


class RoutesServerManager:
    """
    Manages pyRevit Routes server lifecycle.
    Can be used as a context manager or standalone.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._started_by_us = False

    def __enter__(self):
        status = get_routes_status()
        if not status["running"]:
            success, msg = start_routes_server(self.host, self.port)
            if success:
                self._started_by_us = True
            else:
                raise RuntimeError(f"Failed to start Routes server: {msg}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._started_by_us:
            stop_routes_server()
        return False

    @property
    def endpoint(self) -> str:
        status = get_routes_status()
        return status.get("endpoint", f"http://localhost:{self.port}")

    def is_running(self) -> bool:
        return get_routes_status()["running"]


# Singleton manager for global access
_routes_manager: Optional[RoutesServerManager] = None


def get_routes_manager() -> RoutesServerManager:
    """Get or create the global Routes manager."""
    global _routes_manager
    if _routes_manager is None:
        _routes_manager = RoutesServerManager()
    return _routes_manager


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage pyRevit Routes server")
    parser.add_argument("action", choices=["start", "stop", "status"], nargs="?", default="start")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="HTTP port")

    args = parser.parse_args()

    if args.action == "start":
        print(f"Starting pyRevit Routes server on {args.host}:{args.port}...")
        success, msg = start_routes_server(args.host, args.port, detached=False)
        print(msg)
        sys.exit(0 if success else 1)

    elif args.action == "stop":
        print("Stopping pyRevit Routes server...")
        success, msg = stop_routes_server()
        print(msg)
        sys.exit(0 if success else 1)

    elif args.action == "status":
        status = get_routes_status()
        print(f"Routes Server Status:")
        print(f"  Running: {status['running']}")
        print(f"  Host: {status['host']}")
        print(f"  Port: {status['port']}")
        print(f"  WSL Mode: {status['wsl_mode']}")
        if status['endpoint']:
            print(f"  Endpoint: {status['endpoint']}")
