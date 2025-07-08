"""Position generation for NMEA simulation."""

import math
import random
from datetime import datetime
from typing import List, Optional, Tuple
from dataclasses import dataclass

from nmea_lib.types import Position, Speed, Bearing, SpeedUnit, BearingType


@dataclass
class PositionState:
    """Current position and movement state."""
    
    position: Position
    speed: Speed
    heading: Bearing
    timestamp: datetime
    
    def __str__(self) -> str:
        return f"PositionState({self.position}, {self.speed.value:.1f}kts, {self.heading.value:.1f}°)"


class PositionGenerator:
    """Generates realistic GPS position data."""
    
    def __init__(self, initial_position: Position, initial_speed: float = 0.0, 
                 initial_heading: float = 0.0):
        """
        Initialize position generator.
        
        Args:
            initial_position: Starting position
            initial_speed: Initial speed in knots
            initial_heading: Initial heading in degrees true
        """
        self.initial_position = initial_position
        self.current_position = initial_position
        self.current_speed = Speed(initial_speed, SpeedUnit.KNOTS)
        self.current_heading = Bearing(initial_heading, BearingType.TRUE)
        
        # Movement parameters
        self.speed_variation = 2.0  # knots
        self.course_variation = 10.0  # degrees
        self.position_noise = 0.00001  # degrees (about 1 meter)
        
        # Track history
        self.position_history: List[PositionState] = []
        
        # Random number generator
        self.random = random.Random()
        self.random.seed(42)  # Reproducible results
    
    def set_movement_parameters(self, speed_variation: float = 2.0, 
                              course_variation: float = 10.0,
                              position_noise: float = 0.00001) -> None:
        """Set movement variation parameters."""
        self.speed_variation = max(0.0, speed_variation)
        self.course_variation = max(0.0, course_variation)
        self.position_noise = max(0.0, position_noise)
    
    def update_position(self, elapsed_seconds: float, timestamp: datetime) -> PositionState:
        """
        Update position based on elapsed time.
        
        Args:
            elapsed_seconds: Time elapsed since last update
            timestamp: Current simulation time
            
        Returns:
            Updated position state
        """
        # Add some realistic variation to speed and heading
        self._apply_movement_variation()
        
        # Calculate distance traveled
        speed_ms = self.current_speed.to_knots() * 0.514444  # Convert knots to m/s
        distance_m = speed_ms * elapsed_seconds
        
        # Move position
        if distance_m > 0:
            new_position = self.current_position.move_by_bearing_distance(
                self.current_heading.value, distance_m
            )
            
            # Add GPS noise
            new_position = self._add_gps_noise(new_position)
            
            self.current_position = new_position
        
        # Create position state
        state = PositionState(
            position=self.current_position,
            speed=self.current_speed,
            heading=self.current_heading,
            timestamp=timestamp
        )
        
        # Store in history
        self.position_history.append(state)
        
        # Limit history size
        if len(self.position_history) > 1000:
            self.position_history = self.position_history[-500:]
        
        return state
    
    def _apply_movement_variation(self) -> None:
        """Apply realistic variations to speed and heading."""
        # Speed variation
        if self.speed_variation > 0:
            speed_change = self.random.gauss(0, self.speed_variation / 3)
            new_speed = max(0, self.current_speed.value + speed_change * 0.1)
            self.current_speed = Speed(new_speed, SpeedUnit.KNOTS)
        
        # Course variation
        if self.course_variation > 0:
            course_change = self.random.gauss(0, self.course_variation / 3)
            new_heading = (self.current_heading.value + course_change * 0.1) % 360
            self.current_heading = Bearing(new_heading, BearingType.TRUE)
    
    def _add_gps_noise(self, position: Position) -> Position:
        """Add realistic GPS noise to position."""
        if self.position_noise <= 0:
            return position
        
        # Add Gaussian noise to lat/lon
        lat_noise = self.random.gauss(0, self.position_noise)
        lon_noise = self.random.gauss(0, self.position_noise)
        
        new_lat = position.latitude + lat_noise
        new_lon = position.longitude + lon_noise
        
        # Ensure coordinates remain valid
        new_lat = max(-90, min(90, new_lat))
        new_lon = max(-180, min(180, new_lon))
        
        return Position(new_lat, new_lon)
    
    def set_speed(self, speed_knots: float) -> None:
        """Set current speed."""
        self.current_speed = Speed(max(0, speed_knots), SpeedUnit.KNOTS)
    
    def set_heading(self, heading_degrees: float) -> None:
        """Set current heading."""
        self.current_heading = Bearing(heading_degrees % 360, BearingType.TRUE)
    
    def set_position(self, position: Position) -> None:
        """Set current position."""
        self.current_position = position
    
    def get_current_state(self, timestamp: datetime) -> PositionState:
        """Get current position state without updating."""
        return PositionState(
            position=self.current_position,
            speed=self.current_speed,
            heading=self.current_heading,
            timestamp=timestamp
        )
    
    def reset(self, position: Optional[Position] = None) -> None:
        """Reset to initial or specified position."""
        self.current_position = position or self.initial_position
        self.current_speed = Speed(0.0, SpeedUnit.KNOTS)
        self.current_heading = Bearing(0.0, BearingType.TRUE)
        self.position_history.clear()
    
    def get_distance_traveled(self) -> float:
        """Get total distance traveled in meters."""
        if len(self.position_history) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(1, len(self.position_history)):
            prev_pos = self.position_history[i-1].position
            curr_pos = self.position_history[i].position
            total_distance += prev_pos.distance_to(curr_pos)
        
        return total_distance
    
    def get_average_speed(self) -> float:
        """Get average speed in knots."""
        if len(self.position_history) < 2:
            return 0.0
        
        total_time = (self.position_history[-1].timestamp - 
                     self.position_history[0].timestamp).total_seconds()
        
        if total_time <= 0:
            return 0.0
        
        distance_m = self.get_distance_traveled()
        speed_ms = distance_m / total_time
        speed_knots = speed_ms / 0.514444  # Convert m/s to knots
        
        return speed_knots

