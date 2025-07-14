"""Enhanced vessel data models for AIS and GPS integration."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from enum import Enum

from nmea_lib.types import Position, Speed, Bearing
from nmea_lib.ais.constants import (
    NavigationStatus, ShipType, EPFDType, VesselClass,
    AIS_NOT_AVAILABLE
)


@dataclass
class VesselDimensions:
    """Vessel dimension information for AIS."""
    to_bow: int = 0          # Distance from reference point to bow (meters)
    to_stern: int = 0        # Distance from reference point to stern (meters)
    to_port: int = 0         # Distance from reference point to port (meters)
    to_starboard: int = 0    # Distance from reference point to starboard (meters)
    
    @property
    def length(self) -> int:
        """Total vessel length."""
        return self.to_bow + self.to_stern
    
    @property
    def beam(self) -> int:
        """Total vessel beam."""
        return self.to_port + self.to_starboard
    
    def to_ais_format(self) -> Tuple[int, int, int, int]:
        """Convert to AIS message format."""
        return (self.to_bow, self.to_stern, self.to_port, self.to_starboard)


@dataclass
class VesselETA:
    """Estimated Time of Arrival information."""
    month: int = 0      # 1-12, 0 = not available
    day: int = 0        # 1-31, 0 = not available  
    hour: int = 24      # 0-23, 24 = not available
    minute: int = 60    # 0-59, 60 = not available
    
    def to_ais_format(self) -> Tuple[int, int, int, int]:
        """Convert to AIS message format."""
        return (self.month, self.day, self.hour, self.minute)
    
    @classmethod
    def from_datetime(cls, dt: Optional[datetime]) -> 'VesselETA':
        """Create ETA from datetime object."""
        if dt is None:
            return cls()
        return cls(
            month=dt.month,
            day=dt.day,
            hour=dt.hour,
            minute=dt.minute
        )


@dataclass
class VesselMetadata:
    """Additional metadata for a vessel."""
    imo_number: Optional[int] = None
    flag_state: str = ""
    owner: str = ""


@dataclass
class VesselStaticData:
    """Static vessel information for AIS."""
    mmsi: int
    vessel_name: str = ""
    callsign: str = ""
    ship_type: ShipType = ShipType.NOT_AVAILABLE
    dimensions: VesselDimensions = field(default_factory=VesselDimensions)
    epfd_type: EPFDType = EPFDType.GPS
    vessel_class: VesselClass = VesselClass.CLASS_A
    metadata: VesselMetadata = field(default_factory=VesselMetadata)

    def validate(self) -> bool:
        """Validate static data fields."""
        if not (200000000 <= self.mmsi <= 999999999):
            return False
        if len(self.vessel_name) > 20:
            return False
        if len(self.callsign) > 7:
            return False
        return True


@dataclass
class VesselVoyageData:
    """Voyage-related vessel information for AIS."""
    destination: str = ""
    eta: VesselETA = field(default_factory=VesselETA)
    draught: float = 0.0    # Maximum present static draught (meters)
    persons_on_board: int = 0
    dte: int = 1            # Data Terminal Equipment (0=available, 1=not available)
    
    def validate(self) -> bool:
        """Validate voyage data fields."""
        if len(self.destination) > 20:
            return False
        if not (0.0 <= self.draught <= 25.5):
            return False
        if not (0 <= self.persons_on_board <= 8191):
            return False
        return True


@dataclass
class VesselRadioStatus:
    """Radio status information for a vessel."""
    position_accuracy: int = 0  # 0 = low accuracy, 1 = high accuracy
    raim: int = 0  # RAIM flag (0 = not in use, 1 = in use)
    radio_status: int = 0  # Radio status


@dataclass
class VesselNavigationData:
    """Dynamic navigation data for AIS."""
    position: Position
    sog: float = 0.0  # Speed over ground (knots)
    cog: float = 0.0  # Course over ground (degrees)
    heading: int = 511  # True heading (degrees, 511 = not available)
    nav_status: NavigationStatus = NavigationStatus.DEFAULT
    rot: int = 128  # Rate of turn (-128 to 127, 128 = not available)
    timestamp: int = 60  # UTC second (0-59, 60 = not available)
    radio_status: VesselRadioStatus = field(default_factory=VesselRadioStatus)

    def validate(self) -> bool:
        """Validate navigation data fields."""
        if not (0.0 <= self.sog <= 102.3):
            return False
        if not (0.0 <= self.cog <= 360.0):
            return False
        if not (0 <= self.heading <= 511):
            return False
        if not (-128 <= self.rot <= 127):
            return False
        if not (0 <= self.timestamp <= 60):
            return False
        return True


@dataclass
class BaseStationData:
    """Base station information for AIS Type 4 messages."""
    mmsi: int
    position: Position
    timestamp: datetime
    epfd_type: EPFDType = EPFDType.GPS
    raim: int = 0
    radio_status: int = 0
    
    def validate(self) -> bool:
        """Validate base station data."""
        return 1000000 <= self.mmsi <= 9999999


@dataclass
class AidToNavigationStatus:
    """Status information for an aid to navigation."""
    off_position: int = 0  # 0 = on position, 1 = off position
    regional: int = 0  # Regional reserved bits
    raim: int = 0
    virtual_aid: int = 0  # 0 = real aid, 1 = virtual aid
    assigned: int = 0  # 0 = autonomous mode, 1 = assigned mode
    position_accuracy: int = 0  # Position accuracy flag


@dataclass
class AidToNavigationData:
    """Aid to Navigation information for AIS Type 21 messages."""
    mmsi: int
    position: Position
    aid_type: int = 0
    name: str = ""
    dimensions: VesselDimensions = field(default_factory=VesselDimensions)
    epfd_type: EPFDType = EPFDType.GPS
    timestamp: int = 60
    status: AidToNavigationStatus = field(default_factory=AidToNavigationStatus)

    def validate(self) -> bool:
        """Validate aid to navigation data."""
        if not (990000000 <= self.mmsi <= 999999999):
            return False
        if len(self.name) > 20:
            return False
        return True


@dataclass
class VesselState:
    """Complete vessel state combining all AIS and GPS data."""
    # Core identification
    static_data: VesselStaticData
    navigation_data: VesselNavigationData
    voyage_data: VesselVoyageData
    
    # Simulation metadata
    timestamp_sim: datetime
    last_update: datetime = field(default_factory=datetime.now)
    
    # Message transmission tracking
    last_message_times: Dict[int, datetime] = field(default_factory=dict)
    message_sequence: Dict[int, int] = field(default_factory=dict)
    
    @property
    def mmsi(self) -> int:
        """Get vessel MMSI."""
        return self.static_data.mmsi
    
    @property
    def position(self) -> Position:
        """Get current position."""
        return self.navigation_data.position
    
    @property
    def vessel_class(self) -> VesselClass:
        """Get vessel class."""
        return self.static_data.vessel_class
    
    def update_position(self, position: Position, sog: float, cog: float, 
                       heading: int, timestamp: datetime) -> None:
        """Update vessel position and movement data."""
        self.navigation_data.position = position
        self.navigation_data.sog = sog
        self.navigation_data.cog = cog
        self.navigation_data.heading = heading
        self.timestamp_sim = timestamp
        self.last_update = datetime.now()
    
    def should_send_message(self, message_type: int, current_time: datetime,
                           interval: float) -> bool:
        """Check if a message type should be transmitted."""
        if message_type not in self.last_message_times:
            return True
        
        elapsed = (current_time - self.last_message_times[message_type]).total_seconds()
        return elapsed >= interval
    
    def mark_message_sent(self, message_type: int, timestamp: datetime) -> None:
        """Mark that a message type was transmitted."""
        self.last_message_times[message_type] = timestamp
        if message_type not in self.message_sequence:
            self.message_sequence[message_type] = 0
        self.message_sequence[message_type] = (self.message_sequence[message_type] + 1) % 4
    
    def get_message_sequence(self, message_type: int) -> int:
        """Get current sequence number for message type."""
        return self.message_sequence.get(message_type, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert vessel state to dictionary for logging."""
        return {
            'mmsi': self.mmsi,
            'vessel_name': self.static_data.vessel_name,
            'vessel_class': self.vessel_class.value,
            'position': {
                'latitude': self.position.latitude,
                'longitude': self.position.longitude
            },
            'navigation': {
                'sog': self.navigation_data.sog,
                'cog': self.navigation_data.cog,
                'heading': self.navigation_data.heading,
                'nav_status': self.navigation_data.nav_status.value,
                'rot': self.navigation_data.rot
            },
            'static': {
                'callsign': self.static_data.callsign,
                'ship_type': self.static_data.ship_type.value,
                'dimensions': self.static_data.dimensions.to_ais_format()
            },
            'voyage': {
                'destination': self.voyage_data.destination,
                'eta': self.voyage_data.eta.to_ais_format(),
                'draught': self.voyage_data.draught
            },
            'timestamp': self.timestamp_sim.isoformat()
        }
    
    def validate(self) -> bool:
        """Validate all vessel data."""
        return (self.static_data.validate() and 
                self.navigation_data.validate() and 
                self.voyage_data.validate())


