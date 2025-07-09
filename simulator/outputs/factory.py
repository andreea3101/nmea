"""Factory for creating output handlers from configuration."""

from typing import List
from .base import OutputHandler
from .file import FileOutput
from .tcp import TCPOutput
from .udp import UDPOutput
from .serial_output import SerialOutput  # Added import
from ..config.parser import OutputConfig


class OutputFactory:
    """Factory for creating output handlers."""

    @staticmethod
    def create_output_handler(output_config: OutputConfig) -> OutputHandler:
        """Create output handler from configuration."""
        if not output_config.enabled:
            raise ValueError("Output handler is disabled")

        if output_config.type == "file":
            return FileOutput(output_config.config)
        elif output_config.type == "tcp":
            return TCPOutput(output_config.config)
        elif output_config.type == "udp":
            return UDPOutput(output_config.config)
        elif output_config.type == "serial":  # Added serial type
            return SerialOutput(output_config.config)
        else:
            raise ValueError(f"Unknown output type: {output_config.type}")

    @staticmethod
    def create_output_handlers(
        output_configs: List[OutputConfig],
    ) -> List[OutputHandler]:
        """Create multiple output handlers from configuration list."""
        handlers = []

        for output_config in output_configs:
            if output_config.enabled:
                try:
                    handler = OutputFactory.create_output_handler(
                        output_config)
                    handlers.append(handler)
                except Exception as e:
                    print(
                        f"Warning: Failed to create {
                            output_config.type} output handler: {e}"
                    )

        return handlers
