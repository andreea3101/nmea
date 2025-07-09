"""Core simulation engine for NMEA data generation."""

import time
import threading
import logging  # Added
from datetime import datetime
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field

from nmea_lib import GGASentence, RMCSentence, TalkerId, GpsFixQuality
from nmea_lib.types import DataStatus, ModeIndicator, Distance, DistanceUnit, Position # Position added
from .time_manager import TimeManager
from ..generators.position import PositionGenerator, PositionState
from ..outputs.base import OutputHandler


@dataclass
class SentenceConfig:
    """Configuration for a sentence type."""

    sentence_type: str
    talker_id: TalkerId
    rate_hz: float  # Generation rate in Hz
    enabled: bool = True
    last_update: datetime = field(default_factory=datetime.utcnow)

    def should_update(self, current_time: datetime) -> bool:
        """Check if sentence should be updated."""
        if not self.enabled or self.rate_hz <= 0:
            return False

        interval = 1.0 / self.rate_hz
        elapsed = (current_time - self.last_update).total_seconds()
        return elapsed >= interval

    def mark_updated(self, current_time: datetime) -> None:
        """Mark sentence as updated."""
        self.last_update = current_time


@dataclass
class SimulationConfig:
    """Configuration for the simulation."""

    # Time settings
    start_time: Optional[datetime] = None
    time_factor: float = 1.0
    duration_seconds: Optional[float] = None

    # Vessel settings
    vessel_name: str = "SimVessel"
    initial_latitude: float = 37.7749
    initial_longitude: float = -122.4194
    initial_speed: float = 0.0
    initial_heading: float = 0.0

    # Movement settings
    speed_variation: float = 2.0
    course_variation: float = 10.0
    position_noise: float = 0.00001

    # Sentence configuration
    sentences: List[SentenceConfig] = field(default_factory=list)

    def __post_init__(self):
        """Initialize default sentence configuration."""
        if not self.sentences:
            self.sentences = [
                SentenceConfig("GGA", TalkerId.GP, 1.0),
                SentenceConfig("RMC", TalkerId.GP, 1.0),
            ]


