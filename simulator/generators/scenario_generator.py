"""Complete scenario generator for NMEA sample generation with reference data."""

import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import random

from nmea_lib.types import (
    Position, create_vessel_state, NMEATime, NMEADate, Distance, DistanceUnit,
    Speed, SpeedUnit, Bearing, BearingType
)
from nmea_lib.types.vessel import VesselState, VesselClass, ShipType, NavigationStatus
from nmea_lib.types.enums import DataStatus
from nmea_lib.base import GpsFixQuality
from nmea_lib.sentences.aivdm import AISMessageGenerator
from nmea_lib.sentences.gga import GGASentence
from nmea_lib.sentences.rmc import RMCSentence
from simulator.generators.vessel import EnhancedVesselGenerator


@dataclass
class MessageReference:
    """Reference data for a generated message."""
    timestamp: str
    message_type: str  # 'GPS' or 'AIS'
    sentence: str
    vessel_mmsi: Optional[int] = None
    ais_message_type: Optional[int] = None
    input_data: Optional[Dict[str, Any]] = None
    binary_payload: Optional[str] = None
    decoded_fields: Optional[Dict[str, Any]] = None


@dataclass
class TimeSettings:
    """Time settings for scenario generation."""
    start_time: datetime
    duration_minutes: int = 60
    time_step_seconds: float = 1.0


@dataclass
class OutputSettings:
    """Output settings for scenario generation."""
    output_dir: str = "generated_scenario"
    nmea_filename: str = "nmea_output.txt"
    reference_filename: str = "reference_data.json"
    human_readable_filename: str = "human_readable.txt"
    csv_filename: str = "message_summary.csv"


@dataclass
class GenerationSettings:
    """Generation settings for scenario generation."""
    include_gps: bool = True
    include_ais: bool = True
    gps_interval_seconds: float = 1.0
    ais_intervals: Dict[int, float] = None  # Message type -> interval

    def __post_init__(self):
        if self.ais_intervals is None:
            # Default AIS intervals (ITU-R M.1371)
            self.ais_intervals = {
                1: 10.0,  # Position report Class A
                2: 10.0,  # Position report Class A (assigned schedule)
                3: 10.0,  # Position report Class A (response to interrogation)
                4: 10.0,  # Base station report
                5: 360.0,  # Static and voyage data (6 minutes)
                18: 30.0,  # Position report Class B
                19: 30.0,  # Extended Class B position report
                21: 180.0,  # Aid to navigation (3 minutes)
                24: 360.0  # Static data report Class B (6 minutes)
            }


@dataclass
class ScenarioGenerationConfig:
    """Configuration for scenario generation."""
    time_settings: TimeSettings
    output_settings: OutputSettings
    generation_settings: GenerationSettings
    vessel_count: int = 5
    area_bounds: Dict[str, float] = None  # lat_min, lat_max, lon_min, lon_max

    def __post_init__(self):
        if self.area_bounds is None:
            # Default to San Francisco Bay area
            self.area_bounds = {
                'lat_min': 37.7,
                'lat_max': 37.9,
                'lon_min': -122.5,
                'lon_max': -122.3
            }


