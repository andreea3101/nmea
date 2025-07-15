#!/usr/bin/env python3
"""
Enhanced Working NMEA+AIS Simulator
"""

import sys
import os
import json
import time
import socket
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nmea_lib.types import Position
from nmea_lib.types.units import Distance, DistanceUnit
from nmea_lib.sentences.gga import GGASentence
from nmea_lib.sentences.rmc import RMCSentence
from nmea_lib.sentences.aivdm import AISMessageGenerator
from nmea_lib.types.datetime import NMEATime, NMEADate
from nmea_lib.types.vessel import VesselState, VesselClass, ShipType, NavigationStatus
from nmea_lib.types import create_vessel_state


class NetworkOutput:
    """Handle TCP and UDP network output."""
    
    def __init__(self, tcp_port=None, udp_port=None, udp_host="255.255.255.255"):
        """Initialize network outputs."""
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.udp_host = udp_host
        
        self.tcp_server = None
        self.udp_socket = None
        self.tcp_clients = []
        self.running = False
        
        if tcp_port:
            self._setup_tcp_server()
        if udp_port:
            self._setup_udp_socket()
    
    def _setup_tcp_server(self):
        """Set up TCP server for client connections."""
        try:
            self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_server.bind(('0.0.0.0', self.tcp_port))
            self.tcp_server.listen(5)
            self.tcp_server.settimeout(1.0)  # Non-blocking accept
            
            # Start TCP server thread
            self.running = True
            tcp_thread = threading.Thread(target=self._tcp_server_loop, daemon=True)
            tcp_thread.start()
            
            print(f"TCP server listening on port {self.tcp_port}")
            
        except Exception as e:
            print(f"Failed to setup TCP server: {e}")
            self.tcp_server = None
    
    def _setup_udp_socket(self):
        """Set up UDP socket for broadcasting."""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            print(f"UDP broadcast setup on port {self.udp_port}")
            
        except Exception as e:
            print(f"Failed to setup UDP socket: {e}")
            self.udp_socket = None
    
    def _tcp_server_loop(self):
        """TCP server loop to accept client connections."""
        while self.running and self.tcp_server:
            try:
                client_socket, address = self.tcp_server.accept()
                self.tcp_clients.append(client_socket)
                print(f"TCP client connected from {address}")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"TCP server error: {e}")
                break
    
    def send_sentence(self, sentence):
        """Send NMEA sentence to all network outputs."""
        sentence_with_newline = sentence + "\n"
        
        # Send to TCP clients
        if self.tcp_clients:
            disconnected_clients = []
            for client in self.tcp_clients:
                try:
                    client.send(sentence_with_newline.encode('utf-8'))
                except:
                    disconnected_clients.append(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.tcp_clients.remove(client)
                try:
                    client.close()
                except:
                    pass
        
        # Send to UDP broadcast
        if self.udp_socket and self.udp_port:
            try:
                self.udp_socket.sendto(
                    sentence_with_newline.encode('utf-8'), 
                    (self.udp_host, self.udp_port)
                )
            except Exception as e:
                print(f"UDP send error: {e}")
    
    def close(self):
        """Close all network connections."""
        self.running = False
        
        if self.tcp_server:
            self.tcp_server.close()
        
        for client in self.tcp_clients:
            try:
                client.close()
            except:
                pass
        
        if self.udp_socket:
            self.udp_socket.close()


class EnhancedNMEASimulator:
    """Enhanced NMEA simulator with network support and fixed output."""
    
    def __init__(self, output_dir="enhanced_output", tcp_port=None, udp_port=None):
        """Initialize the enhanced simulator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.vessels = []
        self.reference_data = []
        self.message_count = 0
        
        # Create network output
        self.network = NetworkOutput(tcp_port, udp_port)
        
        # Create AIS generator
        self.ais_generator = AISMessageGenerator()
        
        # Create test vessels
        self._create_test_vessels()
    
    def _create_test_vessels(self):
        """Create test vessels for simulation."""
        
        # Vessel 1: Container ship
        vessel1 = create_vessel_state(
            mmsi=367001234,
            vessel_name="EVER FORWARD",
            position=Position(37.8000, -122.4000),
            vessel_class=VesselClass.CLASS_A,
            callsign="TEST123",
            ship_type=ShipType.CARGO_ALL_SHIPS,
            sog=15.5,
            cog=90.0,
            heading=92,
            nav_status=NavigationStatus.UNDER_WAY_USING_ENGINE
        )
        
        # Set additional data
        vessel1.static_data.dimensions.to_bow = 150
        vessel1.static_data.dimensions.to_stern = 50
        vessel1.static_data.dimensions.to_port = 15
        vessel1.static_data.dimensions.to_starboard = 15
        vessel1.voyage_data.destination = "OAKLAND"
        vessel1.voyage_data.draught = 12.5
        
        # Vessel 2: Fishing vessel
        vessel2 = create_vessel_state(
            mmsi=367002345,
            vessel_name="PACIFIC DAWN",
            position=Position(37.7500, -122.4500),
            vessel_class=VesselClass.CLASS_A,
            callsign="FISH01",
            ship_type=ShipType.FISHING,
            sog=8.2,
            cog=180.0,
            heading=185,
            nav_status=NavigationStatus.ENGAGED_IN_FISHING
        )
        
        vessel2.static_data.dimensions.to_bow = 25
        vessel2.static_data.dimensions.to_stern = 5
        vessel2.static_data.dimensions.to_port = 4
        vessel2.static_data.dimensions.to_starboard = 4
        
        self.vessels = [vessel1, vessel2]
    
    def generate_scenario(self, duration_minutes=10):
        """Generate a complete scenario with reference data and network output."""
        
        print(f"Generating {duration_minutes}-minute scenario with {len(self.vessels)} vessels...")
        
        # Output files
        nmea_file = self.output_dir / "nmea_output.txt"
        reference_file = self.output_dir / "reference_data.json"
        human_file = self.output_dir / "human_readable.txt"
        
        start_time = datetime.now()
        current_time = start_time
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        with open(nmea_file, 'w') as nmea_f, open(human_file, 'w') as human_f:
            
            human_f.write("NMEA Simulator Output - Human Readable\n")
            human_f.write("=" * 60 + "\n")
            human_f.write(f"Generated: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            human_f.write(f"Duration: {duration_minutes} minutes\n")
            human_f.write(f"Vessels: {len(self.vessels)}\n")
            human_f.write("=" * 60 + "\n\n")
            
            step = 0
            while current_time < end_time:
                step += 1
                
                # Update vessel positions (simple linear movement)
                self._update_vessel_positions(current_time, start_time)
                
                # Generate GPS sentences every 5 seconds
                if step % 5 == 0:
                    for vessel in self.vessels:
                        gps_sentences = self._generate_gps_sentences(vessel, current_time)
                        for sentence in gps_sentences:
                            # Write to file
                            nmea_f.write(sentence + "\n")
                            # Send to network
                            self.network.send_sentence(sentence)
                            # Add reference data
                            self._add_reference_data(sentence, "GPS", current_time, vessel.mmsi)
                            self._write_human_readable(human_f, sentence, "GPS", current_time, vessel)
                
                # Generate AIS Type 1 messages every 10 seconds
                if step % 10 == 0:
                    for vessel in self.vessels:
                        try:
                            ais_sentences = self._generate_ais_type1(vessel, current_time)
                            for sentence in ais_sentences:
                                # Write to file
                                nmea_f.write(sentence + "\n")
                                # Send to network
                                self.network.send_sentence(sentence)
                                # Add reference data
                                self._add_reference_data(sentence, "AIS", current_time, vessel.mmsi, 1)
                                self._write_human_readable(human_f, sentence, "AIS", current_time, vessel, 1)
                        except Exception as e:
                            print(f"Error generating AIS for vessel {vessel.mmsi}: {e}")
                
                # Generate AIS Type 5 messages every 60 seconds
                if step % 60 == 0:
                    for vessel in self.vessels:
                        if vessel.static_data.vessel_class == VesselClass.CLASS_A:
                            try:
                                ais_sentences = self._generate_ais_type5(vessel, current_time)
                                for sentence in ais_sentences:
                                    # Write to file
                                    nmea_f.write(sentence + "\n")
                                    # Send to network
                                    self.network.send_sentence(sentence)
                                    # Add reference data
                                    self._add_reference_data(sentence, "AIS", current_time, vessel.mmsi, 5)
                                    self._write_human_readable(human_f, sentence, "AIS", current_time, vessel, 5)
                            except Exception as e:
                                print(f"Error generating AIS Type 5 for vessel {vessel.mmsi}: {e}")
                
                # Progress indicator
                if step % 60 == 0:
                    elapsed = (current_time - start_time).total_seconds()
                    progress = elapsed / (duration_minutes * 60) * 100
                    tcp_clients = len(self.network.tcp_clients) if self.network.tcp_clients else 0
                    print(f"Progress: {progress:.1f}% - Generated {self.message_count} messages - TCP clients: {tcp_clients}")
                
                # Advance time by 1 second
                current_time += timedelta(seconds=1)
        
        # Save reference data
        self._save_reference_data(reference_file)
        
        print(f"\nScenario generation complete!")
        print(f"Generated {self.message_count} messages")
        print(f"Files created:")
        print(f"  NMEA output: {nmea_file}")
        print(f"  Reference data: {reference_file}")
        print(f"  Human readable: {human_file}")
        
        if self.network.tcp_port:
            print(f"  TCP server: localhost:{self.network.tcp_port}")
        if self.network.udp_port:
            print(f"  UDP broadcast: port {self.network.udp_port}")
        
        return {
            'nmea_file': str(nmea_file),
            'reference_file': str(reference_file),
            'human_readable': str(human_file)
        }
    
    def _update_vessel_positions(self, current_time, start_time):
        """Update vessel positions with simple linear movement."""
        elapsed_seconds = (current_time - start_time).total_seconds()
        
        for vessel in self.vessels:
            # Simple linear movement
            speed_ms = vessel.navigation_data.sog * 0.514444  # knots to m/s
            distance_m = speed_ms * elapsed_seconds
            
            # Calculate new position (simplified)
            lat_change = (distance_m * 0.000009) * (1 if vessel.navigation_data.cog < 180 else -1)
            lon_change = (distance_m * 0.000009) * (1 if 90 < vessel.navigation_data.cog < 270 else -1)
            
            new_lat = vessel.navigation_data.position.latitude + lat_change
            new_lon = vessel.navigation_data.position.longitude + lon_change
            
            vessel.navigation_data.position = Position(new_lat, new_lon)
            vessel.timestamp = current_time
    
    def _generate_gps_sentences(self, vessel, current_time):
        """Generate GPS sentences for a vessel."""
        sentences = []
        nav = vessel.navigation_data
        
        # Create time string
        time_str = current_time.strftime("%H%M%S.%f")[:-3]  # HHMMSS.sss
        date_str = current_time.strftime("%d%m%y")  # DDMMYY
        
        # Import SentenceBuilder
        from nmea_lib.parser import SentenceBuilder
        from nmea_lib.base import TalkerId, SentenceId
        
        # GGA sentence - GPS Fix Data
        gga_builder = SentenceBuilder(TalkerId.GP, SentenceId.GGA)
        gga_builder.add_field(time_str)  # UTC time
        
        # Position fields
        lat_deg = int(abs(nav.position.latitude))
        lat_min = (abs(nav.position.latitude) - lat_deg) * 60
        lat_str = f"{lat_deg:02d}{lat_min:07.4f}"
        lat_hem = "N" if nav.position.latitude >= 0 else "S"
        
        lon_deg = int(abs(nav.position.longitude))
        lon_min = (abs(nav.position.longitude) - lon_deg) * 60
        lon_str = f"{lon_deg:03d}{lon_min:07.4f}"
        lon_hem = "E" if nav.position.longitude >= 0 else "W"
        
        gga_builder.add_field(lat_str)  # Latitude
        gga_builder.add_field(lat_hem)  # Latitude hemisphere
        gga_builder.add_field(lon_str)  # Longitude
        gga_builder.add_field(lon_hem)  # Longitude hemisphere
        gga_builder.add_field("1")      # Fix quality (1 = GPS fix)
        gga_builder.add_field("08")     # Number of satellites
        gga_builder.add_field("1.2")    # HDOP
        gga_builder.add_field("0.0")    # Altitude
        gga_builder.add_field("M")      # Altitude units
        gga_builder.add_field("19.6")   # Geoidal height
        gga_builder.add_field("M")      # Geoidal height units
        gga_builder.add_field("")       # DGPS age
        gga_builder.add_field("")       # DGPS station ID
        
        sentences.append(gga_builder.build().strip())
        
        # RMC sentence - Recommended Minimum
        rmc_builder = SentenceBuilder(TalkerId.GP, SentenceId.RMC)
        rmc_builder.add_field(time_str)  # UTC time
        rmc_builder.add_field("A")       # Status (A = active)
        rmc_builder.add_field(lat_str)   # Latitude
        rmc_builder.add_field(lat_hem)   # Latitude hemisphere
        rmc_builder.add_field(lon_str)   # Longitude
        rmc_builder.add_field(lon_hem)   # Longitude hemisphere
        rmc_builder.add_field(f"{nav.sog:.1f}")  # Speed over ground
        rmc_builder.add_field(f"{nav.cog:.1f}")  # Course over ground
        rmc_builder.add_field(date_str)  # Date
        rmc_builder.add_field("0.0")     # Magnetic variation
        rmc_builder.add_field("E")       # Variation direction
        
        sentences.append(rmc_builder.build().strip())
        
        return sentences
    
    def _generate_ais_type1(self, vessel, current_time):
        """Generate AIS Type 1 position report."""
        try:
            # Use the proper AIS message generator
            sentences, input_data = self.ais_generator.generate_type_1(vessel)
            return sentences
        except Exception as e:
            print(f"Error generating AIS Type 1 for vessel {vessel.mmsi}: {e}")
            # Fallback to empty list if generation fails
            return []
    
    def _generate_ais_type5(self, vessel, current_time):
        """Generate AIS Type 5 static and voyage data."""
        try:
            # Use the proper AIS message generator
            sentences, input_data = self.ais_generator.generate_type_5(vessel)
            return sentences
        except Exception as e:
            print(f"Error generating AIS Type 5 for vessel {vessel.mmsi}: {e}")
            # Fallback to empty list if generation fails
            return []
    
    def _add_reference_data(self, sentence, msg_type, timestamp, vessel_mmsi, ais_msg_type=None):
        """Add reference data for validation."""
        ref = {
            'timestamp': timestamp.isoformat(),
            'message_type': msg_type,
            'sentence': sentence,
            'vessel_mmsi': vessel_mmsi,
            'ais_message_type': ais_msg_type
        }
        
        # Add vessel data for reference
        vessel = next((v for v in self.vessels if v.mmsi == vessel_mmsi), None)
        if vessel:
            ref['vessel_data'] = {
                'name': vessel.static_data.vessel_name,
                'position': {
                    'latitude': vessel.navigation_data.position.latitude,
                    'longitude': vessel.navigation_data.position.longitude
                },
                'sog': vessel.navigation_data.sog,
                'cog': vessel.navigation_data.cog,
                'heading': vessel.navigation_data.heading
            }
        
        self.reference_data.append(ref)
        self.message_count += 1
    
    def _write_human_readable(self, file, sentence, msg_type, timestamp, vessel, ais_msg_type=None):
        """Write human-readable explanation."""
        time_str = timestamp.strftime('%H:%M:%S')
        nav = vessel.navigation_data
        
        file.write(f"[{time_str}] ")
        
        if msg_type == 'GPS':
            if sentence.startswith('$GPGGA'):
                file.write(f"GPS Fix - {vessel.static_data.vessel_name} (MMSI: {vessel.mmsi})\n")
                file.write(f"  Position: {nav.position.latitude:.6f}, {nav.position.longitude:.6f}\n")
            elif sentence.startswith('$GPRMC'):
                file.write(f"GPS RMC - {vessel.static_data.vessel_name}\n")
                file.write(f"  Speed: {nav.sog:.1f} knots, Course: {nav.cog:.1f}°\n")
        
        elif msg_type == 'AIS':
            file.write(f"AIS Type {ais_msg_type} - {vessel.static_data.vessel_name} (MMSI: {vessel.mmsi})\n")
            if ais_msg_type == 1:
                file.write(f"  Position Report: {nav.position.latitude:.6f}, {nav.position.longitude:.6f}\n")
                file.write(f"  Speed: {nav.sog:.1f} knots, Course: {nav.cog:.1f}°, Heading: {nav.heading}°\n")
            elif ais_msg_type == 5:
                file.write(f"  Static Data: {vessel.static_data.vessel_name}\n")
                file.write(f"  Call Sign: {vessel.static_data.callsign}, Destination: {vessel.voyage_data.destination}\n")
        
        file.write(f"  Sentence: {sentence}\n\n")
    
    def _save_reference_data(self, file_path):
        """Save reference data to JSON file."""
        data = {
            'generation_info': {
                'timestamp': datetime.now().isoformat(),
                'vessel_count': len(self.vessels),
                'total_messages': len(self.reference_data)
            },
            'vessels': [
                {
                    'mmsi': v.mmsi,
                    'name': v.static_data.vessel_name,
                    'call_sign': v.static_data.callsign,
                    'ship_type': v.static_data.ship_type.value,
                    'vessel_class': v.static_data.vessel_class.value
                }
                for v in self.vessels
            ],
            'messages': self.reference_data
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def close(self):
        """Close network connections."""
        self.network.close()


def main():
    """Main function."""
    print("=" * 70)
    print("ENHANCED NMEA+AIS SIMULATOR WITH NETWORK SUPPORT")
    print("=" * 70)
    print()
    
    # Get user input
    try:
        duration = input("Duration in minutes [5]: ").strip()
        duration = int(duration) if duration else 5
        
        output_dir = input("Output directory [enhanced_output]: ").strip()
        output_dir = output_dir if output_dir else "enhanced_output"
        
        # Network options
        print("\nNetwork output options:")
        tcp_input = input("TCP port (empty to disable) [2000]: ").strip()
        tcp_port = int(tcp_input) if tcp_input else 2000
        
        udp_input = input("UDP port (empty to disable) [2001]: ").strip()
        udp_port = int(udp_input) if udp_input else 2001
        
    except (ValueError, KeyboardInterrupt):
        print("Using default values...")
        duration = 5
        output_dir = "enhanced_output"
        tcp_port = 2000
        udp_port = 2001
    
    print(f"\nConfiguration:")
    print(f"  Duration: {duration} minutes")
    print(f"  Output directory: {output_dir}")
    print(f"  TCP port: {tcp_port}")
    print(f"  UDP port: {udp_port}")
    print()
    
    # Create and run simulator
    simulator = EnhancedNMEASimulator(output_dir, tcp_port, udp_port)
    
    try:
        print("Starting simulation...")
        print("Connect your NMEA clients to:")
        print(f"  TCP: localhost:{tcp_port}")
        print(f"  UDP: broadcast port {udp_port}")
        print()
        
        files = simulator.generate_scenario(duration)
        
        print("\n" + "=" * 70)
        print("GENERATION COMPLETE")
        print("=" * 70)
        
        # Show sample output
        nmea_file = files['nmea_file']
        if Path(nmea_file).exists():
            print("\nSample NMEA output (first 5 lines):")
            with open(nmea_file, 'r') as f:
                for i, line in enumerate(f):
                    if i >= 5:
                        break
                    print(f"  {line.strip()}")
        
        print("\nUsage for decoder validation:")
        print(f"1. Feed '{nmea_file}' to your AIS decoder")
        print(f"2. Compare results with '{files['reference_file']}'")
        print(f"3. Check '{files['human_readable']}' for explanations")
        print()
        print("Network streaming:")
        print(f"  TCP clients can connect to localhost:{tcp_port}")
        print(f"  UDP clients can listen on port {udp_port}")
        print()
        print("Press Enter to stop network servers...")
        input()
        
    except KeyboardInterrupt:
        print("\nStopping simulation...")
    
    finally:
        simulator.close()
        print("Network connections closed.")


if __name__ == "__main__":
    main()
