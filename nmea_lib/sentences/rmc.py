"""RMC (Recommended Minimum Navigation Information) sentence implementation."""

from typing import Optional
from dataclasses import dataclass
from ..base import Sentence, TalkerId, SentenceId, PositionSentence, TimeSentence, DateSentence
from ..parser import SentenceParser, SentenceBuilder
from ..types import Position, NMEATime, NMEADate, Speed, Bearing, SpeedUnit, BearingType
from ..types.enums import DataStatus, ModeIndicator, CompassPoint


@dataclass
class RMCMovement:
    """Movement data for RMC sentence."""
    speed: Optional[Speed] = None
    course: Optional[Bearing] = None
    magnetic_variation: Optional[float] = None


@dataclass
class RMCStatus:
    """Status data for RMC sentence."""
    status: DataStatus = DataStatus.VOID
    mode_indicator: ModeIndicator = ModeIndicator.NOT_VALID


@dataclass
class RMCSentence(PositionSentence, TimeSentence, DateSentence):
    """
    RMC - Recommended Minimum Navigation Information
    
    Example: $GPRMC,120044,A,6011.552,N,02501.941,E,000.0,360.0,160705,006.1,E,A*7C
    
    Fields:
    0: UTC Time (HHMMSS.SSS)
    1: Status (A=Active, V=Void)
    2: Latitude (DDMM.MMMM)
    3: Latitude hemisphere (N/S)
    4: Longitude (DDDMM.MMMM)
    5: Longitude hemisphere (E/W)
    6: Speed over ground (knots)
    7: Course over ground (degrees true)
    8: Date (DDMMYY)
    9: Magnetic variation (degrees)
    10: Magnetic variation direction (E/W)
    11: Mode indicator (A/D/E/M/S/N)
    """
    
    # Field indices
    UTC_TIME = 0
    STATUS = 1
    LATITUDE = 2
    LAT_HEMISPHERE = 3
    LONGITUDE = 4
    LON_HEMISPHERE = 5
    SPEED_OVER_GROUND = 6
    COURSE_OVER_GROUND = 7
    DATE = 8
    MAGNETIC_VARIATION = 9
    VARIATION_DIRECTION = 10
    MODE_INDICATOR = 11
    
    def __init__(self, talker_id: TalkerId = TalkerId.GP, sentence_id: SentenceId = SentenceId.RMC):
        """Initialize RMC sentence."""
        super().__init__(talker_id, sentence_id)
        
        # Initialize with empty fields (12 fields total)
        self.fields = [""] * 12
        
        # Default values
        self._time: Optional[NMEATime] = None
        self._position: Optional[Position] = None
        self._date: Optional[NMEADate] = None
        self.movement: RMCMovement = RMCMovement()
        self.status: RMCStatus = RMCStatus()
    
    @classmethod
    def from_sentence(cls, nmea_sentence: str) -> 'RMCSentence':
        """Create RMC sentence from NMEA string."""
        parser = SentenceParser(nmea_sentence)
        
        if parser.sentence_id != SentenceId.RMC:
            raise ValueError(f"Expected RMC sentence, got {parser.sentence_id}")
        
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

        # Status
        status_str = parser.get_field(self.STATUS)
        if status_str:
            try:
                self.status.status = DataStatus(status_str.upper())
            except ValueError:
                self.status.status = DataStatus.VOID

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

        # Speed over ground
        speed_val = parser.get_float_field(self.SPEED_OVER_GROUND)
        if speed_val is not None:
            self.movement.speed = Speed(speed_val, SpeedUnit.KNOTS)

        # Course over ground
        course_val = parser.get_float_field(self.COURSE_OVER_GROUND)
        if course_val is not None:
            self.movement.course = Bearing(course_val, BearingType.TRUE)

        # Date
        date_str = parser.get_field(self.DATE)
        if date_str:
            try:
                self._date = NMEADate.from_nmea(date_str)
            except ValueError:
                self._date = None

        # Magnetic variation
        variation_val = parser.get_float_field(self.MAGNETIC_VARIATION)
        variation_dir = parser.get_field(self.VARIATION_DIRECTION)

        if variation_val is not None and variation_dir:
            try:
                variation_direction = CompassPoint(variation_dir.upper())
                # Apply sign based on direction (East is positive, West is negative)
                self.movement.magnetic_variation = (variation_val if variation_direction == CompassPoint.EAST
                                                     else -variation_val)
            except ValueError:
                self.movement.magnetic_variation = None

        # Mode indicator
        mode_str = parser.get_field(self.MODE_INDICATOR)
        if mode_str:
            try:
                self.status.mode_indicator = ModeIndicator(mode_str.upper())
            except ValueError:
                self.status.mode_indicator = ModeIndicator.NOT_VALID
    
    def to_sentence(self) -> str:
        """Convert to NMEA sentence string."""
        builder = SentenceBuilder(self.talker_id, self.sentence_id)

        # Time
        if self._time:
            builder.add_field(self._time.to_nmea())
        else:
            builder.add_field("")

        # Status
        builder.add_field(self.status.status.value)

        # Position
        if self._position:
            lat_str, lat_hem, lon_str, lon_hem = self._position.to_nmea()
            builder.add_field(lat_str)
            builder.add_field(lat_hem)
            builder.add_field(lon_str)
            builder.add_field(lon_hem)
        else:
            builder.add_field("").add_field("").add_field("").add_field("")

        # Speed over ground
        if self.movement.speed:
            builder.add_float_field(self.movement.speed.value, 1)
        else:
            builder.add_field("")

        # Course over ground
        if self.movement.course:
            builder.add_float_field(self.movement.course.value, 1)
        else:
            builder.add_field("")

        # Date
        if self._date:
            builder.add_field(self._date.to_nmea())
        else:
            builder.add_field("")

        # Magnetic variation
        if self.movement.magnetic_variation is not None:
            variation_direction = CompassPoint.EAST if self.movement.magnetic_variation >= 0 else CompassPoint.WEST
            builder.add_float_field(abs(self.movement.magnetic_variation), 1)
            builder.add_field(variation_direction.value)
        else:
            builder.add_field("").add_field("")

        # Mode indicator
        builder.add_field(self.status.mode_indicator.value)

        return builder.build()

    # Property accessors
    def get_time(self) -> Optional[str]:
        """Get time in HHMMSS.SSS format."""
        return self._time.to_nmea() if self._time else None

    def set_time(self, time_input: NMEATime | str) -> None:
        """Set time from NMEATime object or HHMMSS.SSS string."""
        if isinstance(time_input, NMEATime):
            self._time = time_input
        elif isinstance(time_input, str):
            if time_input:
                try:
                    self._time = NMEATime.from_nmea(time_input)
                except ValueError:
                    self._time = None  # Or handle error appropriately
            else:
                self._time = None
        elif time_input is None:
            self._time = None
        else:
            raise TypeError(f"Unsupported type for time_input: {type(time_input)}. Expected NMEATime or str.")

    def get_date(self) -> Optional[str]:
        """Get date in DDMMYY format."""
        return self._date.to_nmea() if self._date else None

    def set_date(self, date_input: NMEADate | str) -> None:
        """Set date from NMEADate object or DDMMYY string."""
        if isinstance(date_input, NMEADate):
            self._date = date_input
        elif isinstance(date_input, str):
            if date_input:
                try:
                    self._date = NMEADate.from_nmea(date_input)
                except ValueError:
                    self._date = None  # Or handle error appropriately
            else:
                self._date = None
        elif date_input is None:
            self._date = None
        else:
            raise TypeError(f"Unsupported type for date_input: {type(date_input)}. Expected NMEADate or str.")

    def get_latitude(self) -> Optional[float]:
        """Get latitude in decimal degrees."""
        return self._position.latitude if self._position else None

    def get_longitude(self) -> Optional[float]:
        """Get longitude in decimal degrees."""
        return self._position.longitude if self._position else None

    def set_position(self, latitude: float, longitude: float) -> None:
        """Set position coordinates."""
        self._position = Position(latitude, longitude)

    def get_status(self) -> DataStatus:
        """Get data status."""
        return self.status.status

    def set_status(self, status: DataStatus) -> None:
        """Set data status."""
        self.status.status = status

    def get_speed(self) -> Optional[Speed]:
        """Get speed over ground."""
        return self.movement.speed

    def set_speed(self, speed: Speed) -> None:
        """Set speed over ground."""
        self.movement.speed = speed

    def get_course(self) -> Optional[Bearing]:
        """Get course over ground."""
        return self.movement.course

    def set_course(self, course: Bearing) -> None:
        """Set course over ground."""
        self.movement.course = course

    def get_magnetic_variation(self) -> Optional[float]:
        """Get magnetic variation in degrees (positive=East, negative=West)."""
        return self.movement.magnetic_variation

    def set_magnetic_variation(self, variation: Optional[float]) -> None:
        """Set magnetic variation in degrees (positive=East, negative=West)."""
        self.movement.magnetic_variation = variation

    def get_mode_indicator(self) -> ModeIndicator:
        """Get mode indicator."""
        return self.status.mode_indicator

    def set_mode_indicator(self, mode: ModeIndicator) -> None:
        """Set mode indicator."""
        self.status.mode_indicator = mode

    def is_valid_fix(self) -> bool:
        """Check if the sentence represents a valid GPS fix."""
        return (self.status.status == DataStatus.ACTIVE and
                self._position is not None and
                self.status.mode_indicator != ModeIndicator.NOT_VALID)

