"""Base output handler for NMEA sentences."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any


class OutputHandler(ABC):
    """Abstract base class for NMEA sentence output handlers."""
    
    def __init__(self):
        """Initialize output handler."""
        self.is_running = False
        self.sentences_sent = 0
        self.start_time: datetime = datetime.now()
        self.last_sentence_time: datetime = datetime.now()
    
    @abstractmethod
    def start(self) -> None:
        """Start the output handler."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the output handler and release resources."""
        pass
    
    @abstractmethod
    def send_sentence(self, sentence: str) -> bool:
        """
        Send an NMEA sentence.
        
        Args:
            sentence: NMEA sentence string
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get output handler status information."""
        now = datetime.now()
        uptime = (now - self.start_time).total_seconds() if self.is_running else 0
        
        return {
            'running': self.is_running,
            'sentences_sent': self.sentences_sent,
            'uptime_seconds': uptime,
            'last_sentence_time': self.last_sentence_time.isoformat(),
            'sentences_per_second': self.sentences_sent / max(1, uptime)
        }
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.sentences_sent = 0
        self.start_time = datetime.now()
        self.last_sentence_time = datetime.now()
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
