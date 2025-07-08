"""Factory for creating output handlers from configuration."""

from typing import List
from typing import List, Dict, Any # Added Dict, Any
from .base import OutputHandler
from .file import FileOutput, FileOutputConfig # Added FileOutputConfig
from .tcp import TCPOutput, TCPOutputConfig # Added TCPOutputConfig
from .udp import UDPOutput, UDPOutputConfig # Added UDPOutputConfig
from ..config.parser import OutputConfig


class OutputFactory:
    """Factory for creating output handlers."""
    
    @staticmethod
    def create_output_handler(output_config: OutputConfig) -> OutputHandler:
        """Create output handler from configuration."""
        if not output_config.enabled:
            raise ValueError("Output handler is disabled")

        # Ensure config is a dictionary
        if not isinstance(output_config.config, dict):
            raise TypeError(f"Expected config to be a dict, got {type(output_config.config)}")

        config_data: Dict[str, Any] = output_config.config
        
        if output_config.type == 'file':
            # The comprehensive_ais_simulation.py uses 'filename' but FileOutputConfig expects 'file_path'
            # We need to map it here or change the config structure.
            # Let's adjust for 'filename' from the example.
            if 'filename' in config_data and 'file_path' not in config_data:
                config_data['file_path'] = config_data.pop('filename')
            return FileOutput(FileOutputConfig(**config_data))
        elif output_config.type == 'tcp':
            return TCPOutput(TCPOutputConfig(**config_data))
        elif output_config.type == 'udp':
            # The comprehensive_ais_simulation.py directly uses 'host', 'port', 'broadcast'
            # UDPOutputConfig expects these, but also has 'multicast_group'
            # If 'multicast_group' is not in config_data, it will default to None (as per its Optional type hint)
            return UDPOutput(UDPOutputConfig(**config_data))
        else:
            raise ValueError(f"Unknown output type: {output_config.type}")
    
    @staticmethod
    def create_output_handlers(output_configs: List[OutputConfig]) -> List[OutputHandler]:
        """Create multiple output handlers from configuration list."""
        handlers = []
        
        for output_config in output_configs:
            if output_config.enabled:
                try:
                    handler = OutputFactory.create_output_handler(output_config)
                    handlers.append(handler)
                except Exception as e:
                    print(f"Warning: Failed to create {output_config.type} output handler: {e}")
        
        return handlers

