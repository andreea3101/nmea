"""AIS constants and enumerations for NMEA 0183 simulator."""

from enum import Enum, IntEnum
from typing import Dict, List


class AISMessageType(IntEnum):
    """AIS message types supported by the simulator."""
    POSITION_REPORT_CLASS_A = 1
    POSITION_REPORT_SCHEDULED_CLASS_A = 2
    POSITION_REPORT_RESPONSE_CLASS_A = 3
    BASE_STATION_REPORT = 4
    STATIC_VOYAGE_DATA = 5
    POSITION_REPORT_CLASS_B = 18
    EXTENDED_CLASS_B_REPORT = 19
    AIDS_TO_NAVIGATION = 21
    STATIC_DATA_REPORT_CLASS_B = 24


class NavigationStatus(IntEnum):
    """Navigation status values for AIS messages."""
    UNDER_WAY_USING_ENGINE = 0
    AT_ANCHOR = 1
    NOT_UNDER_COMMAND = 2
    RESTRICTED_MANOEUVRABILITY = 3
    CONSTRAINED_BY_DRAUGHT = 4
    MOORED = 5
    AGROUND = 6
    ENGAGED_IN_FISHING = 7
    UNDER_WAY_SAILING = 8
    RESERVED_9 = 9
    RESERVED_10 = 10
    POWER_DRIVEN_VESSEL_TOWING_ASTERN = 11
    POWER_DRIVEN_VESSEL_PUSHING_AHEAD = 12
    RESERVED_13 = 13
    AIS_SART = 14
    DEFAULT = 15


class ShipType(IntEnum):
    """Ship and cargo type values."""
    NOT_AVAILABLE = 0
    
    # Wing In Ground (WIG) craft
    WIG_ALL_SHIPS = 20
    WIG_HAZARDOUS_CAT_A = 21
    WIG_HAZARDOUS_CAT_B = 22
    WIG_HAZARDOUS_CAT_C = 23
    WIG_HAZARDOUS_CAT_D = 24
    WIG_RESERVED_1 = 25
    WIG_RESERVED_2 = 26
    WIG_RESERVED_3 = 27
    WIG_RESERVED_4 = 28
    WIG_NO_ADDITIONAL_INFO = 29
    
    # Fishing vessels
    FISHING = 30
    
    # Towing vessels
    TOWING = 31
    TOWING_LENGTH_EXCEEDS_200M = 32
    
    # Dredging or underwater operations
    DREDGING_OR_UNDERWATER_OPS = 33
    
    # Diving operations
    DIVING_OPS = 34
    
    # Military operations
    MILITARY_OPS = 35
    
    # Sailing
    SAILING = 36
    
    # Pleasure craft
    PLEASURE_CRAFT = 37
    
    # High speed craft (HSC)
    HSC_ALL_SHIPS = 40
    HSC_HAZARDOUS_CAT_A = 41
    HSC_HAZARDOUS_CAT_B = 42
    HSC_HAZARDOUS_CAT_C = 43
    HSC_HAZARDOUS_CAT_D = 44
    HSC_RESERVED_1 = 45
    HSC_RESERVED_2 = 46
    HSC_RESERVED_3 = 47
    HSC_RESERVED_4 = 48
    HSC_NO_ADDITIONAL_INFO = 49
    
    # Pilot vessel
    PILOT_VESSEL = 50
    
    # Search and rescue vessel
    SEARCH_AND_RESCUE = 51
    
    # Tug
    TUG = 52
    
    # Port tender
    PORT_TENDER = 53
    
    # Anti-pollution equipment
    ANTI_POLLUTION = 54
    
    # Law enforcement
    LAW_ENFORCEMENT = 55
    
    # Medical transport
    MEDICAL_TRANSPORT = 58
    
    # Passenger ships
    PASSENGER_ALL_SHIPS = 60
    PASSENGER_HAZARDOUS_CAT_A = 61
    PASSENGER_HAZARDOUS_CAT_B = 62
    PASSENGER_HAZARDOUS_CAT_C = 63
    PASSENGER_HAZARDOUS_CAT_D = 64
    PASSENGER_RESERVED_1 = 65
    PASSENGER_RESERVED_2 = 66
    PASSENGER_RESERVED_3 = 67
    PASSENGER_RESERVED_4 = 68
    PASSENGER_NO_ADDITIONAL_INFO = 69
    
    # Cargo ships
    CARGO_ALL_SHIPS = 70
    CARGO_HAZARDOUS_CAT_A = 71
    CARGO_HAZARDOUS_CAT_B = 72
    CARGO_HAZARDOUS_CAT_C = 73
    CARGO_HAZARDOUS_CAT_D = 74
    CARGO_RESERVED_1 = 75
    CARGO_RESERVED_2 = 76
    CARGO_RESERVED_3 = 77
    CARGO_RESERVED_4 = 78
    CARGO_NO_ADDITIONAL_INFO = 79
    
    # Tanker
    TANKER_ALL_SHIPS = 80
    TANKER_HAZARDOUS_CAT_A = 81
    TANKER_HAZARDOUS_CAT_B = 82
    TANKER_HAZARDOUS_CAT_C = 83
    TANKER_HAZARDOUS_CAT_D = 84
    TANKER_RESERVED_1 = 85
    TANKER_RESERVED_2 = 86
    TANKER_RESERVED_3 = 87
    TANKER_RESERVED_4 = 88
    TANKER_NO_ADDITIONAL_INFO = 89
    
    # Other types
    OTHER_ALL_SHIPS = 90
    OTHER_HAZARDOUS_CAT_A = 91
    OTHER_HAZARDOUS_CAT_B = 92
    OTHER_HAZARDOUS_CAT_C = 93
    OTHER_HAZARDOUS_CAT_D = 94
    OTHER_RESERVED_1 = 95
    OTHER_RESERVED_2 = 96
    OTHER_RESERVED_3 = 97
    OTHER_RESERVED_4 = 98
    OTHER_NO_ADDITIONAL_INFO = 99


