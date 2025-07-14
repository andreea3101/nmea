"""TCP output handler for NMEA sentences."""

import socket
import threading
import time
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .base import OutputHandler


@dataclass
class TCPOutputConfig:
    """Configuration for TCP output."""
    
    host: str = "0.0.0.0"
    port: int = 10110
    max_clients: int = 10
    client_timeout: float = 30.0  # seconds
    send_timeout: float = 5.0  # seconds


class TCPClient:
    """Represents a connected TCP client."""
    
    def __init__(self, socket: socket.socket, address: Tuple[str, int]):
        self.socket = socket
        self.address = address
        self.connected_time = time.time()
        self.last_activity = time.time()
        self.sentences_sent = 0
        self.errors = 0
    
    def send_sentence(self, sentence: str, timeout: float = 5.0) -> bool:
        """Send sentence to client with CRLF line ending."""
        try:
            self.socket.settimeout(timeout)
            # Ensure sentence is stripped of existing newlines and terminated with CRLF
            formatted_sentence = sentence.strip() + '\\r\\n'
            self.socket.sendall(formatted_sentence.encode('utf-8'))
            self.sentences_sent += 1
            self.last_activity = time.time()
            return True
        except (socket.timeout, socket.error, BrokenPipeError, ConnectionResetError):
            self.errors += 1
            return False
    
    def is_alive(self, timeout: float = 30.0) -> bool:
        """Check if client connection is still alive."""
        return (time.time() - self.last_activity) < timeout
    
    def close(self) -> None:
        """Close client connection."""
        try:
            self.socket.close()
        except Exception:
            pass
    
    def __str__(self) -> str:
        """String representation."""
        uptime = time.time() - self.connected_time
        return f"TCPClient({self.address[0]}:{self.address[1]}, {uptime:.1f}s, {self.sentences_sent} sent)"


@dataclass
class TCPServerInfo:
    """Information about the TCP server."""
    server_socket: Optional[socket.socket] = None
    clients: List[TCPClient] = None
    clients_lock: threading.Lock = None
    server_thread: Optional[threading.Thread] = None
    stop_event: threading.Event = None
    client_manager_thread: Optional[threading.Thread] = None

    def __post_init__(self):
        if self.clients is None:
            self.clients = []
        if self.clients_lock is None:
            self.clients_lock = threading.Lock()
        if self.stop_event is None:
            self.stop_event = threading.Event()


class TCPOutput(OutputHandler):
    """TCP server output handler for NMEA sentences."""

    def __init__(self, config: TCPOutputConfig):
        """Initialize TCP output handler."""
        super().__init__()
        self.config = config
        self.server_info: TCPServerInfo = TCPServerInfo()
    
    def start(self) -> None:
        """Start TCP server."""
        if self.is_running:
            return

        try:
            # Create server socket
            self.server_info.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_info.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_info.server_socket.bind((self.config.host, self.config.port))
            self.server_info.server_socket.listen(self.config.max_clients)
            self.server_info.server_socket.settimeout(1.0)  # Non-blocking accept

            self.is_running = True
            self.server_info.stop_event.clear()

            # Start server thread
            self.server_info.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_info.server_thread.start()

            # Start client manager thread
            self.server_info.client_manager_thread = threading.Thread(target=self._client_manager_loop,
                                                                      daemon=True)
            self.server_info.client_manager_thread.start()

            print(f"TCP server started on {self.config.host}:{self.config.port}")

        except Exception as e:
            self.is_running = False
            if self.server_info.server_socket:
                self.server_info.server_socket.close()
                self.server_info.server_socket = None
            raise RuntimeError(f"Failed to start TCP server: {e}")
    
    def stop(self) -> None:
        """Stop TCP server."""
        if not self.is_running:
            return

        self.is_running = False
        self.server_info.stop_event.set()

        # Close all client connections
        with self.server_info.clients_lock:
            for client in self.server_info.clients:
                client.close()
            self.server_info.clients.clear()

        # Close server socket
        if self.server_info.server_socket:
            self.server_info.server_socket.close()
            self.server_info.server_socket = None

        # Wait for threads to finish
        if self.server_info.server_thread:
            self.server_info.server_thread.join(timeout=5.0)

        if self.server_info.client_manager_thread:
            self.server_info.client_manager_thread.join(timeout=5.0)

        print("TCP server stopped")

    def send_sentence(self, sentence: str) -> bool:
        """Send NMEA sentence to all connected clients."""
        if not self.is_running:
            return False

        sent_count = 0
        failed_clients = []

        with self.server_info.clients_lock:
            for client in self.server_info.clients:
                if client.send_sentence(sentence, self.config.send_timeout):
                    sent_count += 1
                else:
                    failed_clients.append(client)

        # Remove failed clients
        if failed_clients:
            with self.server_info.clients_lock:
                for client in failed_clients:
                    if client in self.server_info.clients:
                        self.server_info.clients.remove(client)
                        client.close()

        if sent_count > 0:
            self.sentences_sent += 1
            return True

        return False

    def _server_loop(self) -> None:
        """Main server loop for accepting connections."""
        while self.is_running and not self.server_info.stop_event.is_set():
            try:
                if self.server_info.server_socket:
                    client_socket, client_address = self.server_info.server_socket.accept()

                    # Check client limit
                    with self.server_info.clients_lock:
                        if len(self.server_info.clients) >= self.config.max_clients:
                            client_socket.close()
                            continue

                        # Add new client
                        client = TCPClient(client_socket, client_address)
                        self.server_info.clients.append(client)
                        print(f"TCP client connected: {client_address[0]}:{client_address[1]}")

            except socket.timeout:
                continue  # Normal timeout, check stop condition
            except socket.error:
                if self.is_running:
                    print("TCP server socket error")
                break
            except Exception as e:
                if self.is_running:
                    print(f"TCP server error: {e}")
                time.sleep(1)

    def _client_manager_loop(self) -> None:
        """Client management loop for cleanup."""
        while self.is_running and not self.server_info.stop_event.is_set():
            try:
                time.sleep(5)  # Check every 5 seconds

                dead_clients = []
                with self.server_info.clients_lock:
                    for client in self.server_info.clients:
                        if not client.is_alive(self.config.client_timeout):
                            dead_clients.append(client)

                # Remove dead clients
                if dead_clients:
                    with self.server_info.clients_lock:
                        for client in dead_clients:
                            if client in self.server_info.clients:
                                self.server_info.clients.remove(client)
                                client.close()
                                print(f"TCP client disconnected: {client.address[0]}:{client.address[1]}")

            except Exception as e:
                if self.is_running:
                    print(f"TCP client manager error: {e}")
                time.sleep(1)

    def get_status(self) -> dict:
        """Get TCP output status."""
        status = super().get_status()

        with self.server_info.clients_lock:
            client_info = []
            for client in self.server_info.clients:
                client_info.append({
                    'address': f"{client.address[0]}:{client.address[1]}",
                    'connected_time': client.connected_time,
                    'sentences_sent': client.sentences_sent,
                    'errors': client.errors
                })

        status.update({
            'server_address': f"{self.config.host}:{self.config.port}",
            'client_count': len(client_info),
            'max_clients': self.config.max_clients,
            'clients': client_info
        })

        return status
    
    def __str__(self) -> str:
        """String representation."""
        status = "RUNNING" if self.is_running else "STOPPED"
        client_count = len(self.server_info.clients)
        return f"TCPOutput({status}, {self.config.host}:{self.config.port}, {client_count} clients, {self.sentences_sent} sentences)"

