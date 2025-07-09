"""Enhanced vessel position generator for AIS and GPS simulation."""

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from nmea_lib.types import Position
from nmea_lib.types.vessel import (
    VesselState,
    VesselDimensions,
    VesselETA,
    create_vessel_state,
)
from nmea_lib.ais.constants import (
    NavigationStatus,
    ShipType,
    VesselClass,
)


@dataclass
class MovementPattern:
    """Defines movement patterns for vessel simulation."""

    pattern_type: str = "linear"  # linear, circular, waypoint, random_walk
    speed_variation: float = 2.0  # ±knots
    course_variation: float = 10.0  # ±degrees
    position_noise: float = 0.00001  # GPS noise in degrees

    # Pattern-specific parameters
    waypoints: List[Position] = None
    circle_center: Position = None
    circle_radius: float = 1000.0  # meters
    random_walk_bounds: Tuple[float, float, float, float] = (
        None  # lat_min, lat_max, lon_min, lon_max
    )


class EnhancedVesselGenerator:
    """Enhanced position generator that creates complete vessel states."""

    def __init__(self, vessel_config: Dict):
        """Initialize vessel generator from configuration."""
        self.vessel_config = vessel_config
        self.vessel_state = self._create_initial_vessel_state()
        self.movement_pattern = self._create_movement_pattern()

        # Movement tracking
        self.position_history: List[Tuple[datetime, Position]] = []
        self.max_history = 1000

        # Random number generator for reproducible results
        self.rng = random.Random(vessel_config.get("seed", 42))

        # Navigation state tracking
        self.last_course_change = datetime.now()
        self.course_change_interval = timedelta(
            minutes=5
        )  # Change course every 5 minutes

    def _create_initial_vessel_state(self) -> VesselState:
        """Create initial vessel state from configuration."""
        config = self.vessel_config

        # Extract position
        pos_config = config.get("initial_position", {})
        position = Position(
            pos_config.get("latitude", 0.0), pos_config.get("longitude", 0.0)
        )

        # Create vessel state
        vessel = create_vessel_state(
            mmsi=config["mmsi"],
            vessel_name=config.get("name", f"VESSEL_{config['mmsi']}"),
            position=position,
            vessel_class=VesselClass(config.get("vessel_class", "A")),
            callsign=config.get("callsign", ""),
            ship_type=ShipType(config.get("ship_type", 70)),
            sog=config.get("initial_speed", 0.0),
            cog=config.get("initial_heading", 0.0),
            heading=config.get("initial_heading", 0),
            nav_status=NavigationStatus(config.get("nav_status", 0)),
        )

        # Set dimensions if provided
        if "dimensions" in config:
            dims = config["dimensions"]
            vessel.static_data.dimensions = VesselDimensions(
                to_bow=dims.get("to_bow", 0),
                to_stern=dims.get("to_stern", 0),
                to_port=dims.get("to_port", 0),
                to_starboard=dims.get("to_starboard", 0),
            )

        # Set voyage data if provided
        if "voyage" in config:
            voyage = config["voyage"]
            vessel.voyage_data.destination = voyage.get("destination", "")
            vessel.voyage_data.draught = voyage.get("draught", 0.0)

            # Set ETA if provided
            if "eta" in voyage:
                eta_config = voyage["eta"]
                vessel.voyage_data.eta = VesselETA(
                    month=eta_config.get("month", 0),
                    day=eta_config.get("day", 0),
                    hour=eta_config.get("hour", 24),
                    minute=eta_config.get("minute", 60),
                )

        return vessel

    def _create_movement_pattern(self) -> MovementPattern:
        """Create movement pattern from configuration."""
        movement_config = self.vessel_config.get("movement", {})

        pattern = MovementPattern(
            pattern_type=movement_config.get("pattern", "linear"),
            speed_variation=movement_config.get("speed_variation", 2.0),
            course_variation=movement_config.get("course_variation", 10.0),
            position_noise=movement_config.get("position_noise", 0.00001),
        )

        # Set pattern-specific parameters
        if pattern.pattern_type == "waypoint" and "waypoints" in movement_config:
            waypoints = []
            for wp in movement_config["waypoints"]:
                waypoints.append(Position(wp["latitude"], wp["longitude"]))
            pattern.waypoints = waypoints

        elif pattern.pattern_type == "circular" and "circle" in movement_config:
            circle_config = movement_config["circle"]
            pattern.circle_center = Position(
                circle_config["center"]["latitude"],
                circle_config["center"]["longitude"],
            )
            pattern.circle_radius = circle_config.get("radius", 1000.0)

        elif pattern.pattern_type == "random_walk" and "bounds" in movement_config:
            bounds = movement_config["bounds"]
            pattern.random_walk_bounds = (
                bounds["lat_min"],
                bounds["lat_max"],
                bounds["lon_min"],
                bounds["lon_max"],
            )

        return pattern

    def update_vessel_state(
        self, elapsed_seconds: float, current_time: datetime
    ) -> VesselState:
        """Update vessel state with realistic movement."""
        # Apply movement variation
        self._apply_movement_variation(elapsed_seconds, current_time)

        # Calculate new position based on movement pattern
        new_position = self._calculate_new_position(elapsed_seconds)

        # Update navigation data
        nav = self.vessel_state.navigation_data
        nav.position = new_position
        nav.timestamp = current_time.second

        # Add GPS noise
        nav.position = self._add_gps_noise(nav.position)

        # Update simulation timestamp
        self.vessel_state.timestamp_sim = current_time
        self.vessel_state.last_update = datetime.now()

        # Add to position history
        self.position_history.append((current_time, nav.position))
        if len(self.position_history) > self.max_history:
            self.position_history.pop(0)

        return self.vessel_state

    def _apply_movement_variation(
            self,
            elapsed_seconds: float,
            current_time: datetime):
        """Apply realistic movement variations."""
        nav = self.vessel_state.navigation_data

        # Speed variation (Gaussian noise)
        base_speed = self.vessel_config.get("initial_speed", 0.0)
        speed_noise = self.rng.gauss(
            0, self.movement_pattern.speed_variation * 0.1)
        nav.sog = max(0, base_speed + speed_noise)

        # Course variation (periodic changes)
        if current_time - self.last_course_change > self.course_change_interval:
            base_course = self.vessel_config.get("initial_heading", 0.0)
            course_noise = self.rng.gauss(
                0, self.movement_pattern.course_variation)
            nav.cog = (base_course + course_noise) % 360.0
            nav.heading = int(nav.cog) % 360
            self.last_course_change = current_time

        # Rate of turn (based on course changes)
        if len(self.position_history) > 1:
            prev_time, prev_pos = self.position_history[-1]
            time_diff = (current_time - prev_time).total_seconds()
            if time_diff > 0:
                # Calculate rate of turn based on course change
                course_diff = nav.cog - nav.cog  # This would need previous course
                nav.rot = min(127, max(-127, int(course_diff / time_diff)))

        # Update navigation status based on speed
        if nav.sog < 0.1:
            nav.nav_status = NavigationStatus.AT_ANCHOR
        elif nav.sog > 23.0:  # High speed
            nav.nav_status = NavigationStatus.UNDER_WAY_USING_ENGINE
        else:
            nav.nav_status = NavigationStatus.UNDER_WAY_USING_ENGINE

    def _calculate_new_position(self, elapsed_seconds: float) -> Position:
        """Calculate new position based on movement pattern."""
        current_pos = self.vessel_state.navigation_data.position
        nav = self.vessel_state.navigation_data

        if self.movement_pattern.pattern_type == "linear":
            return self._linear_movement(
                current_pos, nav.sog, nav.cog, elapsed_seconds)

        elif self.movement_pattern.pattern_type == "circular":
            return self._circular_movement(
                current_pos, nav.sog, elapsed_seconds)

        elif self.movement_pattern.pattern_type == "waypoint":
            return self._waypoint_movement(
                current_pos, nav.sog, elapsed_seconds)

        elif self.movement_pattern.pattern_type == "random_walk":
            return self._random_walk_movement(
                current_pos, nav.sog, elapsed_seconds)

        else:
            # Default to linear movement
            return self._linear_movement(
                current_pos, nav.sog, nav.cog, elapsed_seconds)

    def _linear_movement(
        self,
        position: Position,
        speed_knots: float,
        course_degrees: float,
        elapsed_seconds: float,
    ) -> Position:
        """Calculate linear movement."""
        # Convert speed to m/s
        speed_ms = speed_knots * 0.514444

        # Calculate distance traveled
        distance_meters = speed_ms * elapsed_seconds

        # Move by bearing and distance
        return position.move_by_bearing_distance(
            course_degrees, distance_meters)

    def _circular_movement(
        self, position: Position, speed_knots: float, elapsed_seconds: float
    ) -> Position:
        """Calculate circular movement around a center point."""
        if not self.movement_pattern.circle_center:
            return position

        # Calculate angular velocity based on speed and radius
        speed_ms = speed_knots * 0.514444
        radius = self.movement_pattern.circle_radius
        angular_velocity = speed_ms / radius  # radians per second

        # Calculate new angle
        center = self.movement_pattern.circle_center
        current_bearing = center.bearing_to(position)
        new_bearing = (
            current_bearing + math.degrees(angular_velocity * elapsed_seconds)
        ) % 360

        # Calculate new position
        return center.move_by_bearing_distance(new_bearing, radius)

    def _waypoint_movement(
        self, position: Position, speed_knots: float, elapsed_seconds: float
    ) -> Position:
        """Calculate movement towards next waypoint."""
        if not self.movement_pattern.waypoints:
            return position

        # Find closest waypoint
        min_distance = float("inf")
        target_waypoint = self.movement_pattern.waypoints[0]

        for waypoint in self.movement_pattern.waypoints:
            distance = position.distance_to(waypoint)
            if distance < min_distance:
                min_distance = distance
                target_waypoint = waypoint

        # Calculate bearing to target
        bearing = position.bearing_to(target_waypoint)

        # Calculate movement
        speed_ms = speed_knots * 0.514444
        distance_meters = speed_ms * elapsed_seconds

        # Don't overshoot the waypoint
        if distance_meters > min_distance:
            return target_waypoint

        return position.move_by_bearing_distance(bearing, distance_meters)

    def _random_walk_movement(
        self, position: Position, speed_knots: float, elapsed_seconds: float
    ) -> Position:
        """Calculate random walk movement within bounds."""
        # Random course change
        course_change = self.rng.gauss(0, 30)  # ±30 degrees
        nav = self.vessel_state.navigation_data
        new_course = (nav.cog + course_change) % 360

        # Calculate movement
        new_pos = self._linear_movement(
            position, speed_knots, new_course, elapsed_seconds
        )

        # Check bounds
        if self.movement_pattern.random_walk_bounds:
            lat_min, lat_max, lon_min, lon_max = (
                self.movement_pattern.random_walk_bounds
            )

            if not (
                lat_min <= new_pos.latitude <= lat_max
                and lon_min <= new_pos.longitude <= lon_max
            ):
                # Reverse course if hitting bounds
                nav.cog = (nav.cog + 180) % 360
                nav.heading = int(nav.cog)
                return position

        # Update course
        nav.cog = new_course
        nav.heading = int(new_course)

        return new_pos

    def _add_gps_noise(self, position: Position) -> Position:
        """Add realistic GPS noise to position."""
        noise_std = self.movement_pattern.position_noise

        lat_noise = self.rng.gauss(0, noise_std)
        lon_noise = self.rng.gauss(0, noise_std)

        new_lat = position.latitude + lat_noise
        new_lon = position.longitude + lon_noise

        # Clamp to valid ranges
        new_lat = max(-90.0, min(90.0, new_lat))
        new_lon = max(-180.0, min(180.0, new_lon))

        return Position(new_lat, new_lon)

    def get_current_state(self) -> VesselState:
        """Get current vessel state."""
        return self.vessel_state

    def get_position_history(self) -> List[Tuple[datetime, Position]]:
        """Get position history."""
        return self.position_history.copy()

    def get_average_speed(self) -> float:
        """Calculate average speed over recent history."""
        if len(self.position_history) < 2:
            return self.vessel_state.navigation_data.sog

        total_distance = 0.0
        total_time = 0.0

        for i in range(1, min(len(self.position_history),
                       10)):  # Last 10 positions
            prev_time, prev_pos = self.position_history[i - 1]
            curr_time, curr_pos = self.position_history[i]

            distance = prev_pos.distance_to(curr_pos)  # meters
            time_diff = (curr_time - prev_time).total_seconds()

            if time_diff > 0:
                total_distance += distance
                total_time += time_diff

        if total_time > 0:
            # Convert m/s to knots
            avg_speed_ms = total_distance / total_time
            return avg_speed_ms / 0.514444

        return self.vessel_state.navigation_data.sog

    def set_destination(
            self,
            destination: str,
            eta: Optional[VesselETA] = None):
        """Update vessel destination and ETA."""
        self.vessel_state.voyage_data.destination = destination
        if eta:
            self.vessel_state.voyage_data.eta = eta

    def set_navigation_status(self, status: NavigationStatus):
        """Update navigation status."""
        self.vessel_state.navigation_data.nav_status = status


