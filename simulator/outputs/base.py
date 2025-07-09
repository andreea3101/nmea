"""Base output handler for NMEA sentences."""

from abc import ABC, abstractmethod
import time  # Changed from datetime to time
from typing import Dict, Any


class OutputHandler(ABC):
    """Abstract base class for NMEA sentence output handlers."""

    def __init__(self):
        """Initialize output handler."""
        self.is_running = False
        self.sentences_sent = 0
        # Changed to use time.time() for consistency with other modules
        self.start_time: float = time.time()
        self.last_sentence_time: float = time.time()

    @abstractmethod
    def start(self) -> None:
        """Start the output handler."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the output handler."""

    @abstractmethod
    def send_sentence(self, sentence: str) -> bool:
        """
        Send an NMEA sentence.

        Args:
            sentence: NMEA sentence string

        Returns:
            True if sent successfully, False otherwise
        """

    def get_status(self) -> Dict[str, Any]:
        """Get output handler status information."""
        current_time = time.time()
        uptime = (
            (current_time - self.start_time)
            if self.is_running and self.start_time
            else 0
        )

        return {
            "running": self.is_running,
            "sentences_sent": self.sentences_sent,
            "uptime_seconds": uptime,
            # Convert timestamp to ISO format string, or None if not set
            "last_sentence_time": (
                time.strftime(
                    "%Y-%m-%dT%H:%M:%S",
                    time.gmtime(
                        self.last_sentence_time))
                if self.last_sentence_time
                else None
            ),
            "sentences_per_second": (
                self.sentences_sent / max(1, uptime) if uptime > 0 else 0
            ),
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.sentences_sent = 0
        current_time = time.time()
        self.start_time = current_time
        self.last_sentence_time = current_time

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
