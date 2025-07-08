# Python NMEA 0183 Simulator

A comprehensive Python-based NMEA 0183 data simulator for marine equipment testing, development, and training applications.

## Overview

This project provides a realistic NMEA 0183 data stream simulator that can generate various sentence types with configurable parameters. It's designed with a modular architecture separating the core NMEA library from the simulation engine.

## Features

### Core NMEA Library
- ✅ NMEA 0183 sentence parsing and encoding
- ✅ Comprehensive data types (Position, Time, Speed, Bearing, etc.)
- ✅ Sentence validation and checksum calculation
- ✅ Support for GGA and RMC sentences
- ✅ Extensible architecture for additional sentence types

### Simulation Engine
- ✅ Realistic GPS position simulation with movement variation
- ✅ Time management with configurable speed factors
- ✅ Multi-threaded architecture for concurrent operations
- ✅ Configurable sentence generation rates

### Output Options
- ✅ **File Output**: Log to files with rotation support
- ✅ **TCP Server**: Multi-client TCP server for network distribution
- ✅ **UDP Broadcast**: UDP broadcast/multicast for network distribution

### Configuration System
- ✅ YAML-based configuration files
- ✅ Flexible vessel and movement parameters
- ✅ Configurable sentence types and rates
- ✅ Multiple output handler configuration

## Installation

### Prerequisites
- Python 3.8 or higher
- PyYAML library

### Setup
1. Extract the archive to your desired location
2. Navigate to the project directory:
   ```bash
   cd nmea-simulator
   ```

3. Install dependencies:
   ```bash
   pip3 install pyyaml
   ```

## Quick Start

### 1. Basic File Output Simulation
Run a simple 60-second simulation that outputs to a file:

```bash
python3 examples/simple_simulation.py
```

This will:
- Generate GGA and RMC sentences at 1Hz
- Simulate vessel movement from San Francisco Bay
- Output to `nmea_output.log`
- Display real-time position updates

### 2. Network Distribution Simulation
Run a simulation with TCP and UDP network outputs:

```bash
python3 examples/network_simulation.py
```

This will:
- Start TCP server on port 10110
- Start UDP broadcast on port 10111
- Include built-in test clients
- Display network activity in real-time

### 3. Custom Configuration
Create your own configuration file or modify existing ones:

```bash
# Copy example configuration
cp config/example_config.yaml config/my_config.yaml

# Edit configuration
nano config/my_config.yaml

# Run with custom configuration
python3 -c "
from simulator.core.engine import SimulationEngine
from simulator.config.parser import ConfigParser
from simulator.outputs.factory import OutputFactory

config = ConfigParser.from_file('config/my_config.yaml')
engine = SimulationEngine(config)

if hasattr(config, 'output_configs'):
    handlers = OutputFactory.create_output_handlers(config.output_configs)
    for handler in handlers:
        engine.add_output_handler(handler)

engine.start()
input('Press Enter to stop...')
engine.stop()
"
```

## Configuration Guide

### Basic Configuration Structure

```yaml
simulation:
  duration: 300        # Simulation duration in seconds
  time_factor: 1.0     # Speed multiplier (1.0 = real-time)
  start_time: null     # ISO format or null for current time

vessel:
  name: "My Vessel"
  initial_position:
    latitude: 37.7749   # Decimal degrees
    longitude: -122.4194
  initial_speed: 10.0   # Knots
  initial_heading: 45.0 # Degrees true

movement:
  speed_variation: 2.0     # Speed variation in knots
  course_variation: 10.0   # Course variation in degrees
  position_noise: 0.00001  # GPS noise in degrees

sentences:
  - type: GGA           # Sentence type
    talker_id: GP       # Talker ID (GP, GL, GA, etc.)
    rate: 1.0          # Generation rate in Hz
    enabled: true

outputs:
  - type: file
    enabled: true
    path: "output.log"
    
  - type: tcp
    enabled: true
    host: "0.0.0.0"
    port: 10110
    
  - type: udp
    enabled: true
    host: "255.255.255.255"
    port: 10111
    broadcast: true
```

### Output Handler Options

#### File Output
```yaml
- type: file
  enabled: true
  path: "nmea_output.log"
  append: true                    # Append to existing file
  auto_flush: true               # Auto-flush writes
  rotation_size_mb: 10           # Rotate when file exceeds size
  rotation_time_hours: 24        # Rotate every N hours
  max_files: 5                   # Keep N rotated files
```

#### TCP Server Output
```yaml
- type: tcp
  enabled: true
  host: "0.0.0.0"               # Bind address
  port: 10110                   # Port number
  max_clients: 10               # Maximum concurrent clients
  client_timeout: 30.0          # Client timeout in seconds
  send_timeout: 5.0             # Send timeout in seconds
```

