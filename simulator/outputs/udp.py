"""UDP output handler for NMEA sentences."""

import socket
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .base import OutputHandler


@dataclass
class UDPOutputConfig:
    """Configuration for UDP output."""
    
    host: str = "255.255.255.255"  # Broadcast address
    port: int = 10111
    broadcast: bool = True
    multicast_group: Optional[str] = None  # e.g., "224.0.0.1"
    multicast_ttl: int = 1
    send_timeout: float = 1.0  # seconds


class UDPOutput(OutputHandler):
    """UDP broadcast/multicast output handler for NMEA sentences."""
    
    def __init__(self, config: UDPOutputConfig):
        """Initialize UDP output handler."""
        super().__init__()
        self.config = config
        self.socket: Optional[socket.socket] = None
        self.target_addresses: List[Tuple[str, int]] = []
        
        # Prepare target addresses
        if config.multicast_group:
            self.target_addresses.append((config.multicast_group, config.port))
        else:
            self.target_addresses.append((config.host, config.port))
    
    def start(self) -> None:
        """Start UDP output."""
        if self.is_running:
            return
        
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(self.config.send_timeout)
            
            # Configure socket for broadcast/multicast
            if self.config.broadcast and not self.config.multicast_group:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            if self.config.multicast_group:
                # Set multicast TTL
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.config.multicast_ttl)
                
                # Bind to any address for multicast
                self.socket.bind(('', 0))
            
            self.is_running = True
            
            if self.config.multicast_group:
                print(f"UDP multicast output started to {self.config.multicast_group}:{self.config.port}")
            else:
                print(f"UDP broadcast output started to {self.config.host}:{self.config.port}")
            
        except Exception as e:
            self.is_running = False
            if self.socket:
                self.socket.close()
                self.socket = None
            raise RuntimeError(f"Failed to start UDP output: {e}")
    
    def stop(self) -> None:
        """Stop UDP output."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.socket:
            self.socket.close()
            self.socket = None
        
        print("UDP output stopped")
    
    def send_sentence(self, sentence: str) -> bool:
        """Send NMEA sentence via UDP."""
        if not self.is_running or not self.socket:
            return False
        
        try:
            # Ensure sentence is stripped of existing newlines and terminated with CRLF
            formatted_sentence = sentence.strip() + '\\r\\n'
            sentence_bytes = formatted_sentence.encode('utf-8')
            sent_count = 0
            
            for address in self.target_addresses:
                try:
                    self.socket.sendto(sentence_bytes, address)
                    sent_count += 1
                except socket.error as e:
                    print(f"UDP send error to {address}: {e}")
            
            if sent_count > 0:
                self.sentences_sent += 1
                return True
            
            return False
            
        except Exception as e:
            print(f"UDP output error: {e}")
            return False
    
    def add_target(self, host: str, port: int) -> None:
        """Add additional UDP target."""
        target = (host, port)
        if target not in self.target_addresses:
            self.target_addresses.append(target)
    
    def remove_target(self, host: str, port: int) -> None:
        """Remove UDP target."""
        target = (host, port)
        if target in self.target_addresses:
            self.target_addresses.remove(target)
    
    def get_status(self) -> dict:
        """Get UDP output status."""
        status = super().get_status()
        
        status.update({
            'targets': [f"{addr[0]}:{addr[1]}" for addr in self.target_addresses],
            'broadcast': self.config.broadcast,
            'multicast_group': self.config.multicast_group,
            'multicast_ttl': self.config.multicast_ttl if self.config.multicast_group else None
        })
        
        return status
    
    def __str__(self) -> str:
        """String representation."""
        status = "RUNNING" if self.is_running else "STOPPED"
        targets = len(self.target_addresses)
        mode = "multicast" if self.config.multicast_group else "broadcast"
        return f"UDPOutput({status}, {mode}, {targets} targets, {self.sentences_sent} sentences)"

