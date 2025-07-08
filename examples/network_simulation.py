#!/usr/bin/env python3
"""Network NMEA simulation example with TCP and UDP outputs."""

import sys
import time
import threading
import socket
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.core.engine import SimulationEngine
from simulator.config.parser import ConfigParser
from simulator.outputs.factory import OutputFactory


def tcp_client_test(host='localhost', port=10110, duration=30):
    """Test TCP client connection."""
    print(f"Starting TCP client test to {host}:{port}")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            sock.settimeout(5.0)
            
            start_time = time.time()
            sentence_count = 0
            
            while time.time() - start_time < duration:
                try:
                    data = sock.recv(1024)
                    if data:
                        sentences = data.decode('utf-8').strip().split('\n')
                        for sentence in sentences:
                            if sentence.startswith('$'):
                                sentence_count += 1
                                print(f"TCP: {sentence}")
                    else:
                        break
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"TCP client error: {e}")
                    break
            
            print(f"TCP client received {sentence_count} sentences")
    
    except Exception as e:
        print(f"TCP client connection failed: {e}")


def udp_client_test(host='localhost', port=10111, duration=30):
    """Test UDP client reception."""
    print(f"Starting UDP client test on port {port}")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(('', port))
            sock.settimeout(5.0)
            
            start_time = time.time()
            sentence_count = 0
            
            while time.time() - start_time < duration:
                try:
                    data, addr = sock.recvfrom(1024)
                    if data:
                        sentence = data.decode('utf-8').strip()
                        if sentence.startswith('$'):
                            sentence_count += 1
                            print(f"UDP from {addr[0]}: {sentence}")
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"UDP client error: {e}")
                    break
            
            print(f"UDP client received {sentence_count} sentences")
    
    except Exception as e:
        print(f"UDP client setup failed: {e}")


def main():
    """Run network NMEA simulation example."""
    print("NMEA Simulator - Network Example")
    print("=" * 50)
    
    # Load configuration
    config_path = "config/network_config.yaml"
    if not Path(config_path).exists():
        print(f"Configuration file not found: {config_path}")
        print("Please run from the nmea-simulator directory")
        return
    
    try:
        config = ConfigParser.from_file(config_path)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return
    
    print(f"Vessel: {config.vessel_name}")
    print(f"Initial position: {config.initial_latitude:.6f}, {config.initial_longitude:.6f}")
    print(f"Initial speed: {config.initial_speed} knots")
    print(f"Duration: {config.duration_seconds} seconds")
    print()
    
    # Create simulation engine
    engine = SimulationEngine(config)
    
    # Create output handlers from configuration
    if hasattr(config, 'output_configs'):
        output_handlers = OutputFactory.create_output_handlers(config.output_configs)
        
        for handler in output_handlers:
            engine.add_output_handler(handler)
            print(f"Added output handler: {handler}")
    else:
        print("No output configuration found")
        return
    
    print()
    
    # Start client test threads
    client_threads = []
    
    # Check if TCP output is configured
    tcp_enabled = any(oc.type == 'tcp' and oc.enabled for oc in config.output_configs)
    if tcp_enabled:
        tcp_thread = threading.Thread(
            target=tcp_client_test, 
            args=('localhost', 10110, 60), 
            daemon=True
        )
        client_threads.append(tcp_thread)
    
    # Check if UDP output is configured
    udp_enabled = any(oc.type == 'udp' and oc.enabled for oc in config.output_configs)
    if udp_enabled:
        udp_thread = threading.Thread(
            target=udp_client_test, 
            args=('localhost', 10111, 60), 
            daemon=True
        )
        client_threads.append(udp_thread)
    
    try:
        print("Starting simulation...")
        engine.start()
        
        # Give the server a moment to start
        time.sleep(2)
        
        # Start client test threads
        for thread in client_threads:
            thread.start()
        
        # Monitor simulation
        start_time = time.time()
        while engine.running:
            time.sleep(10)  # Update every 10 seconds
            
            status = engine.get_status()
            elapsed = time.time() - start_time
            
            print(f"\n[{elapsed:6.1f}s] Simulation Status:")
            print(f"  Position: {status['position']['latitude']:.6f}, {status['position']['longitude']:.6f}")
            print(f"  Speed: {status['position']['speed_knots']:.1f} knots")
            print(f"  Heading: {status['position']['heading_degrees']:.1f}°")
            print(f"  Total sentences: {status['statistics']['total_sentences']}")
            
            # Show output handler status
            for i, handler_status in enumerate(status['output_handlers']):
                handler_type = "unknown"
                if 'server_address' in handler_status:
                    handler_type = "TCP"
                elif 'targets' in handler_status:
                    handler_type = "UDP"
                elif 'file_path' in handler_status:
                    handler_type = "File"
                
                print(f"  {handler_type} output: {handler_status.get('sentences_sent', 0)} sentences")
                
                if handler_type == "TCP":
                    client_count = handler_status.get('client_count', 0)
                    print(f"    TCP clients: {client_count}")
        
        print("\nSimulation completed!")
        
        # Show final statistics
        final_status = engine.get_status()
        stats = final_status['statistics']
        
        print(f"\nFinal Statistics:")
        print(f"  Total sentences: {stats['total_sentences']}")
        print(f"  Runtime: {stats['runtime_seconds']:.1f} seconds")
        print(f"  Rate: {stats['sentences_per_second']:.1f} sentences/second")
        print(f"  Sentences by type: {stats['sentences_by_type']}")
        
        # Wait for client threads to finish
        for thread in client_threads:
            thread.join(timeout=5)
    
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
    
    except Exception as e:
        print(f"Error during simulation: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("Stopping simulation...")
        engine.stop()
        print("Done.")


if __name__ == "__main__":
    main()

