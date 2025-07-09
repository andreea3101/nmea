"""Enhanced simulation engine with AIS and GPS integration."""

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import logging

from simulator.core.time_manager import TimeManager
from simulator.core.ais_scheduler import AISMessageScheduler
from simulator.generators.vessel import EnhancedVesselGenerator
from simulator.outputs.base import OutputHandler
from nmea_lib.sentences.gga import GGASentence
from nmea_lib.sentences.rmc import RMCSentence
from nmea_lib.sentences.aivdm import AISMessageGenerator
from nmea_lib.types.vessel import VesselState, BaseStationData, AidToNavigationData
from nmea_lib.types import (
    NMEATime,
    NMEADate,
    Speed,
    Bearing,
    Distance,
    SpeedUnit,
    BearingType,
    DistanceUnit,
)
from nmea_lib.base import GpsFixQuality  # Corrected import
from nmea_lib.types.enums import DataStatus  # Corrected import


@dataclass
class SimulationConfig:
    """Configuration for the enhanced simulation engine."""

    # Time settings
    time_factor: float = 1.0
    update_interval: float = 1.0  # seconds
    duration: Optional[float] = None  # seconds, None = infinite

    # GPS settings
    enable_gps: bool = True
    gps_update_interval: float = 1.0  # seconds

    # AIS settings
    enable_ais: bool = True
    # seconds (check scheduler more frequently)
    ais_update_interval: float = 0.1

    # Output settings
    sentence_rate_limit: float = 1000.0  # sentences per second

    # Logging
    log_level: str = "INFO"
    enable_trace_logging: bool = False


