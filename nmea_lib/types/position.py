"""Position-related data types for NMEA sentences."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
import math


class Hemisphere(Enum):
    """Hemisphere enumeration for latitude and longitude."""
    NORTH = "N"
    SOUTH = "S"
    EAST = "E"
    WEST = "W"


@dataclass
class Position:
    """Represents a geographic position with latitude and longitude."""
    
    latitude: float  # Decimal degrees
    longitude: float  # Decimal degrees
    
    def __post_init__(self):
        """Validate position coordinates."""
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Invalid longitude: {self.longitude}")
    
    @classmethod
    def from_nmea(cls, lat_str: str, lat_hem: str, lon_str: str, lon_hem: str) -> 'Position':
        """Create Position from NMEA format strings."""
        if not all([lat_str, lat_hem, lon_str, lon_hem]):
            raise ValueError("Missing position data")
        
        # Parse latitude (DDMM.MMMM format)
        lat_degrees = int(lat_str[:2])
        lat_minutes = float(lat_str[2:])
        latitude = lat_degrees + lat_minutes / 60.0
        
        if lat_hem.upper() == Hemisphere.SOUTH.value:
            latitude = -latitude
        
        # Parse longitude (DDDMM.MMMM format)
        lon_degrees = int(lon_str[:3])
        lon_minutes = float(lon_str[3:])
        longitude = lon_degrees + lon_minutes / 60.0
        
        if lon_hem.upper() == Hemisphere.WEST.value:
            longitude = -longitude
        
        return cls(latitude, longitude)
    
    def to_nmea(self) -> Tuple[str, str, str, str]:
        """Convert position to NMEA format strings."""
        # Latitude
        lat_abs = abs(self.latitude)
        lat_deg = int(lat_abs)
        lat_min = (lat_abs - lat_deg) * 60.0
        lat_str = f"{lat_deg:02d}{lat_min:07.4f}"
        lat_hem = Hemisphere.NORTH.value if self.latitude >= 0 else Hemisphere.SOUTH.value
        
        # Longitude
        lon_abs = abs(self.longitude)
        lon_deg = int(lon_abs)
        lon_min = (lon_abs - lon_deg) * 60.0
        lon_str = f"{lon_deg:03d}{lon_min:07.4f}"
        lon_hem = Hemisphere.EAST.value if self.longitude >= 0 else Hemisphere.WEST.value
        
        return lat_str, lat_hem, lon_str, lon_hem
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position in meters using Haversine formula."""
        lat1_rad = math.radians(self.latitude)
        lon1_rad = math.radians(self.longitude)
        lat2_rad = math.radians(other.latitude)
        lon2_rad = math.radians(other.longitude)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in meters
        earth_radius = 6371000
        return earth_radius * c
    
    def bearing_to(self, other: 'Position') -> float:
        """Calculate bearing to another position in degrees."""
        lat1_rad = math.radians(self.latitude)
        lon1_rad = math.radians(self.longitude)
        lat2_rad = math.radians(other.latitude)
        lon2_rad = math.radians(other.longitude)
        
        dlon = lon2_rad - lon1_rad
        
        y = math.sin(dlon) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon))
        
        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)
        
        # Normalize to 0-360 degrees
        return (bearing_deg + 360) % 360
    
    def move_by_bearing_distance(self, bearing_deg: float, distance_m: float) -> 'Position':
        """Move position by bearing and distance to get new position."""
        earth_radius = 6371000  # meters
        
        lat1_rad = math.radians(self.latitude)
        lon1_rad = math.radians(self.longitude)
        bearing_rad = math.radians(bearing_deg)
        
        lat2_rad = math.asin(
            math.sin(lat1_rad) * math.cos(distance_m / earth_radius) +
            math.cos(lat1_rad) * math.sin(distance_m / earth_radius) * math.cos(bearing_rad)
        )
        
        lon2_rad = lon1_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_m / earth_radius) * math.cos(lat1_rad),
            math.cos(distance_m / earth_radius) - math.sin(lat1_rad) * math.sin(lat2_rad)
        )
        
        return Position(math.degrees(lat2_rad), math.degrees(lon2_rad))
    
    def __str__(self) -> str:
        """String representation of position."""
        lat_hem = "N" if self.latitude >= 0 else "S"
        lon_hem = "E" if self.longitude >= 0 else "W"
        return f"{abs(self.latitude):.6f}°{lat_hem}, {abs(self.longitude):.6f}°{lon_hem}"

