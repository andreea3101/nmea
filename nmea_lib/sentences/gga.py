"""GGA (Global Positioning System Fix Data) sentence implementation."""

from typing import Optional
from dataclasses import dataclass
from ..base import Sentence, TalkerId, SentenceId, GpsFixQuality, PositionSentence, TimeSentence
from ..parser import SentenceParser, SentenceBuilder
from ..types import Position, Distance, DistanceUnit # NMEATime removed from here for specific import
from ..types.datetime import NMEATime # Specific import for NMEATime


@dataclass
class GGASentence(PositionSentence, TimeSentence):
    """
    GGA - Global Positioning System Fix Data
    
    Example: $GPGGA,120044,6011.552,N,02501.941,E,1,08,2.0,28.0,M,19.6,M,,*79
    
    Fields:
    0: UTC Time (HHMMSS.SSS)
    1: Latitude (DDMM.MMMM)
    2: Latitude hemisphere (N/S)
    3: Longitude (DDDMM.MMMM)
    4: Longitude hemisphere (E/W)
    5: GPS fix quality (0-8)
    6: Number of satellites in use
    7: Horizontal dilution of precision
    8: Antenna altitude above mean sea level
    9: Altitude units (M=meters)
    10: Geoidal separation
    11: Geoidal separation units (M=meters)
    12: Age of DGPS data (seconds)
    13: DGPS station ID
    """
    
    # Field indices
    UTC_TIME = 0
    LATITUDE = 1
    LAT_HEMISPHERE = 2
    LONGITUDE = 3
    LON_HEMISPHERE = 4
    FIX_QUALITY = 5
    SATELLITES_IN_USE = 6
    HORIZONTAL_DILUTION = 7
    ALTITUDE = 8
    ALTITUDE_UNITS = 9
    GEOIDAL_HEIGHT = 10
    HEIGHT_UNITS = 11
    DGPS_AGE = 12
    DGPS_STATION_ID = 13
    
    def __init__(self, talker_id: TalkerId = TalkerId.GP, sentence_id: SentenceId = SentenceId.GGA):
        """Initialize GGA sentence."""
        super().__init__(talker_id, sentence_id)
        
        # Initialize with empty fields (14 fields total)
        self.fields = [""] * 14
        
        # Default values
        self._time: Optional[NMEATime] = None
        self._position: Optional[Position] = None
        self._fix_quality: GpsFixQuality = GpsFixQuality.INVALID
        self._satellites_in_use: int = 0
        self._horizontal_dilution: Optional[float] = None
        self._altitude: Optional[Distance] = None
        self._geoidal_height: Optional[Distance] = None
        self._dgps_age: Optional[float] = None
        self._dgps_station_id: Optional[str] = None
    
    @classmethod
    def from_sentence(cls, nmea_sentence: str) -> 'GGASentence':
        """Create GGA sentence from NMEA string."""
        parser = SentenceParser(nmea_sentence)
        
        if parser.sentence_id != SentenceId.GGA:
            raise ValueError(f"Expected GGA sentence, got {parser.sentence_id}")
        
        sentence = cls(parser.talker_id, parser.sentence_id)
        sentence.fields = parser.fields.copy()
        
        # Parse fields
        sentence._parse_fields(parser)
        
        return sentence
    
    def _parse_fields(self, parser: SentenceParser) -> None:
        """Parse fields from parser."""
        # Time
        time_str = parser.get_field(self.UTC_TIME)
        if time_str:
            try:
                self._time = NMEATime.from_nmea(time_str)
            except ValueError:
                self._time = None
        
        # Position
        lat_str = parser.get_field(self.LATITUDE)
        lat_hem = parser.get_field(self.LAT_HEMISPHERE)
        lon_str = parser.get_field(self.LONGITUDE)
        lon_hem = parser.get_field(self.LON_HEMISPHERE)
        
        if all([lat_str, lat_hem, lon_str, lon_hem]):
            try:
                self._position = Position.from_nmea(lat_str, lat_hem, lon_str, lon_hem)
            except ValueError:
                self._position = None
        
        # Fix quality
        fix_quality_val = parser.get_int_field(self.FIX_QUALITY)
        if fix_quality_val is not None:
            try:
                self._fix_quality = GpsFixQuality(fix_quality_val)
            except ValueError:
                self._fix_quality = GpsFixQuality.INVALID
        
        # Satellites in use
        self._satellites_in_use = parser.get_int_field(self.SATELLITES_IN_USE) or 0
        
        # Horizontal dilution
        self._horizontal_dilution = parser.get_float_field(self.HORIZONTAL_DILUTION)
        
        # Altitude
        altitude_val = parser.get_float_field(self.ALTITUDE)
        altitude_unit = parser.get_field(self.ALTITUDE_UNITS)
        if altitude_val is not None:
            unit = DistanceUnit.METERS if altitude_unit == "M" else DistanceUnit.METERS
            self._altitude = Distance(altitude_val, unit)
        
        # Geoidal height
        geoidal_val = parser.get_float_field(self.GEOIDAL_HEIGHT)
        geoidal_unit = parser.get_field(self.HEIGHT_UNITS)
        if geoidal_val is not None:
            unit = DistanceUnit.METERS if geoidal_unit == "M" else DistanceUnit.METERS
            self._geoidal_height = Distance(geoidal_val, unit)
        
        # DGPS data
        self._dgps_age = parser.get_float_field(self.DGPS_AGE)
        dgps_id = parser.get_field(self.DGPS_STATION_ID)
        self._dgps_station_id = dgps_id if dgps_id else None
    
    def to_sentence(self) -> str:
        """Convert to NMEA sentence string."""
        builder = SentenceBuilder(self.talker_id, self.sentence_id)
        
        # Time
        if self._time:
            builder.add_field(self._time.to_nmea())
        else:
            builder.add_field("")
        
        # Position
        if self._position:
            lat_str, lat_hem, lon_str, lon_hem = self._position.to_nmea()
            builder.add_field(lat_str)
            builder.add_field(lat_hem)
            builder.add_field(lon_str)
            builder.add_field(lon_hem)
        else:
            builder.add_field("").add_field("").add_field("").add_field("")
        
        # Fix quality
        builder.add_field(self._fix_quality.value)
        
        # Satellites in use
        builder.add_field(self._satellites_in_use if self._satellites_in_use > 0 else "")
        
        # Horizontal dilution
        builder.add_float_field(self._horizontal_dilution, 1)
        
        # Altitude
        if self._altitude:
            builder.add_float_field(self._altitude.value, 1)
            builder.add_field("M")
        else:
            builder.add_field("").add_field("")
        
        # Geoidal height
        if self._geoidal_height:
            builder.add_float_field(self._geoidal_height.value, 1)
            builder.add_field("M")
        else:
            builder.add_field("").add_field("")
        
        # DGPS data
        builder.add_float_field(self._dgps_age, 1)
        builder.add_field(self._dgps_station_id or "")
        
        return builder.build()
    
    # Property accessors
    def get_time(self) -> Optional[NMEATime]: # Return NMEATime object
        """Get time as NMEATime object."""
        return self._time
    
    def set_time(self, time_obj: Optional[NMEATime]) -> None: # Accept NMEATime object or None
        """Set time using NMEATime object."""
        self._time = time_obj
    
    def get_latitude(self) -> Optional[float]:
        """Get latitude in decimal degrees."""
        return self._position.latitude if self._position else None
    
    def get_longitude(self) -> Optional[float]:
        """Get longitude in decimal degrees."""
        return self._position.longitude if self._position else None
    
    def set_position(self, latitude: float, longitude: float) -> None:
        """Set position coordinates."""
        self._position = Position(latitude, longitude)
    
    def get_fix_quality(self) -> GpsFixQuality:
        """Get GPS fix quality."""
        return self._fix_quality
    
    def set_fix_quality(self, quality: GpsFixQuality) -> None:
        """Set GPS fix quality."""
        self._fix_quality = quality
    
    def get_satellites_in_use(self) -> int:
        """Get number of satellites in use."""
        return self._satellites_in_use
    
    def set_satellites_in_use(self, count: int) -> None:
        """Set number of satellites in use."""
        self._satellites_in_use = max(0, count)
    
    def get_horizontal_dilution(self) -> Optional[float]:
        """Get horizontal dilution of precision."""
        return self._horizontal_dilution
    
    def set_horizontal_dilution(self, hdop: Optional[float]) -> None:
        """Set horizontal dilution of precision."""
        self._horizontal_dilution = hdop
    
    def get_altitude(self) -> Optional[Distance]:
        """Get antenna altitude."""
        return self._altitude
    
    def set_altitude(self, altitude: Distance) -> None:
        """Set antenna altitude."""
        self._altitude = altitude
    
    def get_geoidal_height(self) -> Optional[Distance]:
        """Get geoidal separation."""
        return self._geoidal_height
    
    def set_geoidal_height(self, height: Distance) -> None:
        """Set geoidal separation."""
        self._geoidal_height = height
    
    def get_dgps_age(self) -> Optional[float]:
        """Get age of DGPS data in seconds."""
        return self._dgps_age
    
    def set_dgps_age(self, age: Optional[float]) -> None:
        """Set age of DGPS data in seconds."""
        self._dgps_age = age
    
    def get_dgps_station_id(self) -> Optional[str]:
        """Get DGPS station ID."""
        return self._dgps_station_id
    
    def set_dgps_station_id(self, station_id: Optional[str]) -> None:
        """Set DGPS station ID."""
        self._dgps_station_id = station_id

