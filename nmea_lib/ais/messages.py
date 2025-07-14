"""AIS binary message encoders for all supported message types."""

import math
from typing import Dict, Any, Tuple
from datetime import datetime

from nmea_lib.types.vessel import (
    VesselState, BaseStationData, AidToNavigationData
)
from nmea_lib.ais.constants import (
    AISMessageType, AIS_NOT_AVAILABLE, AIS_MAX_VALUES
)


class AISBinaryEncoder:
    """Encodes vessel data into AIS binary message format."""
    
    @staticmethod
    def _encode_bits(value: int, bits: int) -> str:
        """Encode integer value as binary string with specified bit length."""
        if value < 0:
            # Handle signed integers using two's complement
            value = (1 << bits) + value
        return format(value, f'0{bits}b')
    
    @staticmethod
    def _encode_string(text: str, max_chars: int) -> str:
        """Encode string as 6-bit ASCII binary."""
        # Pad or truncate to max_chars
        text = text.ljust(max_chars)[:max_chars]
        binary = ""
        for char in text:
            # Convert to 6-bit ASCII (@ = 0, A = 1, etc.)
            if char == ' ':
                ascii_val = 32  # Space
            else:
                ascii_val = ord(char.upper())
            
            # Map to 6-bit range
            if 32 <= ascii_val <= 95:
                six_bit = ascii_val - 32
            else:
                six_bit = 0  # Default to @
            
            binary += AISBinaryEncoder._encode_bits(six_bit, 6)
        return binary
    
    @staticmethod
    def _encode_latitude(lat: float) -> str:
        """Encode latitude in AIS format (1/10000 minute resolution)."""
        if lat == AIS_NOT_AVAILABLE['latitude']:
            return AISBinaryEncoder._encode_bits(0x3412140, 27)  # Not available
        
        # Convert to 1/10000 minutes
        lat_minutes = lat * 600000
        lat_int = int(round(lat_minutes))
        
        # Clamp to valid range
        lat_int = max(-324000000, min(324000000, lat_int))
        
        return AISBinaryEncoder._encode_bits(lat_int, 27)
    
    @staticmethod
    def _encode_longitude(lon: float) -> str:
        """Encode longitude in AIS format (1/10000 minute resolution)."""
        if lon == AIS_NOT_AVAILABLE['longitude']:
            return AISBinaryEncoder._encode_bits(0x6791AC0, 28)  # Not available
        
        # Convert to 1/10000 minutes
        lon_minutes = lon * 600000
        lon_int = int(round(lon_minutes))
        
        # Clamp to valid range
        lon_int = max(-648000000, min(648000000, lon_int))
        
        return AISBinaryEncoder._encode_bits(lon_int, 28)
    
    @staticmethod
    def _encode_sog(sog: float) -> str:
        """Encode speed over ground (0.1 knot resolution)."""
        if sog >= AIS_MAX_VALUES['sog']:
            return AISBinaryEncoder._encode_bits(1023, 10)  # Not available
        
        sog_int = int(round(sog * 10))
        sog_int = max(0, min(1022, sog_int))
        return AISBinaryEncoder._encode_bits(sog_int, 10)
    
    @staticmethod
    def _encode_cog(cog: float) -> str:
        """Encode course over ground (0.1 degree resolution)."""
        if cog >= AIS_MAX_VALUES['cog']:
            return AISBinaryEncoder._encode_bits(3600, 12)  # Not available
        
        cog_int = int(round(cog * 10))
        cog_int = max(0, min(3599, cog_int))
        return AISBinaryEncoder._encode_bits(cog_int, 12)
    
    @staticmethod
    def _encode_heading(heading: int) -> str:
        """Encode true heading."""
        if heading >= AIS_MAX_VALUES['heading']:
            return AISBinaryEncoder._encode_bits(511, 9)  # Not available
        
        heading = max(0, min(359, heading))
        return AISBinaryEncoder._encode_bits(heading, 9)
    
    @staticmethod
    def _encode_rot(rot: int) -> str:
        """Encode rate of turn."""
        if rot == AIS_MAX_VALUES['rot']:
            return AISBinaryEncoder._encode_bits(128, 8)  # Not available
        
        # Rate of turn encoding: ROT_AIS = 4.733 * sqrt(ROT_sensor)
        if rot == 0:
            rot_ais = 0
        elif rot > 0:
            rot_ais = int(round(4.733 * math.sqrt(abs(rot))))
            rot_ais = min(127, rot_ais)
        else:
            rot_ais = -int(round(4.733 * math.sqrt(abs(rot))))
            rot_ais = max(-127, rot_ais)
        
        return AISBinaryEncoder._encode_bits(rot_ais, 8)

    @staticmethod
    def _encode_altitude(alt: int) -> str:
        """Encode altitude for SAR aircraft (meters)."""
        if alt >= 4095:
            return AISBinaryEncoder._encode_bits(4095, 12)  # Not available or >= 4094m
        return AISBinaryEncoder._encode_bits(alt, 12)

    @staticmethod
    def _encode_sog_sar(sog: float) -> str:
        """Encode speed over ground for SAR aircraft (knots)."""
        if sog >= 1023:
            return AISBinaryEncoder._encode_bits(1023, 10)  # Not available or >= 1022 knots
        sog_int = int(round(sog))
        sog_int = max(0, min(1022, sog_int))
        return AISBinaryEncoder._encode_bits(sog_int, 10)
    
    @staticmethod
    def encode_type_1(vessel: VesselState) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 1: Position Report Class A."""
        nav = vessel.navigation_data
        
        # Build binary message
        binary = ""
        binary += AISBinaryEncoder._encode_bits(1, 6)  # Message type
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Repeat indicator
        binary += AISBinaryEncoder._encode_bits(vessel.mmsi, 30)  # MMSI
        binary += AISBinaryEncoder._encode_bits(nav.nav_status.value, 4)  # Navigation status
        binary += AISBinaryEncoder._encode_rot(nav.rot)  # Rate of turn
        binary += AISBinaryEncoder._encode_sog(nav.sog)  # Speed over ground
        binary += AISBinaryEncoder._encode_bits(nav.position_accuracy, 1)  # Position accuracy
        binary += AISBinaryEncoder._encode_longitude(nav.position.longitude)  # Longitude
        binary += AISBinaryEncoder._encode_latitude(nav.position.latitude)  # Latitude
        binary += AISBinaryEncoder._encode_cog(nav.cog)  # Course over ground
        binary += AISBinaryEncoder._encode_heading(nav.heading)  # True heading
        binary += AISBinaryEncoder._encode_bits(nav.timestamp, 6)  # Time stamp
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Maneuver indicator
        binary += AISBinaryEncoder._encode_bits(0, 3)  # Spare
        binary += AISBinaryEncoder._encode_bits(nav.raim, 1)  # RAIM
        binary += AISBinaryEncoder._encode_bits(nav.radio_status, 19)  # Radio status
        
        # Input data for trace logging
        input_data = {
            'message_type': 1,
            'mmsi': vessel.mmsi,
            'nav_status': nav.nav_status.value,
            'rot': nav.rot,
            'sog': nav.sog,
            'position_accuracy': nav.position_accuracy,
            'longitude': nav.position.longitude,
            'latitude': nav.position.latitude,
            'cog': nav.cog,
            'heading': nav.heading,
            'timestamp': nav.timestamp,
            'raim': nav.raim,
            'radio_status': nav.radio_status
        }
        
        return binary, input_data
    
    @staticmethod
    def encode_type_9(vessel: VesselState) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 9: Standard SAR Aircraft Position Report."""
        nav = vessel.navigation_data

        # Build binary message
        binary = ""
        binary += AISBinaryEncoder._encode_bits(9, 6)  # Message type
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Repeat indicator
        binary += AISBinaryEncoder._encode_bits(vessel.mmsi, 30)  # MMSI
        binary += AISBinaryEncoder._encode_altitude(nav.altitude)  # Altitude
        binary += AISBinaryEncoder._encode_sog_sar(nav.sog)  # Speed over ground
        binary += AISBinaryEncoder._encode_bits(nav.position_accuracy, 1)  # Position accuracy
        binary += AISBinaryEncoder._encode_longitude(nav.position.longitude)  # Longitude
        binary += AISBinaryEncoder._encode_latitude(nav.position.latitude)  # Latitude
        binary += AISBinaryEncoder._encode_cog(nav.cog)  # Course over ground
        binary += AISBinaryEncoder._encode_heading(nav.heading)  # True heading
        binary += AISBinaryEncoder._encode_bits(nav.timestamp, 6)  # Time stamp
        binary += AISBinaryEncoder._encode_bits(0, 8)  # Regional reserved
        binary += AISBinaryEncoder._encode_bits(0, 1)  # DTE
        binary += AISBinaryEncoder._encode_bits(0, 3)  # Spare
        binary += AISBinaryEncoder._encode_bits(0, 1)  # Assigned mode
        binary += AISBinaryEncoder._encode_bits(nav.raim, 1)  # RAIM
        binary += AISBinaryEncoder._encode_bits(nav.radio_status, 20)  # Radio status

        # Input data for trace logging
        input_data = {
            'message_type': 9,
            'mmsi': vessel.mmsi,
            'altitude': nav.altitude,
            'sog': nav.sog,
            'position_accuracy': nav.position_accuracy,
            'longitude': nav.position.longitude,
            'latitude': nav.position.latitude,
            'cog': nav.cog,
            'heading': nav.heading,
            'timestamp': nav.timestamp,
            'raim': nav.raim,
            'radio_status': nav.radio_status
        }

        return binary, input_data

    @staticmethod
    def encode_type_2(vessel: VesselState) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 2: Position Report Scheduled Class A."""
        # Type 2 has same format as Type 1, just different message type
        binary, input_data = AISBinaryEncoder.encode_type_1(vessel)
        # Change message type to 2
        binary = AISBinaryEncoder._encode_bits(2, 6) + binary[6:]
        input_data['message_type'] = 2
        return binary, input_data
    
    @staticmethod
    def encode_type_3(vessel: VesselState) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 3: Position Report Response Class A."""
        # Type 3 has same format as Type 1, just different message type
        binary, input_data = AISBinaryEncoder.encode_type_1(vessel)
        # Change message type to 3
        binary = AISBinaryEncoder._encode_bits(3, 6) + binary[6:]
        input_data['message_type'] = 3
        return binary, input_data
    
    @staticmethod
    def encode_type_4(base_station: BaseStationData) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 4: Base Station Report."""
        # Build binary message
        binary = ""
        binary += AISBinaryEncoder._encode_bits(4, 6)  # Message type
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Repeat indicator
        binary += AISBinaryEncoder._encode_bits(base_station.mmsi, 30)  # MMSI
        
        # UTC time
        utc_time = base_station.timestamp
        binary += AISBinaryEncoder._encode_bits(utc_time.year, 14)  # Year
        binary += AISBinaryEncoder._encode_bits(utc_time.month, 4)  # Month
        binary += AISBinaryEncoder._encode_bits(utc_time.day, 5)  # Day
        binary += AISBinaryEncoder._encode_bits(utc_time.hour, 5)  # Hour
        binary += AISBinaryEncoder._encode_bits(utc_time.minute, 6)  # Minute
        binary += AISBinaryEncoder._encode_bits(utc_time.second, 6)  # Second
        
        binary += AISBinaryEncoder._encode_bits(1, 1)  # Position accuracy (high)
        binary += AISBinaryEncoder._encode_longitude(base_station.position.longitude)  # Longitude
        binary += AISBinaryEncoder._encode_latitude(base_station.position.latitude)  # Latitude
        binary += AISBinaryEncoder._encode_bits(base_station.epfd_type.value, 4)  # EPFD type
        binary += AISBinaryEncoder._encode_bits(0, 10)  # Spare
        binary += AISBinaryEncoder._encode_bits(base_station.raim, 1)  # RAIM
        binary += AISBinaryEncoder._encode_bits(base_station.radio_status, 19)  # Radio status
        
        input_data = {
            'message_type': 4,
            'mmsi': base_station.mmsi,
            'year': utc_time.year,
            'month': utc_time.month,
            'day': utc_time.day,
            'hour': utc_time.hour,
            'minute': utc_time.minute,
            'second': utc_time.second,
            'longitude': base_station.position.longitude,
            'latitude': base_station.position.latitude,
            'epfd_type': base_station.epfd_type.value,
            'raim': base_station.raim,
            'radio_status': base_station.radio_status
        }
        
        return binary, input_data
    
    @staticmethod
    def encode_type_5(vessel: VesselState) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 5: Static and Voyage Related Data."""
        static = vessel.static_data
        voyage = vessel.voyage_data
        
        # Build binary message
        binary = ""
        binary += AISBinaryEncoder._encode_bits(5, 6)  # Message type
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Repeat indicator
        binary += AISBinaryEncoder._encode_bits(vessel.mmsi, 30)  # MMSI
        binary += AISBinaryEncoder._encode_bits(0, 2)  # AIS version
        binary += AISBinaryEncoder._encode_bits(static.imo_number or 0, 30)  # IMO number
        binary += AISBinaryEncoder._encode_string(static.callsign, 7)  # Call sign (42 bits)
        binary += AISBinaryEncoder._encode_string(static.vessel_name, 20)  # Vessel name (120 bits)
        binary += AISBinaryEncoder._encode_bits(static.ship_type.value, 8)  # Ship type
        
        # Dimensions
        dims = static.dimensions.to_ais_format()
        binary += AISBinaryEncoder._encode_bits(dims[0], 9)  # Dimension to bow
        binary += AISBinaryEncoder._encode_bits(dims[1], 9)  # Dimension to stern
        binary += AISBinaryEncoder._encode_bits(dims[2], 6)  # Dimension to port
        binary += AISBinaryEncoder._encode_bits(dims[3], 6)  # Dimension to starboard
        
        binary += AISBinaryEncoder._encode_bits(static.epfd_type.value, 4)  # EPFD type
        
        # ETA
        eta = voyage.eta.to_ais_format()
        binary += AISBinaryEncoder._encode_bits(eta[0], 4)  # ETA month
        binary += AISBinaryEncoder._encode_bits(eta[1], 5)  # ETA day
        binary += AISBinaryEncoder._encode_bits(eta[2], 5)  # ETA hour
        binary += AISBinaryEncoder._encode_bits(eta[3], 6)  # ETA minute
        
        # Draught
        draught_int = int(round(voyage.draught * 10)) if voyage.draught < 25.5 else 0
        binary += AISBinaryEncoder._encode_bits(draught_int, 8)  # Maximum draught
        
        binary += AISBinaryEncoder._encode_string(voyage.destination, 20)  # Destination (120 bits)
        binary += AISBinaryEncoder._encode_bits(voyage.dte, 1)  # DTE
        binary += AISBinaryEncoder._encode_bits(0, 1)  # Spare
        
        input_data = {
            'message_type': 5,
            'mmsi': vessel.mmsi,
            'imo_number': static.imo_number or 0,
            'callsign': static.callsign,
            'vessel_name': static.vessel_name,
            'ship_type': static.ship_type.value,
            'dimensions': dims,
            'epfd_type': static.epfd_type.value,
            'eta': eta,
            'draught': voyage.draught,
            'destination': voyage.destination,
            'dte': voyage.dte
        }
        
        return binary, input_data
    
    @staticmethod
    def encode_type_18(vessel: VesselState) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 18: Standard Class B Position Report."""
        nav = vessel.navigation_data
        
        # Build binary message
        binary = ""
        binary += AISBinaryEncoder._encode_bits(18, 6)  # Message type
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Repeat indicator
        binary += AISBinaryEncoder._encode_bits(vessel.mmsi, 30)  # MMSI
        binary += AISBinaryEncoder._encode_bits(0, 8)  # Regional reserved
        binary += AISBinaryEncoder._encode_sog(nav.sog)  # Speed over ground
        binary += AISBinaryEncoder._encode_bits(nav.position_accuracy, 1)  # Position accuracy
        binary += AISBinaryEncoder._encode_longitude(nav.position.longitude)  # Longitude
        binary += AISBinaryEncoder._encode_latitude(nav.position.latitude)  # Latitude
        binary += AISBinaryEncoder._encode_cog(nav.cog)  # Course over ground
        binary += AISBinaryEncoder._encode_heading(nav.heading)  # True heading
        binary += AISBinaryEncoder._encode_bits(nav.timestamp, 6)  # Time stamp
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Regional reserved
        binary += AISBinaryEncoder._encode_bits(1, 1)  # CS unit (1 = Class B SOTDMA)
        binary += AISBinaryEncoder._encode_bits(0, 1)  # Display flag
        binary += AISBinaryEncoder._encode_bits(0, 1)  # DSC flag
        binary += AISBinaryEncoder._encode_bits(0, 1)  # Band flag
        binary += AISBinaryEncoder._encode_bits(0, 1)  # Message 22 flag
        binary += AISBinaryEncoder._encode_bits(0, 1)  # Assigned mode
        binary += AISBinaryEncoder._encode_bits(nav.raim, 1)  # RAIM
        binary += AISBinaryEncoder._encode_bits(nav.radio_status, 20)  # Radio status
        
        input_data = {
            'message_type': 18,
            'mmsi': vessel.mmsi,
            'sog': nav.sog,
            'position_accuracy': nav.position_accuracy,
            'longitude': nav.position.longitude,
            'latitude': nav.position.latitude,
            'cog': nav.cog,
            'heading': nav.heading,
            'timestamp': nav.timestamp,
            'raim': nav.raim,
            'radio_status': nav.radio_status
        }
        
        return binary, input_data
    
    @staticmethod
    def encode_type_19(vessel: VesselState) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 19: Extended Class B Position Report."""
        nav = vessel.navigation_data
        static = vessel.static_data
        
        # Build binary message
        binary = ""
        binary += AISBinaryEncoder._encode_bits(19, 6)  # Message type
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Repeat indicator
        binary += AISBinaryEncoder._encode_bits(vessel.mmsi, 30)  # MMSI
        binary += AISBinaryEncoder._encode_bits(0, 8)  # Regional reserved
        binary += AISBinaryEncoder._encode_sog(nav.sog)  # Speed over ground
        binary += AISBinaryEncoder._encode_bits(nav.position_accuracy, 1)  # Position accuracy
        binary += AISBinaryEncoder._encode_longitude(nav.position.longitude)  # Longitude
        binary += AISBinaryEncoder._encode_latitude(nav.position.latitude)  # Latitude
        binary += AISBinaryEncoder._encode_cog(nav.cog)  # Course over ground
        binary += AISBinaryEncoder._encode_heading(nav.heading)  # True heading
        binary += AISBinaryEncoder._encode_bits(nav.timestamp, 6)  # Time stamp
        binary += AISBinaryEncoder._encode_bits(0, 4)  # Regional reserved
        binary += AISBinaryEncoder._encode_string(static.vessel_name, 20)  # Ship name (120 bits)
        binary += AISBinaryEncoder._encode_bits(static.ship_type.value, 8)  # Ship type
        
        # Dimensions
        dims = static.dimensions.to_ais_format()
        binary += AISBinaryEncoder._encode_bits(dims[0], 9)  # Dimension to bow
        binary += AISBinaryEncoder._encode_bits(dims[1], 9)  # Dimension to stern
        binary += AISBinaryEncoder._encode_bits(dims[2], 6)  # Dimension to port
        binary += AISBinaryEncoder._encode_bits(dims[3], 6)  # Dimension to starboard
        
        binary += AISBinaryEncoder._encode_bits(static.epfd_type.value, 4)  # EPFD type
        binary += AISBinaryEncoder._encode_bits(nav.raim, 1)  # RAIM
        binary += AISBinaryEncoder._encode_bits(1, 1)  # DTE (not available)
        binary += AISBinaryEncoder._encode_bits(0, 1)  # Assigned mode
        binary += AISBinaryEncoder._encode_bits(0, 4)  # Spare
        
        input_data = {
            'message_type': 19,
            'mmsi': vessel.mmsi,
            'sog': nav.sog,
            'position_accuracy': nav.position_accuracy,
            'longitude': nav.position.longitude,
            'latitude': nav.position.latitude,
            'cog': nav.cog,
            'heading': nav.heading,
            'timestamp': nav.timestamp,
            'vessel_name': static.vessel_name,
            'ship_type': static.ship_type.value,
            'dimensions': dims,
            'epfd_type': static.epfd_type.value,
            'raim': nav.raim
        }
        
        return binary, input_data
    
    @staticmethod
    def encode_type_21(aid_nav: AidToNavigationData) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 21: Aid-to-Navigation Report."""
        # Build binary message
        binary = ""
        binary += AISBinaryEncoder._encode_bits(21, 6)  # Message type
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Repeat indicator
        binary += AISBinaryEncoder._encode_bits(aid_nav.mmsi, 30)  # MMSI
        binary += AISBinaryEncoder._encode_bits(aid_nav.aid_type, 5)  # Aid type
        binary += AISBinaryEncoder._encode_string(aid_nav.name, 20)  # Name (120 bits)
        binary += AISBinaryEncoder._encode_bits(aid_nav.position_accuracy, 1)  # Position accuracy
        binary += AISBinaryEncoder._encode_longitude(aid_nav.position.longitude)  # Longitude
        binary += AISBinaryEncoder._encode_latitude(aid_nav.position.latitude)  # Latitude
        
        # Dimensions
        dims = aid_nav.dimensions.to_ais_format()
        binary += AISBinaryEncoder._encode_bits(dims[0], 9)  # Dimension to bow
        binary += AISBinaryEncoder._encode_bits(dims[1], 9)  # Dimension to stern
        binary += AISBinaryEncoder._encode_bits(dims[2], 6)  # Dimension to port
        binary += AISBinaryEncoder._encode_bits(dims[3], 6)  # Dimension to starboard
        
        binary += AISBinaryEncoder._encode_bits(aid_nav.epfd_type.value, 4)  # EPFD type
        binary += AISBinaryEncoder._encode_bits(aid_nav.timestamp, 6)  # Time stamp
        binary += AISBinaryEncoder._encode_bits(aid_nav.off_position, 1)  # Off position
        binary += AISBinaryEncoder._encode_bits(aid_nav.regional, 8)  # Regional reserved
        binary += AISBinaryEncoder._encode_bits(aid_nav.raim, 1)  # RAIM
        binary += AISBinaryEncoder._encode_bits(aid_nav.virtual_aid, 1)  # Virtual aid
        binary += AISBinaryEncoder._encode_bits(aid_nav.assigned, 1)  # Assigned mode
        binary += AISBinaryEncoder._encode_bits(0, 1)  # Spare
        
        # Pad to byte boundary if needed
        while len(binary) % 8 != 0:
            binary += "0"
        
        input_data = {
            'message_type': 21,
            'mmsi': aid_nav.mmsi,
            'aid_type': aid_nav.aid_type,
            'name': aid_nav.name,
            'longitude': aid_nav.position.longitude,
            'latitude': aid_nav.position.latitude,
            'dimensions': dims,
            'epfd_type': aid_nav.epfd_type.value,
            'timestamp': aid_nav.timestamp,
            'off_position': aid_nav.off_position,
            'regional': aid_nav.regional,
            'raim': aid_nav.raim,
            'virtual_aid': aid_nav.virtual_aid,
            'assigned': aid_nav.assigned
        }
        
        return binary, input_data
    
    @staticmethod
    def encode_type_24_part_a(vessel: VesselState) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 24 Part A: Static Data Report."""
        static = vessel.static_data
        
        # Build binary message
        binary = ""
        binary += AISBinaryEncoder._encode_bits(24, 6)  # Message type
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Repeat indicator
        binary += AISBinaryEncoder._encode_bits(vessel.mmsi, 30)  # MMSI
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Part number (0 = Part A)
        binary += AISBinaryEncoder._encode_string(static.vessel_name, 20)  # Vessel name (120 bits)
        binary += AISBinaryEncoder._encode_bits(0, 8)  # Spare
        
        input_data = {
            'message_type': 24,
            'part_number': 0,
            'mmsi': vessel.mmsi,
            'vessel_name': static.vessel_name
        }
        
        return binary, input_data
    
    @staticmethod
    def encode_type_24_part_b(vessel: VesselState) -> Tuple[str, Dict[str, Any]]:
        """Encode AIS Type 24 Part B: Static Data Report."""
        static = vessel.static_data
        
        # Build binary message
        binary = ""
        binary += AISBinaryEncoder._encode_bits(24, 6)  # Message type
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Repeat indicator
        binary += AISBinaryEncoder._encode_bits(vessel.mmsi, 30)  # MMSI
        binary += AISBinaryEncoder._encode_bits(1, 2)  # Part number (1 = Part B)
        binary += AISBinaryEncoder._encode_bits(static.ship_type.value, 8)  # Ship type
        binary += AISBinaryEncoder._encode_string("", 3)  # Vendor ID (18 bits)
        binary += AISBinaryEncoder._encode_string("", 1)  # Unit model code (6 bits)
        binary += AISBinaryEncoder._encode_bits(0, 20)  # Serial number
        binary += AISBinaryEncoder._encode_string(static.callsign, 7)  # Call sign (42 bits)
        
        # Dimensions
        dims = static.dimensions.to_ais_format()
        binary += AISBinaryEncoder._encode_bits(dims[0], 9)  # Dimension to bow
        binary += AISBinaryEncoder._encode_bits(dims[1], 9)  # Dimension to stern
        binary += AISBinaryEncoder._encode_bits(dims[2], 6)  # Dimension to port
        binary += AISBinaryEncoder._encode_bits(dims[3], 6)  # Dimension to starboard
        
        binary += AISBinaryEncoder._encode_bits(0, 2)  # Mothership MMSI (not used)
        binary += AISBinaryEncoder._encode_bits(0, 6)  # Spare
        
        input_data = {
            'message_type': 24,
            'part_number': 1,
            'mmsi': vessel.mmsi,
            'ship_type': static.ship_type.value,
            'callsign': static.callsign,
            'dimensions': dims
        }
        
        return binary, input_data

