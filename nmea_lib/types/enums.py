"""Additional enumerations for NMEA sentence handling."""

from enum import Enum


class CompassPoint(Enum):
    """Compass point enumeration for magnetic variation."""

    EAST = "E"
    WEST = "W"


class FaaMode(Enum):
    """FAA mode indicator enumeration."""

    AUTONOMOUS = "A"
    DIFFERENTIAL = "D"
    ESTIMATED = "E"
    MANUAL = "M"
    SIMULATED = "S"
    NOT_VALID = "N"


class NavStatus(Enum):
    """Navigation status enumeration."""

    SAFE = "S"
    CAUTION = "C"
    UNSAFE = "U"
    NOT_VALID = "V"


class GsaMode(Enum):
    """GSA mode enumeration."""

    MANUAL = "M"
    AUTOMATIC = "A"


class GsaFixType(Enum):
    """GSA fix type enumeration."""

    NO_FIX = 1
    FIX_2D = 2
    FIX_3D = 3


class DataStatus(Enum):
    """Data status enumeration."""

    ACTIVE = "A"
    VOID = "V"


class ModeIndicator(Enum):
    """Mode indicator enumeration."""

    AUTONOMOUS = "A"
    DIFFERENTIAL = "D"
    ESTIMATED = "E"
    MANUAL = "M"
    SIMULATED = "S"
    NOT_VALID = "N"
