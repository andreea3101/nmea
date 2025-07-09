"""Configuration parser for NMEA simulator."""

import yaml
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
from dataclasses import dataclass

from nmea_lib import TalkerId
from ..core.engine import SimulationConfig, SentenceConfig
from ..outputs import FileOutputConfig, TCPOutputConfig, UDPOutputConfig
from ..outputs.serial_output import SerialOutputConfig  # Added import


@dataclass
class OutputConfig:
    """Configuration for output handlers."""

    type: str  # 'file', 'tcp', 'udp'
    enabled: bool = True
    config: Any = None  # Specific config object


class ConfigParser:
    """Parser for YAML configuration files."""

    @staticmethod
    def from_file(config_path: str) -> SimulationConfig:
        """Load configuration from YAML file."""
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}")

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")

        return ConfigParser.from_dict(config_data)

    @staticmethod
    def from_dict(config_data: Dict[str, Any]) -> SimulationConfig:
        """Create configuration from dictionary."""
        config = SimulationConfig()

        # Simulation settings
        if "simulation" in config_data:
            sim_config = config_data["simulation"]

            if "duration" in sim_config:
                config.duration_seconds = float(sim_config["duration"])

            if "time_factor" in sim_config:
                config.time_factor = float(sim_config["time_factor"])

            if "start_time" in sim_config:
                start_time_str = sim_config["start_time"]
                if start_time_str:
                    config.start_time = datetime.fromisoformat(
                        start_time_str.replace("Z", "+00:00")
                    )

        # Vessel settings
        if "vessel" in config_data:
            vessel_config = config_data["vessel"]

            if "name" in vessel_config:
                config.vessel_name = str(vessel_config["name"])

            if "initial_position" in vessel_config:
                pos_config = vessel_config["initial_position"]
                config.initial_latitude = float(
                    pos_config.get("latitude", config.initial_latitude)
                )
                config.initial_longitude = float(
                    pos_config.get("longitude", config.initial_longitude)
                )

            if "initial_speed" in vessel_config:
                config.initial_speed = float(vessel_config["initial_speed"])

            if "initial_heading" in vessel_config:
                config.initial_heading = float(
                    vessel_config["initial_heading"])

        # Movement settings
        if "movement" in config_data:
            movement_config = config_data["movement"]

            if "speed_variation" in movement_config:
                config.speed_variation = float(
                    movement_config["speed_variation"])

            if "course_variation" in movement_config:
                config.course_variation = float(
                    movement_config["course_variation"])

            if "position_noise" in movement_config:
                config.position_noise = float(
                    movement_config["position_noise"])

        # Sentence configuration
        if "sentences" in config_data:
            config.sentences = []
            for sentence_data in config_data["sentences"]:
                sentence_config = ConfigParser._parse_sentence_config(
                    sentence_data)
                config.sentences.append(sentence_config)

        # Store output configurations for later use
        config.output_configs = []
        if "outputs" in config_data:
            for output_data in config_data["outputs"]:
                output_config = ConfigParser._parse_output_config(output_data)
                config.output_configs.append(output_config)

        return config

    @staticmethod
    def _parse_sentence_config(
            sentence_data: Dict[str, Any]) -> SentenceConfig:
        """Parse sentence configuration."""
        sentence_type = sentence_data.get("type", "GGA").upper()

        # Parse talker ID
        talker_str = sentence_data.get("talker_id", "GP").upper()
        try:
            talker_id = TalkerId(talker_str)
        except ValueError:
            talker_id = TalkerId.GP

        rate_hz = float(sentence_data.get("rate", 1.0))
        enabled = bool(sentence_data.get("enabled", True))

        return SentenceConfig(
            sentence_type=sentence_type,
            talker_id=talker_id,
            rate_hz=rate_hz,
            enabled=enabled,
        )

    @staticmethod
    def _parse_output_config(output_data: Dict[str, Any]) -> OutputConfig:
        """Parse output configuration."""
        output_type = output_data.get("type", "file").lower()
        enabled = bool(output_data.get("enabled", True))

        if output_type == "file":
            config = FileOutputConfig(
                file_path=output_data.get("path", "nmea_output.log"),
                append_mode=bool(output_data.get("append", True)),
                auto_flush=bool(output_data.get("auto_flush", True)),
                rotation_size_mb=output_data.get("rotation_size_mb"),
                rotation_time_hours=output_data.get("rotation_time_hours"),
                max_files=int(output_data.get("max_files", 10)),
            )

        elif output_type == "tcp":
            config = TCPOutputConfig(
                host=output_data.get("host", "0.0.0.0"),
                port=int(output_data.get("port", 10110)),
                max_clients=int(output_data.get("max_clients", 10)),
                client_timeout=float(output_data.get("client_timeout", 30.0)),
                send_timeout=float(output_data.get("send_timeout", 5.0)),
            )

        elif output_type == "udp":
            config = UDPOutputConfig(
                host=output_data.get("host", "255.255.255.255"),
                port=int(output_data.get("port", 10111)),
                broadcast=bool(output_data.get("broadcast", True)),
                multicast_group=output_data.get("multicast_group"),
                multicast_ttl=int(output_data.get("multicast_ttl", 1)),
                send_timeout=float(output_data.get("send_timeout", 1.0)),
            )

        elif output_type == "serial":
            config = SerialOutputConfig(
                port=str(output_data.get("port", "/dev/ttyS0")),
                baudrate=int(output_data.get("baudrate", 9600)),
                bytesize=output_data.get(
                    "bytesize", "EIGHTBITS"
                ),  # Keep as string for config flexibility
                parity=output_data.get(
                    "parity", "PARITY_NONE"),  # Keep as string
                stopbits=output_data.get(
                    "stopbits", "STOPBITS_ONE"),  # Keep as string
                timeout=output_data.get(
                    "timeout"
                ),  # Allow None by not providing default here if that's desired
                write_timeout=output_data.get("write_timeout"),  # Allow None
                rtscts=bool(output_data.get("rtscts", False)),
                dsrdtr=bool(output_data.get("dsrdtr", False)),
                xonxoff=bool(output_data.get("xonxoff", False)),
                exclusive=bool(output_data.get("exclusive", True)),
                send_interval=float(output_data.get("send_interval", 0.1)),
                reconnect_delay=float(output_data.get("reconnect_delay", 5.0)),
                max_reconnect_attempts=int(
                    output_data.get("max_reconnect_attempts", 5)
                ),
                line_ending=str(output_data.get("line_ending", "\r\n")),
            )
            # Handle optional timeout values more carefully:
            # If timeout/write_timeout is specified in YAML as null/None, it should pass as None.
            # If it's missing, it will default to None in SerialOutputConfig or its __post_init__ can set a default.
            # The current SerialOutputConfig defaults them to 1.0, so missing means 1.0.
            # If we want to allow YAML to explicitly set it to None to override the dataclass default,
            # we might need to adjust SerialOutputConfig or handle it here.
            # For now, `output_data.get('timeout')` will pass None if key is missing or value is null.
            # SerialOutputConfig.__post_init__ will then use its default of 1.0.
            # If YAML has `timeout: null`, it will be None.
            if "timeout" in output_data and output_data["timeout"] is not None:
                config.timeout = float(output_data["timeout"])
            elif "timeout" not in output_data:  # Key missing, rely on dataclass default
                pass  # SerialOutputConfig will use its default of 1.0

            if (
                "write_timeout" in output_data
                and output_data["write_timeout"] is not None
            ):
                config.write_timeout = float(output_data["write_timeout"])
            elif (
                "write_timeout" not in output_data
            ):  # Key missing, rely on dataclass default
                pass  # SerialOutputConfig will use its default of 1.0

        else:
            raise ValueError(f"Unknown output type: {output_type}")

        return OutputConfig(type=output_type, enabled=enabled, config=config)


class SimulatorConfig:
    """Convenience class for configuration management."""

    @staticmethod
    def from_file(config_path: str) -> SimulationConfig:
        """Load configuration from file."""
        return ConfigParser.from_file(config_path)

    @staticmethod
    def create_default() -> SimulationConfig:
        """Create default configuration."""
        return SimulationConfig()

    @staticmethod
    def create_example() -> SimulationConfig:
        """Create example configuration."""
        config = SimulationConfig()
        config.duration_seconds = 3600  # 1 hour
        config.time_factor = 1.0  # Real-time
        config.vessel_name = "Example Vessel"
        config.initial_latitude = 37.7749  # San Francisco
        config.initial_longitude = -122.4194
        config.initial_speed = 10.0  # 10 knots
        config.initial_heading = 45.0  # Northeast

        # Configure sentences
        config.sentences = [
            SentenceConfig("GGA", TalkerId.GP, 1.0),  # 1 Hz
            SentenceConfig("RMC", TalkerId.GP, 1.0),  # 1 Hz
        ]

        return config