class EPFDType(IntEnum):
    """Electronic Position Fixing Device types."""
    UNDEFINED = 0
    GPS = 1
    GLONASS = 2
    COMBINED_GPS_GLONASS = 3
    LORAN_C = 4
    CHAYKA = 5
    INTEGRATED_NAVIGATION_SYSTEM = 6
    SURVEYED = 7
    GALILEO = 8
    INTERNAL_GNSS = 15


class AidType(IntEnum):
    """Aid to Navigation types."""
    DEFAULT = 0
    REFERENCE_POINT = 1
    RACON = 2
    FIXED_STRUCTURE_OFF_SHORE = 3
    SPARE = 4
    LIGHT_WITHOUT_SECTORS = 5
    LIGHT_WITH_SECTORS = 6
    LEADING_LIGHT_FRONT = 7
    LEADING_LIGHT_REAR = 8
    BEACON_CARDINAL_N = 9
    BEACON_CARDINAL_E = 10
    BEACON_CARDINAL_S = 11
    BEACON_CARDINAL_W = 12
    BEACON_PORT_HAND = 13
    BEACON_STARBOARD_HAND = 14
    BEACON_PREFERRED_CHANNEL_PORT_HAND = 15
    BEACON_PREFERRED_CHANNEL_STARBOARD_HAND = 16
    BEACON_ISOLATED_DANGER = 17
    BEACON_SAFE_WATER = 18
    BEACON_SPECIAL_MARK = 19
    CARDINAL_MARK_N = 20
    CARDINAL_MARK_E = 21
    CARDINAL_MARK_S = 22
    CARDINAL_MARK_W = 23
    PORT_HAND_MARK = 24
    STARBOARD_HAND_MARK = 25
    PREFERRED_CHANNEL_PORT_HAND = 26
    PREFERRED_CHANNEL_STARBOARD_HAND = 27
    ISOLATED_DANGER = 28
    SAFE_WATER = 29
    SPECIAL_MARK = 30
    LIGHT_VESSEL_LANBY_RIGS = 31


class VesselClass(Enum):
    """Vessel class for AIS transmission."""
    CLASS_A = "A"
    CLASS_B = "B"


# AIS message transmission intervals (in seconds)
AIS_MESSAGE_INTERVALS: Dict[int, float] = {
    1: 2.0,     # Position Report Class A - every 2-10 seconds (using 2s)
    2: 2.0,     # Position Report Scheduled Class A
    3: 2.0,     # Position Report Response Class A
    4: 10.0,    # Base Station Report - every 10 seconds
    5: 360.0,   # Static & Voyage Data - every 6 minutes
    18: 3.0,    # Position Report Class B - every 3-10 seconds (using 3s)
    19: 30.0,   # Extended Class B Report - every 30 seconds
    21: 180.0,  # Aids-to-Navigation - every 3 minutes
    24: 360.0,  # Static Data Report Class B - every 6 minutes
}

# AIS message bit lengths
AIS_MESSAGE_LENGTHS: Dict[int, int] = {
    1: 168,   # Type 1: Position Report Class A
    2: 168,   # Type 2: Position Report Scheduled Class A
    3: 168,   # Type 3: Position Report Response Class A
    4: 168,   # Type 4: Base Station Report
    5: 424,   # Type 5: Static & Voyage Data
    18: 168,  # Type 18: Position Report Class B
    19: 312,  # Type 19: Extended Class B Report
    21: 272,  # Type 21: Aids-to-Navigation (minimum)
    24: 168,  # Type 24: Static Data Report Class B (Part A)
}

# 6-bit ASCII encoding table for AIS
AIS_6BIT_ASCII: List[str] = [
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?',
    '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
    'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_',
    '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
]

# Reverse lookup for 6-bit ASCII decoding
AIS_ASCII_6BIT: Dict[str, int] = {char: idx for idx, char in enumerate(AIS_6BIT_ASCII)}

# Default MMSI ranges
MMSI_RANGES = {
    'ship': (200000000, 799999999),
    'coastal_station': (1000000, 9999999),
    'group_ship': (800000000, 899999999),
    'navigation_aid': (990000000, 999999999),
    'search_rescue': (970000000, 979999999),
    'craft_parent_ship': (980000000, 989999999),
}

# Channel designators for AIVDM sentences
AIS_CHANNELS = ['A', 'B']

# Maximum values for various AIS fields
AIS_MAX_VALUES = {
    'mmsi': 999999999,
    'latitude': 91.0,   # 91 degrees = not available
    'longitude': 181.0, # 181 degrees = not available
    'sog': 102.3,       # 102.3 knots = not available
    'cog': 360.0,       # 360 degrees = not available
    'heading': 511,     # 511 = not available
    'rot': 128,         # 128 = not available
    'draught': 25.5,    # 25.5 meters = not available
}

# Default values for unavailable data
AIS_NOT_AVAILABLE = {
    'latitude': 91.0,
    'longitude': 181.0,
    'sog': 102.3,
    'cog': 360.0,
    'heading': 511,
    'rot': 128,
    'draught': 25.5,
    'eta_month': 0,
    'eta_day': 0,
    'eta_hour': 24,
    'eta_minute': 60,
}

