#!/usr/bin/env python3
"""
Position Calculation Example
Demonstrates how the NMEA simulator calculates the next position.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import math
from datetime import datetime, timedelta
from nmea_lib.types import Position, Speed, Bearing, SpeedUnit, BearingType
from simulator.generators.position import PositionGenerator


def demonstrate_position_calculation():
    """Demonstrate step-by-step position calculation."""
    
    print("=" * 60)
    print("NMEA Simulator - Position Calculation Demonstration")
    print("=" * 60)
    
    # Initial conditions
    start_position = Position(37.7749, -122.4194)  # San Francisco
    initial_speed = 5.0  # knots
    initial_heading = 45.0  # degrees (Northeast)
    
    print(f"\n1. INITIAL CONDITIONS:")
    print(f"   Position: {start_position}")
    print(f"   Speed: {initial_speed} knots")
    print(f"   Heading: {initial_heading}° True")
    
    # Create position generator
    generator = PositionGenerator(start_position, initial_speed, initial_heading)
    
    # Set movement parameters for demonstration
    generator.set_movement_parameters(
        speed_variation=2.0,    # ±2 knots variation
        course_variation=10.0,  # ±10 degrees variation
        position_noise=0.00001  # ~1 meter GPS noise
    )
    
    print(f"\n2. MOVEMENT PARAMETERS:")
    print(f"   Speed variation: ±2.0 knots (Gaussian)")
    print(f"   Course variation: ±10.0 degrees (Gaussian)")
    print(f"   GPS noise: ±0.00001° (~1.1 meters)")
    
    # Simulate multiple position updates
    print(f"\n3. POSITION CALCULATION STEPS:")
    print(f"   {'Time':<8} {'Latitude':<12} {'Longitude':<13} {'Speed':<8} {'Heading':<8} {'Distance':<10}")
    print(f"   {'-'*8} {'-'*12} {'-'*13} {'-'*8} {'-'*8} {'-'*10}")
    
    current_time = datetime.now()
    total_distance = 0.0
    
    for i in range(10):
        # Update position (1 second intervals)
        elapsed_time = 1.0
        current_time += timedelta(seconds=elapsed_time)
        
        # Get previous position for distance calculation
        prev_position = generator.current_position
        
        # Update position
        state = generator.update_position(elapsed_time, current_time)
        
        # Calculate distance moved
        if i > 0:
            distance_moved = prev_position.distance_to(state.position)
            total_distance += distance_moved
        else:
            distance_moved = 0.0
        
        # Display results
        print(f"   {i+1:<8} {state.position.latitude:<12.6f} {state.position.longitude:<13.6f} "
              f"{state.speed.value:<8.2f} {state.heading.value:<8.1f} {distance_moved:<10.2f}")
    
    print(f"\n4. SUMMARY:")
    print(f"   Total distance traveled: {total_distance:.2f} meters")
    print(f"   Average speed: {generator.get_average_speed():.2f} knots")
    print(f"   Final position: {generator.current_position}")


def demonstrate_mathematical_formulas():
    """Demonstrate the mathematical formulas used in position calculation."""
    
    print(f"\n" + "=" * 60)
    print("MATHEMATICAL FORMULAS DEMONSTRATION")
    print("=" * 60)
    
    # Example calculation
    start_lat = 37.7749  # degrees
    start_lon = -122.4194  # degrees
    bearing = 45.0  # degrees (Northeast)
    distance = 1000.0  # meters
    
    print(f"\n1. INPUT VALUES:")
    print(f"   Start position: {start_lat}°N, {abs(start_lon)}°W")
    print(f"   Bearing: {bearing}° True")
    print(f"   Distance: {distance} meters")
    
    # Convert to radians
    lat1_rad = math.radians(start_lat)
    lon1_rad = math.radians(start_lon)
    bearing_rad = math.radians(bearing)
    earth_radius = 6371000  # meters
    
    print(f"\n2. CONVERSION TO RADIANS:")
    print(f"   lat1 = {lat1_rad:.6f} radians")
    print(f"   lon1 = {lon1_rad:.6f} radians")
    print(f"   bearing = {bearing_rad:.6f} radians")
    print(f"   Earth radius = {earth_radius:,} meters")
    
    # Calculate new position using spherical geometry
    lat2_rad = math.asin(
        math.sin(lat1_rad) * math.cos(distance / earth_radius) +
        math.cos(lat1_rad) * math.sin(distance / earth_radius) * math.cos(bearing_rad)
    )
    
    lon2_rad = lon1_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(distance / earth_radius) * math.cos(lat1_rad),
        math.cos(distance / earth_radius) - math.sin(lat1_rad) * math.sin(lat2_rad)
    )
    
    # Convert back to degrees
    lat2_deg = math.degrees(lat2_rad)
    lon2_deg = math.degrees(lon2_rad)
    
    print(f"\n3. SPHERICAL GEOMETRY CALCULATION:")
    print(f"   Formula: lat2 = asin(sin(lat1)×cos(d/R) + cos(lat1)×sin(d/R)×cos(θ))")
    print(f"   Formula: lon2 = lon1 + atan2(sin(θ)×sin(d/R)×cos(lat1), cos(d/R) - sin(lat1)×sin(lat2))")
    print(f"   ")
    print(f"   Intermediate calculations:")
    print(f"   - cos(d/R) = cos({distance}/{earth_radius}) = {math.cos(distance / earth_radius):.6f}")
    print(f"   - sin(d/R) = sin({distance}/{earth_radius}) = {math.sin(distance / earth_radius):.6f}")
    print(f"   ")
    print(f"   Result in radians:")
    print(f"   - lat2 = {lat2_rad:.6f} radians")
    print(f"   - lon2 = {lon2_rad:.6f} radians")
    
    print(f"\n4. FINAL RESULT:")
    print(f"   New position: {lat2_deg:.6f}°N, {abs(lon2_deg):.6f}°W")
    
    # Verify using Position class
    start_pos = Position(start_lat, start_lon)
    end_pos = start_pos.move_by_bearing_distance(bearing, distance)
    
    print(f"   Verification: {end_pos}")
    
    # Calculate actual distance and bearing
    actual_distance = start_pos.distance_to(end_pos)
    actual_bearing = start_pos.bearing_to(end_pos)
    
    print(f"\n5. VERIFICATION:")
    print(f"   Calculated distance: {actual_distance:.2f} meters (expected: {distance:.2f})")
    print(f"   Calculated bearing: {actual_bearing:.1f}° (expected: {bearing:.1f}°)")
    print(f"   Distance error: {abs(actual_distance - distance):.2f} meters")
    print(f"   Bearing error: {abs(actual_bearing - bearing):.1f} degrees")


def demonstrate_speed_conversion():
    """Demonstrate speed unit conversions."""
    
    print(f"\n" + "=" * 60)
    print("SPEED CONVERSION DEMONSTRATION")
    print("=" * 60)
    
    speed_knots = 5.0
    
    # Conversion factors
    knots_to_ms = 0.514444
    ms_to_kmh = 3.6
    ms_to_mph = 2.23694
    
    speed_ms = speed_knots * knots_to_ms
    speed_kmh = speed_ms * ms_to_kmh
    speed_mph = speed_ms * ms_to_mph
    
    print(f"\n1. SPEED CONVERSIONS:")
    print(f"   Original speed: {speed_knots} knots")
    print(f"   ")
    print(f"   Conversion factors:")
    print(f"   - 1 knot = {knots_to_ms} m/s")
    print(f"   - 1 m/s = {ms_to_kmh} km/h")
    print(f"   - 1 m/s = {ms_to_mph} mph")
    print(f"   ")
    print(f"   Converted speeds:")
    print(f"   - {speed_ms:.3f} m/s")
    print(f"   - {speed_kmh:.2f} km/h")
    print(f"   - {speed_mph:.2f} mph")
    
    # Distance calculation example
    time_seconds = 60.0  # 1 minute
    distance_meters = speed_ms * time_seconds
    distance_nautical_miles = distance_meters / 1852.0  # 1 nautical mile = 1852 meters
    
    print(f"\n2. DISTANCE CALCULATION:")
    print(f"   Time: {time_seconds} seconds (1 minute)")
    print(f"   Distance = speed × time")
    print(f"   Distance = {speed_ms:.3f} m/s × {time_seconds} s = {distance_meters:.1f} meters")
    print(f"   Distance = {distance_nautical_miles:.3f} nautical miles")


if __name__ == "__main__":
    demonstrate_position_calculation()
    demonstrate_mathematical_formulas()
    demonstrate_speed_conversion()
    
    print(f"\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)