# Factory functions for creating vessel states
def create_vessel_state(mmsi: int, vessel_name: str, position: Position,
                       vessel_class: VesselClass = VesselClass.CLASS_A,
                       **kwargs) -> "VesselState":
    """Create a vessel state with default values."""
    static_data = VesselStaticData(
        mmsi=mmsi,
        vessel_name=vessel_name,
        vessel_class=vessel_class,
        **{k: v for k, v in kwargs.items() if k in [f.name for f in fields(VesselStaticData)]}
    )

    navigation_data = VesselNavigationData(
        position=position,
        **{k: v for k, v in kwargs.items() if k in [f.name for f in fields(VesselNavigationData)]}
    )

    voyage_data = VesselVoyageData(
        **{k: v for k, v in kwargs.items() if k in [f.name for f in fields(VesselVoyageData)]}
    )
    
    return VesselState(
        static_data=static_data,
        navigation_data=navigation_data,
        voyage_data=voyage_data,
        timestamp_sim=datetime.now()
    )


def create_base_station(mmsi: int, position: Position, **kwargs) -> BaseStationData:
    """Create a base station with default values."""
    return BaseStationData(
        mmsi=mmsi,
        position=position,
        timestamp=datetime.now(),
        **kwargs
    )


def create_aid_to_navigation(mmsi: int, name: str, position: Position, 
                           aid_type: int = 0, **kwargs) -> AidToNavigationData:
    """Create an aid to navigation with default values."""
    return AidToNavigationData(
        mmsi=mmsi,
        name=name,
        position=position,
        aid_type=aid_type,
        **kwargs
    )

