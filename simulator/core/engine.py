"""Core simulation engine for NMEA data generation."""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field

from nmea_lib import GGASentence, RMCSentence, TalkerId, GpsFixQuality
from nmea_lib.types import DataStatus, ModeIndicator, Distance, DistanceUnit
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
class VesselSettings:
    """Vessel settings for the simulation."""
    vessel_name: str = "SimVessel"
    initial_latitude: float = 37.7749
    initial_longitude: float = -122.4194
    initial_speed: float = 0.0
    initial_heading: float = 0.0


@dataclass
class MovementSettings:
    """Movement settings for the simulation."""
    speed_variation: float = 2.0
    course_variation: float = 10.0
    position_noise: float = 0.00001


@dataclass
class SimulationConfig:
    """Configuration for the simulation."""
    start_time: Optional[datetime] = None
    time_factor: float = 1.0
    duration_seconds: Optional[float] = None
    vessel_settings: VesselSettings = field(default_factory=VesselSettings)
    movement_settings: MovementSettings = field(default_factory=MovementSettings)
    sentences: List[SentenceConfig] = field(default_factory=list)

    def __post_init__(self):
        """Initialize default sentence configuration."""
        if not self.sentences:
            self.sentences = [
                SentenceConfig("GGA", TalkerId.GP, 1.0),
                SentenceConfig("RMC", TalkerId.GP, 1.0),
            ]


@dataclass
class SimulationState:
    """State of the simulation."""
    running: bool = False
    simulation_thread: Optional[threading.Thread] = None
    stop_event: threading.Event = field(default_factory=threading.Event)


@dataclass
class SimulationStatistics:
    """Statistics of the simulation."""
    total_sentences_generated: int = 0
    sentences_by_type: Dict[str, int] = field(default_factory=dict)
    simulation_start_time: Optional[datetime] = None