class CompleteScenarioGenerator:
    """Generates complete NMEA scenarios with reference data for validation."""

    def __init__(self, config: ScenarioGenerationConfig):
        """Initialize scenario generator."""
        self.config = config
        self.ais_generator = AISMessageGenerator()
        self.vessels: List[VesselState] = []
        self.vessel_generators: Dict[int, EnhancedVesselGenerator] = {}
        self.reference_data: List[MessageReference] = []
        self.message_count = 0

        # Create output directory
        Path(self.config.output_settings.output_dir).mkdir(exist_ok=True)

        # Initialize vessels
        self._create_vessels()
    
    def _create_vessels(self):
        """Create vessels for the scenario."""
        vessel_templates = [
            {'type': 'container_ship', 'class': VesselClass.CLASS_A, 'ship_type': ShipType.CARGO_ALL_SHIPS},
            {'type': 'tanker', 'class': VesselClass.CLASS_A, 'ship_type': ShipType.TANKER_ALL_SHIPS},
            {'type': 'fishing_vessel', 'class': VesselClass.CLASS_A, 'ship_type': ShipType.FISHING},
            {'type': 'pleasure_craft', 'class': VesselClass.CLASS_B, 'ship_type': ShipType.PLEASURE_CRAFT},
            {'type': 'cargo_ship', 'class': VesselClass.CLASS_A, 'ship_type': ShipType.CARGO_ALL_SHIPS},
        ]
        
        bounds = self.config.area_bounds
        
        for i in range(self.config.vessel_count):
            template = vessel_templates[i % len(vessel_templates)]
            
            # Generate random position within bounds
            lat = random.uniform(bounds['lat_min'], bounds['lat_max'])
            lon = random.uniform(bounds['lon_min'], bounds['lon_max'])
            position = Position(lat, lon)
            
            # Generate MMSI (starting from 367000000 for US vessels)
            mmsi = 367000000 + i + 1
            
            # Create vessel state
            vessel = create_vessel_state(
                mmsi=mmsi,
                vessel_name=f"{template['type'].upper()}_{i+1:02d}",
                position=position,
                vessel_class=template['class'],
                callsign=f"TEST{i+1:03d}",
                ship_type=template['ship_type'],
                sog=random.uniform(5.0, 20.0),
                cog=random.uniform(0.0, 360.0),
                heading=int(random.uniform(0.0, 360.0)), # Ensure heading is int
                nav_status=NavigationStatus.UNDER_WAY_USING_ENGINE
            )
            
            # Set additional vessel data
            vessel.static_data.dimensions.to_bow = random.randint(50, 200)
            vessel.static_data.dimensions.to_stern = random.randint(10, 50)
            vessel.static_data.dimensions.to_port = random.randint(5, 20)
            vessel.static_data.dimensions.to_starboard = random.randint(5, 20)
            
            if template['class'] == VesselClass.CLASS_A:
                vessel.voyage_data.destination = f"PORT_{random.randint(1, 10)}"
                vessel.voyage_data.draught = random.uniform(5.0, 15.0)
                vessel.voyage_data.eta_month = random.randint(1, 12)
                vessel.voyage_data.eta_day = random.randint(1, 28)
                vessel.voyage_data.eta_hour = random.randint(0, 23)
                vessel.voyage_data.eta_minute = random.randint(0, 59)
            
            self.vessels.append(vessel)
            
            # Create vessel generator for movement
            vessel_config = {
                'mmsi': mmsi,
                'name': vessel.static_data.vessel_name,
                'initial_position': {'latitude': lat, 'longitude': lon},
                'initial_speed': vessel.navigation_data.sog,
                'initial_heading': vessel.navigation_data.heading,
                'movement': {
                    'pattern': 'linear',
                    'speed_variation': 2.0,
                    'course_variation': 5.0
                }
            }
            
            generator = EnhancedVesselGenerator(vessel_config)
            self.vessel_generators[mmsi] = generator
    
    def generate_scenario(self) -> Dict[str, str]:
        """Generate complete scenario with all output files."""
        print(f"Generating scenario with {self.config.vessel_count} vessels...")
        print(f"Duration: {self.config.time_settings.duration_minutes} minutes")
        print(f"Output directory: {self.config.output_settings.output_dir}")

        # Open output files
        nmea_file_path = Path(self.config.output_settings.output_dir) / self.config.output_settings.nmea_filename
        human_readable_path = Path(
            self.config.output_settings.output_dir) / self.config.output_settings.human_readable_filename

        with open(nmea_file_path, 'w') as nmea_file, \
                open(human_readable_path, 'w') as human_file:

            # Write headers
            human_file.write("NMEA 0183 Scenario Generation - Human Readable Output\\n")
            human_file.write("=" * 80 + "\\n")
            human_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
            human_file.write(f"Scenario duration: {self.config.time_settings.duration_minutes} minutes\\n")
            human_file.write(f"Vessels: {self.config.vessel_count}\\n")
            human_file.write("=" * 80 + "\\n\\n")

            # Generate time series
            current_time = self.config.time_settings.start_time
            end_time = current_time + timedelta(minutes=self.config.time_settings.duration_minutes)

            # Track last message times for each vessel and message type
            last_message_times: Dict[Tuple[int, int], datetime] = {}
            last_gps_time = current_time

            step_count = 0
            while current_time < end_time:
                step_count += 1

                # Update vessel positions
                self._update_vessel_positions(current_time)

                # Generate GPS messages
                if self.config.generation_settings.include_gps and \
                        (
                                current_time - last_gps_time).total_seconds() >= self.config.generation_settings.gps_interval_seconds:

                    for vessel in self.vessels:
                        gps_sentences = self._generate_gps_sentences(vessel, current_time)
                        for sentence in gps_sentences:
                            nmea_file.write(sentence + "\\n")
                            self._add_reference_data(sentence, 'GPS', current_time, vessel.mmsi)
                            self._write_human_readable(human_file, sentence, 'GPS', current_time, vessel)

                    last_gps_time = current_time

                # Generate AIS messages
                if self.config.generation_settings.include_ais:
                    for vessel in self.vessels:
                        for msg_type, interval in self.config.generation_settings.ais_intervals.items():
                            key = (vessel.mmsi, msg_type)

                            if key not in last_message_times:
                                last_message_times[key] = current_time
                                should_send = True
                            else:
                                time_since_last = (current_time - last_message_times[key]).total_seconds()
                                should_send = time_since_last >= interval

                            if should_send:
                                try:
                                    # Skip Type 4 and 21 if we only have VesselState objects,
                                    # as these types require BaseStationData and AidToNavigationData respectively.
                                    if msg_type == 4 and isinstance(vessel, VesselState):
                                        # print(f"Skipping AIS type 4 for Vessel {vessel.mmsi}, BaseStationData required.")
                                        continue
                                    if msg_type == 21 and isinstance(vessel, VesselState):
                                        # print(f"Skipping AIS type 21 for Vessel {vessel.mmsi}, AidToNavigationData required.")
                                        continue

                                    sentences, input_data = self.ais_generator.generate_message(msg_type, vessel)

                                    for sentence in sentences:
                                        nmea_file.write(sentence + "\\n")
                                        self._add_reference_data(
                                            sentence, 'AIS', current_time, vessel.mmsi,
                                            msg_type, input_data
                                        )
                                        self._write_human_readable(
                                            human_file, sentence, 'AIS', current_time, vessel,
                                            msg_type, input_data
                                        )

                                    last_message_times[key] = current_time

                                except Exception as e:
                                    print(f"Error generating AIS type {msg_type} for vessel {vessel.mmsi}: {e}")

                # Progress indicator
                if step_count % 100 == 0:
                    progress = (current_time - self.config.time_settings.start_time).total_seconds() / (
                                self.config.time_settings.duration_minutes * 60) * 100
                    print(f"Progress: {progress:.1f}% - Generated {self.message_count} messages")

                # Advance time
                current_time += timedelta(seconds=self.config.time_settings.time_step_seconds)

        # Save reference data and summary
        self._save_reference_data()
        self._save_csv_summary()

        # Return file paths
        return {
            'nmea_file': str(nmea_file_path),
            'reference_file': str(
                Path(self.config.output_settings.output_dir) / self.config.output_settings.reference_filename),
            'human_readable': str(human_readable_path),
            'csv_summary': str(Path(self.config.output_settings.output_dir) / self.config.output_settings.csv_filename)
        }
    
    def _update_vessel_positions(self, current_time: datetime):
        """Update vessel positions using generators."""
        for vessel in self.vessels:
            if vessel.mmsi in self.vessel_generators:
                generator = self.vessel_generators[vessel.mmsi]
                updated_state = generator.update_vessel_state(
                    self.config.time_settings.time_step_seconds, current_time
                )

                # Update vessel state
                vessel.navigation_data = updated_state.navigation_data
                vessel.timestamp = current_time
    
    def _generate_gps_sentences(self, vessel: VesselState, current_time: datetime) -> List[str]:
        """Generate GPS sentences for a vessel."""
        sentences = []
        nav = vessel.navigation_data
        
        # GGA sentence
        gga = GGASentence()
        gga.set_time(NMEATime.from_datetime(current_time))
        gga.set_position(nav.position.latitude, nav.position.longitude)
        gga.set_fix_quality(GpsFixQuality.GPS)  # Use enum member
        gga.set_satellites_in_use(8) # Corrected method name
        gga.set_horizontal_dilution(1.2)
        gga.set_altitude(Distance(0.0, DistanceUnit.METERS))
        gga.set_geoidal_height(Distance(19.6, DistanceUnit.METERS))
        sentences.append(str(gga))
        
        # RMC sentence
        rmc = RMCSentence()
        rmc.set_time(NMEATime.from_datetime(current_time))
        rmc.set_status(DataStatus.ACTIVE)  # Use enum member
        rmc.set_position(nav.position.latitude, nav.position.longitude)
        rmc.set_speed(Speed(nav.sog, SpeedUnit.KNOTS))
        rmc.set_course(Bearing(nav.cog, BearingType.TRUE))
        rmc.set_date(NMEADate.from_date(current_time.date()))
        rmc.set_magnetic_variation(0.0) # Pass only the float value
        sentences.append(str(rmc))
        
        return sentences
    
    def _add_reference_data(self, sentence: str, msg_type: str, timestamp: datetime,
                           vessel_mmsi: int, ais_msg_type: Optional[int] = None,
                           input_data: Optional[Dict[str, Any]] = None):
        """Add reference data for a generated sentence."""
        
        # Extract binary payload for AIS messages
        binary_payload = None
        if msg_type == 'AIS' and ',' in sentence:
            parts = sentence.split(',')
            if len(parts) >= 6:
                binary_payload = parts[5]  # AIS payload
        
        # Create decoded fields summary
        decoded_fields = None
        if input_data:
            decoded_fields = {k: v for k, v in input_data.items() 
                            if not k.startswith('_') and v is not None}
        
        ref = MessageReference(
            timestamp=timestamp.isoformat(),
            message_type=msg_type,
            sentence=sentence,
            vessel_mmsi=vessel_mmsi,
            ais_message_type=ais_msg_type,
            input_data=input_data,
            binary_payload=binary_payload,
            decoded_fields=decoded_fields
        )
        
        self.reference_data.append(ref)
        self.message_count += 1
    
    def _write_human_readable(self, file, sentence: str, msg_type: str, timestamp: datetime,
                             vessel: VesselState, ais_msg_type: Optional[int] = None,
                             input_data: Optional[Dict[str, Any]] = None):
        """Write human-readable explanation of the message."""
        
        file.write(f"[{timestamp.strftime('%H:%M:%S')}] ")
        
        if msg_type == 'GPS':
            if sentence.startswith('$GPGGA'):
                file.write(f"GPS Fix Data - Vessel {vessel.mmsi} ({vessel.static_data.vessel_name})\\n")
                file.write(f"  Position: {vessel.navigation_data.position.latitude:.6f}, {vessel.navigation_data.position.longitude:.6f}\\n")
                file.write(f"  Sentence: {sentence}\\n")
            elif sentence.startswith('$GPRMC'):
                file.write(f"GPS Recommended Minimum - Vessel {vessel.mmsi}\\n")
                file.write(f"  Speed: {vessel.navigation_data.sog:.1f} knots, Course: {vessel.navigation_data.cog:.1f}°\\n")
                file.write(f"  Sentence: {sentence}\\n")
        
        elif msg_type == 'AIS':
            file.write(f"AIS Type {ais_msg_type} - Vessel {vessel.mmsi} ({vessel.static_data.vessel_name})\\n")
            
            if ais_msg_type in [1, 2, 3]:
                file.write(f"  Position Report Class A\\n")
                file.write(f"  Position: {vessel.navigation_data.position.latitude:.6f}, {vessel.navigation_data.position.longitude:.6f}\\n")
                file.write(f"  Speed: {vessel.navigation_data.sog:.1f} knots, Course: {vessel.navigation_data.cog:.1f}°\\n")
                file.write(f"  Heading: {vessel.navigation_data.heading}°\\n")
            elif ais_msg_type == 4:
                file.write(f"  Base Station Report\\n")
            elif ais_msg_type == 5:
                file.write(f"  Static and Voyage Data\\n")
                file.write(f"  Call Sign: {vessel.static_data.callsign}\\n")
                file.write(f"  Destination: {vessel.voyage_data.destination}\\n")
                file.write(f"  Draught: {vessel.voyage_data.draught:.1f}m\\n")
            elif ais_msg_type == 18:
                file.write(f"  Position Report Class B\\n")
                file.write(f"  Position: {vessel.navigation_data.position.latitude:.6f}, {vessel.navigation_data.position.longitude:.6f}\\n")
                file.write(f"  Speed: {vessel.navigation_data.sog:.1f} knots\\n")
            elif ais_msg_type == 24:
                file.write(f"  Static Data Report Class B\\n")
            
            file.write(f"  Sentence: {sentence}\\n")
            
            if input_data:
                file.write(f"  Input Data: {json.dumps(input_data, indent=4)}\\n")
        
        file.write("\\n")
    
    def _save_reference_data(self):
        """Save reference data to JSON file."""
        reference_path = Path(self.config.output_settings.output_dir) / self.config.output_settings.reference_filename

        # Convert to serializable format
        data = {
            'generation_config': {
                'start_time': self.config.time_settings.start_time.isoformat(),
                'duration_minutes': self.config.time_settings.duration_minutes,
                'vessel_count': self.config.vessel_count,
                'area_bounds': self.config.area_bounds
            },
            'vessels': [
                {
                    'mmsi': vessel.mmsi,
                    'name': vessel.static_data.vessel_name,
                    'call_sign': vessel.static_data.callsign,  # Corrected attribute
                    'vessel_class': vessel.static_data.vessel_class.value,
                    'ship_type': vessel.static_data.ship_type.value,
                    'dimensions': asdict(vessel.static_data.dimensions)
                }
                for vessel in self.vessels
            ],
            'messages': [asdict(ref) for ref in self.reference_data],
            'statistics': {
                'total_messages': len(self.reference_data),
                'gps_messages': len([r for r in self.reference_data if r.message_type == 'GPS']),
                'ais_messages': len([r for r in self.reference_data if r.message_type == 'AIS']),
                'message_types': {}
            }
        }

        # Count AIS message types
        for ref in self.reference_data:
            if ref.message_type == 'AIS' and ref.ais_message_type:
                msg_type = ref.ais_message_type
                if msg_type not in data['statistics']['message_types']:
                    data['statistics']['message_types'][msg_type] = 0
                data['statistics']['message_types'][msg_type] += 1

        with open(reference_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Reference data saved to: {reference_path}")

    def _save_csv_summary(self):
        """Save message summary to CSV file."""
        csv_path = Path(self.config.output_settings.output_dir) / self.config.output_settings.csv_filename

        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Timestamp', 'Message_Type', 'Vessel_MMSI', 'AIS_Message_Type',
                'Latitude', 'Longitude', 'Speed_Knots', 'Course_Degrees',
                'Sentence'
            ])

            # Data rows
            for ref in self.reference_data:
                # Extract position data if available
                lat, lon, speed, course = '', '', '', ''

                if ref.decoded_fields:
                    lat = ref.decoded_fields.get('latitude', '')
                    lon = ref.decoded_fields.get('longitude', '')
                    speed = ref.decoded_fields.get('sog', '')
                    course = ref.decoded_fields.get('cog', '')

                writer.writerow([
                    ref.timestamp,
                    ref.message_type,
                    ref.vessel_mmsi or '',
                    ref.ais_message_type or '',
                    lat,
                    lon,
                    speed,
                    course,
                    ref.sentence
                ])

        print(f"CSV summary saved to: {csv_path}")


def create_default_config(output_dir: str = "generated_scenario") -> ScenarioGenerationConfig:
    """Create default scenario generation configuration."""
    return ScenarioGenerationConfig(
        time_settings=TimeSettings(start_time=datetime.now(), duration_minutes=30),
        output_settings=OutputSettings(output_dir=output_dir),
        generation_settings=GenerationSettings(),
        vessel_count=5
    )


def generate_complete_scenario(config: Optional[ScenarioGenerationConfig] = None) -> Dict[str, str]:
    """Generate a complete NMEA scenario with reference data."""
    if config is None:
        config = create_default_config()
    
    generator = CompleteScenarioGenerator(config)
    return generator.generate_scenario()


# Example usage
if __name__ == "__main__":
    # Generate a complete scenario
    config = ScenarioGenerationConfig(
        start_time=datetime(2025, 7, 4, 12, 0, 0),
        duration_minutes=60,
        output_dir="test_scenario",
        vessel_count=3
    )
    
    files = generate_complete_scenario(config)
    
    print("\\nGenerated files:")
    for file_type, file_path in files.items():
        print(f"  {file_type}: {file_path}")