class SimulationEngine:
    """Main NMEA simulation engine."""

    def __init__(self, config: SimulationConfig):
        """Initialize simulation engine."""
        self.config = config

        # Core components
        self.time_manager = TimeManager(
            start_time=config.start_time, time_factor=config.time_factor
        )

        initial_position = Position(
            config.initial_latitude,
            config.initial_longitude)
        self.position_generator = PositionGenerator(
            initial_position=initial_position,
            initial_speed=config.initial_speed,
            initial_heading=config.initial_heading,
        )

        # Set movement parameters
        self.position_generator.set_movement_parameters(
            speed_variation=config.speed_variation,
            course_variation=config.course_variation,
            position_noise=config.position_noise,
        )

        # Output handlers
        self.output_handlers: List[OutputHandler] = []

        # Sentence generators
        self.sentence_generators: Dict[str, Callable] = {
            "GGA": self._generate_gga_sentence,
            "RMC": self._generate_rmc_sentence,
        }

        # Control
        self.running = False
        self.simulation_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # Statistics
        self.total_sentences_generated = 0
        self.sentences_by_type: Dict[str, int] = {}
        self.simulation_start_time: Optional[datetime] = None

        # Logging
        self.logger = logging.getLogger(__name__)

    def add_output_handler(self, handler: OutputHandler) -> None:
        """Add an output handler."""
        self.output_handlers.append(handler)

    def remove_output_handler(self, handler: OutputHandler) -> None:
        """Remove an output handler."""
        if handler in self.output_handlers:
            self.output_handlers.remove(handler)

    def start(self) -> None:
        """Start the simulation."""
        if self.running:
            return

        self.running = True
        self.stop_event.clear()
        self.simulation_start_time = datetime.now()

        # Start output handlers
        for handler in self.output_handlers:
            try:
                handler.start()
            except Exception as e:
                self.logger.warning(
                    f"Failed to start output handler {handler}: {e}", exc_info=True)

        # Start simulation thread
        self.simulation_thread = threading.Thread(
            target=self._simulation_loop, daemon=True
        )
        self.simulation_thread.start()

    def stop(self) -> None:
        """Stop the simulation."""
        if not self.running:
            return

        self.running = False
        self.stop_event.set()

        # Wait for simulation thread to finish
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5.0)

        # Stop output handlers
        for handler in self.output_handlers:
            try:
                handler.stop()
            except Exception as e:
                self.logger.warning(f"Failed to stop output handler {handler}: {e}", exc_info=True)

    def _simulation_loop(self) -> None:
        """Main simulation loop."""
        last_update_time = self.time_manager.get_current_time()

        while self.running and not self.stop_event.is_set():
            try:
                current_time = self.time_manager.get_current_time()
                elapsed = (current_time - last_update_time).total_seconds()

                # Update position
                position_state = self.position_generator.update_position(
                    elapsed, current_time
                )

                # Generate sentences
                self._generate_sentences(current_time, position_state)

                # Check duration limit
                if self.config.duration_seconds:
                    sim_elapsed = (
                        current_time - self.time_manager.start_time
                    ).total_seconds()
                    if sim_elapsed >= self.config.duration_seconds:
                        self.logger.info(
                            f"Simulation duration limit reached: {self.config.duration_seconds}s"
                        )
                        break

                last_update_time = current_time

                # Sleep until next update
                self.time_manager.sleep_until_next_update(
                    0.1)  # 10Hz update rate

            except Exception as e:
                self.logger.error(f"Error in simulation loop: {e}", exc_info=True)
                time.sleep(0.1)  # Allow other threads to run

        self.running = False

    def _generate_sentences(
        self, current_time: datetime, position_state: PositionState
    ) -> None:
        """Generate NMEA sentences based on configuration."""
        for sentence_config in self.config.sentences:
            if sentence_config.should_update(current_time):
                try:
                    # Generate sentence
                    generator = self.sentence_generators.get(
                        sentence_config.sentence_type
                    )
                    if generator:
                        sentence = generator(
                            sentence_config, current_time, position_state
                        )
                        if sentence:
                            # Send to all output handlers
                            self._send_sentence(sentence)

                            # Update statistics
                            self.total_sentences_generated += 1
                            self.sentences_by_type[sentence_config.sentence_type] = (
                                self.sentences_by_type.get(
                                    sentence_config.sentence_type, 0
                                )
                                + 1
                            )

                    sentence_config.mark_updated(current_time)

                except Exception as e:
                    self.logger.error(
                        f"Error generating {sentence_config.sentence_type} sentence: {e}",
                        exc_info=True
                    )

    def _send_sentence(self, sentence: str) -> None:
        """Send sentence to all output handlers."""
        for handler in self.output_handlers:
            try:
                handler.send_sentence(sentence)
            except Exception as e:
                self.logger.error(f"Error sending sentence to {handler}: {e}", exc_info=True)

    def _generate_gga_sentence(
        self,
        config: SentenceConfig,
        current_time: datetime,
        position_state: PositionState,
    ) -> Optional[str]:
        """Generate GGA sentence."""
        try:
            sentence = GGASentence.create(
                talker_id=config.talker_id,
                current_time=current_time,
                latitude=position_state.position.latitude,
                longitude=position_state.position.longitude,
                fix_quality=GpsFixQuality.GPS,
                satellites=8,
                hdop=1.2,
                altitude=Distance(50.0, DistanceUnit.METERS),
                geoidal_height=Distance(19.6, DistanceUnit.METERS)
            )
            return sentence.to_sentence()
        except Exception as e:
            self.logger.error(f"Error generating GGA sentence: {e}", exc_info=True)
            return None

    def _generate_rmc_sentence(
        self,
        config: SentenceConfig,
        current_time: datetime,
        position_state: PositionState,
    ) -> Optional[str]:
        """Generate RMC sentence."""
        try:
            # Assuming PositionState has .speed and .heading that are Speed and Bearing objects
            from nmea_lib.types import Speed, Bearing, SpeedUnit, BearingType # Local import for type construction

            sentence = RMCSentence.create(
                talker_id=config.talker_id,
                current_time=current_time,
                status=DataStatus.ACTIVE,
                latitude=position_state.position.latitude,
                longitude=position_state.position.longitude,
                speed=Speed(position_state.speed.value, SpeedUnit.KNOTS),
                course=Bearing(position_state.heading.value, BearingType.TRUE),
                magnetic_variation=6.1,
                mode_indicator=ModeIndicator.AUTONOMOUS
            )
            return sentence.to_sentence()
        except Exception as e:
            self.logger.error(f"Error generating RMC sentence: {e}", exc_info=True)
            return None

    def get_status(self) -> Dict:
        """Get simulation status."""
        current_time = self.time_manager.get_current_time()
        position_state = self.position_generator.get_current_state(
            current_time)

        # Calculate runtime
        runtime = 0.0
        if self.simulation_start_time:
            runtime = (
                datetime.now() -
                self.simulation_start_time).total_seconds()

        return {
            "running": self.running,
            "simulation_time": current_time.isoformat(),
            "time_factor": self.time_manager.time_factor,
            "position": {
                "latitude": position_state.position.latitude,
                "longitude": position_state.position.longitude,
                "speed_knots": position_state.speed.value,
                "heading_degrees": position_state.heading.value,
            },
            "statistics": {
                "total_sentences": self.total_sentences_generated,
                "sentences_by_type": self.sentences_by_type.copy(),
                "runtime_seconds": runtime,
                "sentences_per_second": self.total_sentences_generated
                / max(1, runtime),
            },
            "output_handlers": [
                handler.get_status() for handler in self.output_handlers
            ],
        }

    def __str__(self) -> str:
        """String representation."""
        status = "RUNNING" if self.running else "STOPPED"
        return f"SimulationEngine({status}, {
            len(
                self.output_handlers)} outputs, {
            self.total_sentences_generated} sentences)"