#### UDP Broadcast Output
```yaml
- type: udp
  enabled: true
  host: "255.255.255.255"       # Broadcast address
  port: 10111                   # Port number
  broadcast: true               # Enable broadcast
  multicast_group: null         # Multicast group (optional)
  multicast_ttl: 1              # Multicast TTL
  send_timeout: 1.0             # Send timeout in seconds
```

## NMEA Sentence Types

### Currently Supported

#### GGA - Global Positioning System Fix Data
Contains position, time, fix quality, and satellite information.

Example: `$GPGGA,120044,3746.4953,N,12225.1625,W,1,8,1.2,50.0,M,19.6,M,,*4A`

#### RMC - Recommended Minimum Navigation Information
Contains position, time, date, speed, course, and status information.

Example: `$GPRMC,120044,A,3746.4953,N,12225.1625,W,5.0,43.3,260625,6.1,E,A*20`

## Testing Network Outputs

### TCP Client Test
```bash
# Connect to TCP server and display received sentences
telnet localhost 10110
```

### UDP Client Test
```bash
# Listen for UDP broadcasts (Linux/Mac)
nc -u -l 10111

# Or use Python
python3 -c "
import socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.bind(('', 10111))
    while True:
        data, addr = s.recvfrom(1024)
        print(f'{addr[0]}: {data.decode()}'.strip())
"
```

## Project Structure

```
nmea-simulator/
├── nmea_lib/                    # Core NMEA library
│   ├── sentences/               # Sentence implementations
│   │   ├── gga.py              # GGA sentence
│   │   └── rmc.py              # RMC sentence
│   ├── types/                  # Data types
│   │   ├── position.py         # Position handling
│   │   ├── datetime.py         # Time/date handling
│   │   ├── units.py            # Speed/bearing/distance
│   │   └── enums.py            # Enumerations
│   ├── base.py                 # Base classes
│   ├── parser.py               # Sentence parsing
│   ├── validator.py            # Validation utilities
│   └── factory.py              # Sentence factory
├── simulator/                  # Simulation engine
│   ├── core/                   # Core components
│   │   ├── engine.py           # Main simulation engine
│   │   └── time_manager.py     # Time management
│   ├── generators/             # Data generators
│   │   └── position.py         # Position generation
│   ├── outputs/                # Output handlers
│   │   ├── base.py             # Base output handler
│   │   ├── file.py             # File output
│   │   ├── tcp.py              # TCP server output
│   │   ├── udp.py              # UDP broadcast output
│   │   └── factory.py          # Output factory
│   └── config/                 # Configuration
│       └── parser.py           # Config file parser
├── config/                     # Configuration files
│   ├── example_config.yaml     # Basic example
│   └── network_config.yaml     # Network example
├── examples/                   # Usage examples
│   ├── simple_simulation.py    # Basic file output
│   └── network_simulation.py   # Network distribution
├── tests/                      # Unit tests
│   └── test_nmea_lib.py        # Core library tests
└── docs/                       # Documentation
```

## Development and Testing

### Running Unit Tests
```bash
python3 -m unittest tests.test_nmea_lib -v
```

### Validating NMEA Output
```bash
# Check generated sentences
python3 -c "
from nmea_lib import SentenceValidator
with open('nmea_output.log') as f:
    for i, line in enumerate(f):
        if line.startswith('\$'):
            valid = SentenceValidator.is_valid(line.strip())
            print(f'Line {i+1}: {valid} - {line.strip()[:50]}...')
"
```

### Adding New Sentence Types
1. Create new sentence class in `nmea_lib/sentences/`
2. Register with factory in `nmea_lib/sentences/__init__.py`
3. Add generator method to simulation engine
4. Update configuration parser if needed

## Troubleshooting

### Common Issues

#### "Permission denied" on network ports
- Use ports > 1024 for non-root users
- Check firewall settings
- Ensure ports are not already in use

#### "Module not found" errors
- Ensure you're running from the project root directory
- Check Python path and imports
- Install required dependencies

#### TCP clients can't connect
- Verify server is running and listening
- Check host/port configuration
- Test with telnet first

#### UDP broadcasts not received
- Check network configuration
- Verify broadcast addresses
- Test on localhost first

### Debug Mode
Enable verbose output by modifying the examples:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Notes

- File output: ~1000+ sentences/second
- TCP output: ~500+ sentences/second per client
- UDP output: ~1000+ sentences/second
- Memory usage: ~10-50MB depending on configuration

## License

This project is open source. See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues and questions:
1. Check this README and configuration examples
2. Review the unit tests for usage patterns
3. Examine the example scripts
4. Check the troubleshooting section

## Version History

- v1.0.0: Initial release with GGA/RMC support and network outputs
- Core NMEA library with parsing and validation
- Multi-threaded simulation engine
- File, TCP, and UDP output handlers
- YAML configuration system