class SimulationEngine:
    """Main NMEA simulation engine."""

    def __init__(self, config: SimulationConfig):
        """Initialize simulation engine."""
        self.config = config
        self.state: SimulationState = SimulationState()
        self.stats: SimulationStatistics = SimulationStatistics()

        # Core components
        self.time_manager = TimeManager(
            start_time=config.start_time,
            time_factor=config.time_factor
        )

        from nmea_lib.types import Position
        initial_position = Position(config.vessel_settings.initial_latitude,
                                    config.vessel_settings.initial_longitude)
        self.position_generator = PositionGenerator(
            initial_position=initial_position,
            initial_speed=config.vessel_settings.initial_speed,
            initial_heading=config.vessel_settings.initial_heading
        )

        # Set movement parameters
        self.position_generator.set_movement_parameters(
            speed_variation=config.movement_settings.speed_variation,
            course_variation=config.movement_settings.course_variation,
            position_noise=config.movement_settings.position_noise
        )

        # Output handlers
        self.output_handlers: List[OutputHandler] = []

        # Sentence generators
        self.sentence_generators: Dict[str, Callable] = {
            "GGA": self._generate_gga_sentence,
            "RMC": self._generate_rmc_sentence,
        }
    
    def add_output_handler(self, handler: OutputHandler) -> None:
        """Add an output handler."""
        self.output_handlers.append(handler)
    
    def remove_output_handler(self, handler: OutputHandler) -> None:
        """Remove an output handler."""
        if handler in self.output_handlers:
            self.output_handlers.remove(handler)
    
    def start(self) -> None:
        """Start the simulation."""
        if self.state.running:
            return

        self.state.running = True
        self.state.stop_event.clear()
        self.stats.simulation_start_time = datetime.now()

        # Start output handlers
        for handler in self.output_handlers:
            try:
                handler.start()
            except Exception as e:
                print(f"Warning: Failed to start output handler {handler}: {e}")

        # Start simulation thread
        self.state.simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.state.simulation_thread.start()

    def stop(self) -> None:
        """Stop the simulation."""
        if not self.state.running:
            return

        self.state.running = False
        self.state.stop_event.set()

        # Wait for simulation thread to finish
        if self.state.simulation_thread:
            self.state.simulation_thread.join(timeout=5.0)

        # Stop output handlers
        for handler in self.output_handlers:
            try:
                handler.stop()
            except Exception as e:
                print(f"Warning: Failed to stop output handler {handler}: {e}")
    
    def _simulation_loop(self) -> None:
        """Main simulation loop."""
        last_update_time = self.time_manager.get_current_time()

        while self.state.running and not self.state.stop_event.is_set():
            try:
                current_time = self.time_manager.get_current_time()
                elapsed = (current_time - last_update_time).total_seconds()

                # Update position
                position_state = self.position_generator.update_position(elapsed, current_time)

                # Generate sentences
                self._generate_sentences(current_time, position_state)

                # Check duration limit
                if self.config.duration_seconds:
                    sim_elapsed = (current_time - self.time_manager.start_time).total_seconds()
                    if sim_elapsed >= self.config.duration_seconds:
                        print(f"Simulation duration limit reached: {self.config.duration_seconds}s")
                        break

                last_update_time = current_time

                # Sleep until next update
                self.time_manager.sleep_until_next_update(0.1)  # 10Hz update rate

            except Exception as e:
                print(f"Error in simulation loop: {e}")
                time.sleep(0.1)

        self.state.running = False

    def _generate_sentences(self, current_time: datetime, position_state: PositionState) -> None:
        """Generate NMEA sentences based on configuration."""
        for sentence_config in self.config.sentences:
            if sentence_config.should_update(current_time):
                try:
                    # Generate sentence
                    generator = self.sentence_generators.get(sentence_config.sentence_type)
                    if generator:
                        sentence = generator(sentence_config, current_time, position_state)
                        if sentence:
                            # Send to all output handlers
                            self._send_sentence(sentence)

                            # Update statistics
                            self.stats.total_sentences_generated += 1
                            self.stats.sentences_by_type[sentence_config.sentence_type] = (
                                    self.stats.sentences_by_type.get(sentence_config.sentence_type, 0) + 1
                            )

                    sentence_config.mark_updated(current_time)

                except Exception as e:
                    print(f"Error generating {sentence_config.sentence_type} sentence: {e}")
    
    def _send_sentence(self, sentence: str) -> None:
        """Send sentence to all output handlers."""
        for handler in self.output_handlers:
            try:
                handler.send_sentence(sentence)
            except Exception as e:
                print(f"Error sending sentence to {handler}: {e}")
    
    def _generate_gga_sentence(self, config: SentenceConfig, current_time: datetime, 
                             position_state: PositionState) -> Optional[str]:
        """Generate GGA sentence."""
        try:
            sentence = GGASentence(config.talker_id)
            
            # Set time
            time_str = current_time.strftime("%H%M%S.%f")[:-3]  # HHMMSS.SSS
            sentence.set_time(time_str)
            
            # Set position
            sentence.set_position(
                position_state.position.latitude,
                position_state.position.longitude
            )
            
            # Set fix quality and satellites
            sentence.set_fix_quality(GpsFixQuality.GPS)
            sentence.set_satellites_in_use(8)  # Typical value
            sentence.set_horizontal_dilution(1.2)  # Good HDOP
            
            # Set altitude (simulate 50m above sea level)
            sentence.set_altitude(Distance(50.0, DistanceUnit.METERS))
            sentence.set_geoidal_height(Distance(19.6, DistanceUnit.METERS))
            
            return sentence.to_sentence()
            
        except Exception as e:
            print(f"Error generating GGA sentence: {e}")
            return None
    
    def _generate_rmc_sentence(self, config: SentenceConfig, current_time: datetime,
                             position_state: PositionState) -> Optional[str]:
        """Generate RMC sentence."""
        try:
            sentence = RMCSentence(config.talker_id)
            
            # Set time
            time_str = current_time.strftime("%H%M%S.%f")[:-3]  # HHMMSS.SSS
            sentence.set_time(time_str)
            
            # Set date
            date_str = current_time.strftime("%d%m%y")  # DDMMYY
            sentence.set_date(date_str)
            
            # Set status
            sentence.set_status(DataStatus.ACTIVE)
            
            # Set position
            sentence.set_position(
                position_state.position.latitude,
                position_state.position.longitude
            )
            
            # Set speed and course
            sentence.set_speed(position_state.speed)
            sentence.set_course(position_state.heading)
            
            # Set magnetic variation (example: 6.1° East)
            sentence.set_magnetic_variation(6.1)
            
            # Set mode indicator
            sentence.set_mode_indicator(ModeIndicator.AUTONOMOUS)
            
            return sentence.to_sentence()
            
        except Exception as e:
            print(f"Error generating RMC sentence: {e}")
            return None
    
    def get_status(self) -> Dict:
        """Get simulation status."""
        current_time = self.time_manager.get_current_time()
        position_state = self.position_generator.get_current_state(current_time)

        # Calculate runtime
        runtime = 0.0
        if self.stats.simulation_start_time:
            runtime = (datetime.now() - self.stats.simulation_start_time).total_seconds()

        return {
            'running': self.state.running,
            'simulation_time': current_time.isoformat(),
            'time_factor': self.time_manager.time_factor,
            'position': {
                'latitude': position_state.position.latitude,
                'longitude': position_state.position.longitude,
                'speed_knots': position_state.speed.value,
                'heading_degrees': position_state.heading.value
            },
            'statistics': {
                'total_sentences': self.stats.total_sentences_generated,
                'sentences_by_type': self.stats.sentences_by_type.copy(),
                'runtime_seconds': runtime,
                'sentences_per_second': self.stats.total_sentences_generated / max(1, runtime)
            },
            'output_handlers': [handler.get_status() for handler in self.output_handlers]
        }

    def __str__(self) -> str:
        """String representation."""
        status = "RUNNING" if self.state.running else "STOPPED"
        return f"SimulationEngine({status}, {len(self.output_handlers)} outputs, {self.stats.total_sentences_generated} sentences)"