class EnhancedSimulationEngine:
    """Enhanced simulation engine supporting both GPS and AIS."""

    def __init__(self, config: SimulationConfig):
        """Initialize enhanced simulation engine."""
        self.config = config
        # Correctly initialize TimeManager using keyword argument for
        # time_factor
        self.time_manager = TimeManager(time_factor=config.time_factor)
        self.ais_scheduler = AISMessageScheduler()
        self.ais_generator = AISMessageGenerator()

        # Vessel management
        self.vessel_generators: Dict[int, EnhancedVesselGenerator] = {}
        self.base_stations: Dict[int, BaseStationData] = {}
        self.aids_to_navigation: Dict[int, AidToNavigationData] = {}

        # Output management
        self.output_handlers: List[OutputHandler] = []

        # Threading
        self.running = False
        self.simulation_thread: Optional[threading.Thread] = None
        self.gps_thread: Optional[threading.Thread] = None
        self.ais_thread: Optional[threading.Thread] = None

        # Statistics
        self.stats = {
            "start_time": None,
            "sentences_sent": 0,
            "gps_sentences": 0,
            "ais_sentences": 0,
            "errors": 0,
            "vessels_active": 0,
        }

        # Logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, config.log_level.upper()))

        # Trace logging callback
        self.trace_callback: Optional[Callable[[
            str, Dict[str, Any]], None]] = None

    def add_vessel(self, vessel_config: Dict) -> int:
        """Add a vessel to the simulation."""
        vessel_generator = EnhancedVesselGenerator(vessel_config)
        vessel_state = vessel_generator.get_current_state()
        mmsi = vessel_state.mmsi

        # Add to vessel generators
        self.vessel_generators[mmsi] = vessel_generator

        # Add to AIS scheduler
        if self.config.enable_ais:
            self.ais_scheduler.add_vessel(vessel_state)

        self.logger.info(
            f"Added vessel {mmsi} ({vessel_state.static_data.vessel_name})"
        )
        return mmsi

    def add_base_station(self, base_station_data: BaseStationData) -> int:
        """Add a base station to the simulation."""
        mmsi = base_station_data.mmsi
        self.base_stations[mmsi] = base_station_data

        if self.config.enable_ais:
            self.ais_scheduler.add_base_station(mmsi)

        self.logger.info(f"Added base station {mmsi}")
        return mmsi

    def add_aid_to_navigation(self, aid_nav_data: AidToNavigationData) -> int:
        """Add an aid to navigation to the simulation."""
        mmsi = aid_nav_data.mmsi
        self.aids_to_navigation[mmsi] = aid_nav_data

        if self.config.enable_ais:
            self.ais_scheduler.add_aid_to_navigation(mmsi)

        self.logger.info(f"Added aid to navigation {mmsi}")
        return mmsi

    def remove_vessel(self, mmsi: int):
        """Remove a vessel from the simulation."""
        if mmsi in self.vessel_generators:
            del self.vessel_generators[mmsi]
            self.ais_scheduler.remove_vessel(mmsi)
            self.logger.info(f"Removed vessel {mmsi}")

    def add_output_handler(self, handler: OutputHandler):
        """Add an output handler."""
        self.output_handlers.append(handler)
        self.logger.info(f"Added output handler: {type(handler).__name__}")

    def remove_output_handler(self, handler: OutputHandler):
        """Remove an output handler."""
        if handler in self.output_handlers:
            self.output_handlers.remove(handler)
            self.logger.info(
                f"Removed output handler: {
                    type(handler).__name__}"
            )

    def set_trace_callback(
            self, callback: Callable[[str, Dict[str, Any]], None]):
        """Set callback for trace logging."""
        self.trace_callback = callback

    def start(self):
        """Start the simulation."""
        if self.running:
            self.logger.warning("Simulation is already running")
            return

        self.running = True
        self.stats["start_time"] = datetime.now()
        self.stats["vessels_active"] = len(self.vessel_generators)

        self.logger.info("Starting enhanced simulation engine")

        # Initialize time manager (no start method needed)
        # Time manager automatically tracks time from initialization

        # Start output handlers
        for handler in self.output_handlers:
            try:
                handler.start()
                self.logger.info(
                    f"Started output handler: {
                        type(handler).__name__}"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to start output handler {
                        type(handler).__name__}: {e}"
                )

        # Start simulation threads
        if self.config.enable_gps:
            self.gps_thread = threading.Thread(
                target=self._gps_loop, daemon=True)
            self.gps_thread.start()
            self.logger.info("GPS simulation thread started")

        if self.config.enable_ais:
            self.ais_thread = threading.Thread(
                target=self._ais_loop, daemon=True)
            self.ais_thread.start()
            self.logger.info("AIS simulation thread started")

        # Start main simulation thread
        self.simulation_thread = threading.Thread(
            target=self._simulation_loop, daemon=True
        )
        self.simulation_thread.start()
        self.logger.info("Main simulation thread started")

    def stop(self):
        """Stop the simulation."""
        if not self.running:
            return

        self.logger.info("Stopping simulation engine")
        self.running = False

        # No explicit stop needed for time manager
        # It will stop tracking when simulation ends

        # Wait for threads to finish
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=5.0)

        if self.gps_thread and self.gps_thread.is_alive():
            self.gps_thread.join(timeout=5.0)

        if self.ais_thread and self.ais_thread.is_alive():
            self.ais_thread.join(timeout=5.0)

        # Stop output handlers
        for handler in self.output_handlers:
            try:
                handler.stop()
                self.logger.info(
                    f"Stopped output handler: {
                        type(handler).__name__}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error stopping output handler {
                        type(handler).__name__}: {e}"
                )

        self.logger.info("Simulation engine stopped")

    def _simulation_loop(self):
        """Main simulation loop."""
        start_time = datetime.now()

        while self.running:
            try:
                current_time = self.time_manager.get_current_time()
                elapsed = (datetime.now() - start_time).total_seconds()

                # Check duration limit
                if self.config.duration and elapsed >= self.config.duration:
                    self.logger.info(
                        f"Simulation duration ({
                            self.config.duration}s) reached"
                    )
                    break

                # Update vessel positions
                self._update_vessel_positions(current_time)

                # Update AIS scheduler intervals based on vessel speeds
                self._update_ais_intervals()

                # Sleep for update interval
                time.sleep(self.config.update_interval)

            except Exception as e:
                self.logger.error(f"Error in simulation loop: {e}")
                self.stats["errors"] += 1
                time.sleep(1.0)

        self.running = False

    def _gps_loop(self):
        """GPS sentence generation loop."""
        # Initialize last_gps_update to ensure the first update occurs if needed,
        # or handle the first run explicitly. Using None and checking is
        # cleaner.
        last_gps_update: Optional[datetime] = None

        while self.running:
            try:
                # Use simulation time for GPS scheduling
                sim_current_time = self.time_manager.get_current_time()

                # Check if it's time for GPS update based on simulation time
                if (
                    last_gps_update is None
                    or (sim_current_time - last_gps_update).total_seconds()
                    >= self.config.gps_update_interval
                ):
                    self._generate_gps_sentences(sim_current_time)
                    last_gps_update = sim_current_time

                # Sleep based on a fraction of GPS interval or a fixed small duration,
                # ensuring responsiveness without excessive CPU load.
                # This sleep is in real-time, so it should be small.
                # Consider the time_factor if very precise real-time alignment of this loop is needed,
                # but typically, this loop just needs to check periodically.
                sleep_duration = min(
                    0.1,
                    self.config.gps_update_interval
                    / (
                        self.time_manager.time_factor
                        if self.time_manager.time_factor > 0
                        else 1.0
                    )
                    / 2,
                )
                time.sleep(max(0.01, sleep_duration))  # Ensure a minimum sleep

            except Exception as e:
                self.logger.error(f"Error in GPS loop: {e}")
                self.stats["errors"] += 1
                time.sleep(1.0)

    def _ais_loop(self):
        """AIS sentence generation loop."""
        while self.running:
            try:
                current_time = self.time_manager.get_current_time()

                # Get due AIS messages
                due_messages = self.ais_scheduler.get_due_messages(
                    current_time)

                for vessel_mmsi, message_type in due_messages:
                    self._generate_ais_message(
                        vessel_mmsi, message_type, current_time)

                # Clean up old schedules periodically
                self.ais_scheduler.cleanup_old_schedules(current_time)

                time.sleep(self.config.ais_update_interval)

            except Exception as e:
                self.logger.error(f"Error in AIS loop: {e}")
                self.stats["errors"] += 1
                time.sleep(1.0)

    def _update_vessel_positions(self, current_time: datetime):
        """Update positions for all vessels."""
        for mmsi, generator in self.vessel_generators.items():
            try:
                # Update vessel state
                vessel_state = generator.update_vessel_state(
                    self.config.update_interval, current_time
                )

                # Update AIS scheduler with new speed
                self.ais_scheduler.update_vessel_intervals(
                    mmsi, vessel_state.navigation_data.sog
                )

            except Exception as e:
                self.logger.error(f"Error updating vessel {mmsi}: {e}")
                self.stats["errors"] += 1

    def _generate_gps_sentences(self, current_time: datetime):
        """Generate GPS sentences for all vessels."""
        for mmsi, generator in self.vessel_generators.items():
            try:
                vessel_state = generator.get_current_state()

                # Generate GGA sentence
                gga_sentence = self._create_gga_sentence(
                    vessel_state, current_time)
                self._send_sentence(gga_sentence.to_sentence(), "GPS")

                # Generate RMC sentence
                rmc_sentence = self._create_rmc_sentence(
                    vessel_state, current_time)
                self._send_sentence(rmc_sentence.to_sentence(), "GPS")

                self.stats["gps_sentences"] += 2

            except Exception as e:
                self.logger.error(
                    f"Error generating GPS sentences for vessel {mmsi}: {e}"
                )
                self.stats["errors"] += 1

    def _generate_ais_message(
        self, vessel_mmsi: int, message_type: int, current_time: datetime
    ):
        """Generate AIS message for a specific vessel and message type."""
        try:
            # Get vessel data
            vessel_data = None

            if vessel_mmsi in self.vessel_generators:
                vessel_data = self.vessel_generators[vessel_mmsi].get_current_state(
                )
            elif vessel_mmsi in self.base_stations:
                vessel_data = self.base_stations[vessel_mmsi]
            elif vessel_mmsi in self.aids_to_navigation:
                vessel_data = self.aids_to_navigation[vessel_mmsi]
            else:
                self.logger.warning(f"Unknown vessel MMSI: {vessel_mmsi}")
                return

            # Generate AIS message
            sentences, input_data = self.ais_generator.generate_message(
                message_type, vessel_data
            )

            # Send sentences
            for sentence in sentences:
                self._send_sentence(sentence, "AIS")

            # Mark message as sent
            self.ais_scheduler.mark_message_sent(
                vessel_mmsi, message_type, current_time
            )

            # Trace logging
            if self.config.enable_trace_logging and self.trace_callback:
                # Directly call the trace_callback (AISTraceLogger.log_message_generation)
                # with the required arguments.
                # processing_time_ms is not readily available here, so it
                # defaults to None.
                self.trace_callback(
                    vessel_mmsi=vessel_mmsi,
                    message_type=message_type,
                    sentences=sentences,
                    input_data=input_data,
                )

            self.stats["ais_sentences"] += len(sentences)

        except Exception as e:
            self.logger.error(
                f"Error generating AIS message type {message_type} for vessel {vessel_mmsi}: {e}")
            self.stats["errors"] += 1

    def _create_gga_sentence(
        self, vessel_state: VesselState, current_time: datetime
    ) -> GGASentence:
        """Create GGA sentence from vessel state."""
        nav = vessel_state.navigation_data
        # Using TalkerId.GP as a default for GPS sentences.
        # This can be enhanced later if vessels need to specify preferred talker IDs.
        talker_id = TalkerId.GP

        return GGASentence.create(
            talker_id=talker_id,
            current_time=current_time,
            latitude=nav.position.latitude,
            longitude=nav.position.longitude,
            fix_quality=GpsFixQuality.GPS,
            satellites=8,
            hdop=1.2,
            altitude=Distance(0.0, DistanceUnit.METERS),
            geoidal_height=Distance(19.6, DistanceUnit.METERS),
        )

    def _create_rmc_sentence(
        self, vessel_state: VesselState, current_time: datetime
    ) -> RMCSentence:
        """Create RMC sentence from vessel state."""
        nav = vessel_state.navigation_data
        # Using TalkerId.GP as a default for GPS sentences.
        # This can be enhanced later if vessels need to specify preferred talker IDs.
        talker_id = TalkerId.GP

        return RMCSentence.create(
            talker_id=talker_id,
            current_time=current_time,
            status=DataStatus.ACTIVE,
            latitude=nav.position.latitude,
            longitude=nav.position.longitude,
            speed=Speed(nav.sog, SpeedUnit.KNOTS),
            course=Bearing(nav.cog, BearingType.TRUE),
            magnetic_variation=0.0, # Default, can be customized
            mode_indicator=ModeIndicator.AUTONOMOUS # Default, can be customized
        )

    def _send_sentence(self, sentence: str, sentence_type: str):
        """Send sentence to all output handlers."""
        for handler in self.output_handlers:
            try:
                success = handler.send_sentence(sentence)
                if success:
                    self.stats["sentences_sent"] += 1
                else:
                    self.stats["errors"] += 1
            except Exception as e:
                self.logger.error(
                    f"Error sending sentence via {type(handler).__name__}: {e}"
                )
                self.stats["errors"] += 1

    def _update_ais_intervals(self):
        """Update AIS transmission intervals based on vessel speeds."""
        for mmsi, generator in self.vessel_generators.items():
            vessel_state = generator.get_current_state()
            speed = vessel_state.navigation_data.sog
            self.ais_scheduler.update_vessel_intervals(mmsi, speed)

    def get_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics."""
        runtime = 0
        if self.stats["start_time"]:
            runtime = (
                datetime.now() -
                self.stats["start_time"]).total_seconds()

        stats = self.stats.copy()
        stats["runtime_seconds"] = runtime
        stats["sentences_per_second"] = stats["sentences_sent"] / \
            max(1, runtime)
        stats["ais_scheduler_stats"] = self.ais_scheduler.get_transmission_statistics()

        return stats

    def get_vessel_states(self) -> Dict[int, VesselState]:
        """Get current states of all vessels."""
        states = {}
        for mmsi, generator in self.vessel_generators.items():
            states[mmsi] = generator.get_current_state()
        return states

    def get_vessel_count(self) -> int:
        """Get number of active vessels."""
        return len(self.vessel_generators)

    def is_running(self) -> bool:
        """Check if simulation is running."""
        return self.running

    def wait_for_completion(self):
        """Wait for simulation to complete."""
        if self.simulation_thread:
            self.simulation_thread.join()


# Utility functions
def create_default_simulation_config() -> SimulationConfig:
    """Create default simulation configuration."""
    return SimulationConfig()


def create_enhanced_engine(
    config: Optional[SimulationConfig] = None,
) -> EnhancedSimulationEngine:
    """Create enhanced simulation engine with optional configuration."""
    if config is None:
        config = create_default_simulation_config()
    return EnhancedSimulationEngine(config)
