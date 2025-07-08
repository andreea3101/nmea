#!/usr/bin/env python3
"""Enhanced NMEA simulation example showing original NMEA messages."""

import sys
import time
from pathlib import Path
from collections import deque

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.core.engine import SimulationEngine
from simulator.config.parser import SimulatorConfig
from simulator.outputs.file import FileOutput, FileOutputConfig
from simulator.outputs.base import OutputHandler


class ConsoleOutput(OutputHandler):
    """Output handler that displays NMEA sentences to console."""
    
    def __init__(self, max_display=5):
        """Initialize console output handler."""
        super().__init__()
        self.max_display = max_display
        self.recent_sentences = deque(maxlen=max_display)
    
    def start(self) -> None:
        """Start console output."""
        self.is_running = True
        print("Console output started - showing NMEA sentences:")
        print("-" * 80)
    
    def stop(self) -> None:
        """Stop console output."""
        self.is_running = False
        print("-" * 80)
        print("Console output stopped")
    
    def send_sentence(self, sentence: str) -> bool:
        """Display NMEA sentence to console."""
        if not self.is_running:
            return False
        
        try:
            # Parse sentence type from NMEA string
            sentence_clean = sentence.strip()
            if sentence_clean.startswith('$') and ',' in sentence_clean:
                # Extract sentence type (e.g., GPGGA, GPRMC)
                parts = sentence_clean.split(',')
                sentence_type = parts[0][1:]  # Remove $ prefix
                talker_id = sentence_type[:2]  # First 2 chars (GP, GL, etc.)
                msg_type = sentence_type[2:]   # Last 3 chars (GGA, RMC, etc.)
                
                # Store for recent display
                self.recent_sentences.append({
                    'sentence': sentence_clean,
                    'type': msg_type,
                    'talker': talker_id,
                    'timestamp': time.time()
                })
                
                # Display immediately
                print(f"[{msg_type}] {sentence_clean}")
                
                self.sentences_sent += 1
                return True
            
        except Exception as e:
            print(f"Error displaying sentence: {e}")
            return False
        
        return False
    
    def get_recent_sentences(self):
        """Get recently sent sentences."""
        return list(self.recent_sentences)


def main():
    """Run enhanced NMEA simulation with message display."""
    print("NMEA Simulator - Enhanced Example with Message Display")
    print("=" * 60)
    
    # Create configuration
    config = SimulatorConfig.create_example()
    config.duration_seconds = 60  # 1 minute simulation
    config.initial_speed = 5.0  # 5 knots
    
    print(f"Vessel: {config.vessel_name}")
    print(f"Initial position: {config.initial_latitude:.6f}, {config.initial_longitude:.6f}")
    print(f"Initial speed: {config.initial_speed} knots")
    print(f"Duration: {config.duration_seconds} seconds")
    print()
    
    # Create simulation engine
    engine = SimulationEngine(config)
    
    # Add file output
    file_config = FileOutputConfig(
        file_path="nmea_output_enhanced.log",
        append_mode=False,  # Overwrite existing file
        auto_flush=True
    )
    file_output = FileOutput(file_config)
    engine.add_output_handler(file_output)
    
    # Add console output to see live NMEA messages
    console_output = ConsoleOutput(max_display=10)
    engine.add_output_handler(console_output)
    
    try:
        print("Starting simulation...")
        engine.start()
        
        # Monitor simulation
        start_time = time.time()
        last_sentence_count = 0
        
        while engine.running:
            time.sleep(5)  # Update every 5 seconds
            
            status = engine.get_status()
            elapsed = time.time() - start_time
            
            # Show position and statistics
            print(f"\n[{elapsed:6.1f}s] STATUS UPDATE:")
            print(f"  Position: {status['position']['latitude']:.6f}, {status['position']['longitude']:.6f}")
            print(f"  Speed: {status['position']['speed_knots']:.1f} knots")
            print(f"  Heading: {status['position']['heading_degrees']:.1f}°")
            print(f"  Total sentences: {status['statistics']['total_sentences']}")
            
            # Show sentence breakdown
            sentence_types = status['statistics']['sentences_by_type']
            print(f"  Sentence types: {sentence_types}")
            
            # Show recent sentences from console output
            recent = console_output.get_recent_sentences()
            if recent:
                print(f"  Recent NMEA messages:")
                for msg in recent[-3:]:  # Show last 3 messages
                    age = time.time() - msg['timestamp']
                    print(f"    [{msg['talker']}{msg['type']}] {msg['sentence']} ({age:.1f}s ago)")
            
            print("-" * 60)
        
        print("\nSimulation completed!")
        
        # Show final statistics
        final_status = engine.get_status()
        stats = final_status['statistics']
        
        print(f"\nFinal Statistics:")
        print(f"  Total sentences: {stats['total_sentences']}")
        print(f"  Runtime: {stats['runtime_seconds']:.1f} seconds")
        print(f"  Rate: {stats['sentences_per_second']:.1f} sentences/second")
        print(f"  Sentences by type: {stats['sentences_by_type']}")
        
        # Show output file info
        if Path("nmea_output_enhanced.log").exists():
            file_size = Path("nmea_output_enhanced.log").stat().st_size
            print(f"  Output file: nmea_output_enhanced.log ({file_size} bytes)")
        
        # Show sample of generated sentences
        print(f"\nSample NMEA sentences from file:")
        try:
            with open("nmea_output_enhanced.log", 'r') as f:
                lines = [line.strip() for line in f if line.startswith('$')]
                for i, line in enumerate(lines[:5]):  # Show first 5 sentences
                    sentence_type = line.split(',')[0][1:] if ',' in line else "UNKNOWN"
                    print(f"  {i+1}. [{sentence_type}] {line}")
                if len(lines) > 5:
                    print(f"  ... and {len(lines)-5} more sentences")
        except Exception as e:
            print(f"  Error reading file: {e}")
        
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