# Factory function for creating vessel generators
def create_vessel_generator(vessel_config: Dict) -> EnhancedVesselGenerator:
    """Create a vessel generator from configuration."""
    return EnhancedVesselGenerator(vessel_config)


# Utility functions for vessel configuration
def create_default_vessel_config(
    mmsi: int, name: str, position: Position, vessel_class: str = "A"
) -> Dict:
    """Create default vessel configuration."""
    return {
        "mmsi": mmsi,
        "name": name,
        "vessel_class": vessel_class,
        "callsign": f"CALL{mmsi % 10000}",
        "ship_type": 70,  # Cargo ship
        "initial_position": {
            "latitude": position.latitude,
            "longitude": position.longitude,
        },
        "initial_speed": 10.0,
        "initial_heading": 90.0,
        "nav_status": 0,
        "dimensions": {"to_bow": 50, "to_stern": 10, "to_port": 5, "to_starboard": 5},
        "voyage": {
            "destination": "UNKNOWN",
            "draught": 5.0,
            "eta": {"month": 0, "day": 0, "hour": 24, "minute": 60},
        },
        "movement": {
            "pattern": "linear",
            "speed_variation": 2.0,
            "course_variation": 10.0,
            "position_noise": 0.00001,
        },
        "seed": 42,
    }
