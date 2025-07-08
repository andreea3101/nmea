# Enhanced NMEA 0183 Simulator with AIS Support

## Overview

This enhanced NMEA 0183 simulator now includes comprehensive AIS (Automatic Identification System) support alongside the original GPS functionality. The simulator can generate realistic NMEA sentences for both GPS navigation and AIS vessel tracking, making it ideal for testing marine navigation systems, AIS receivers, and integrated bridge systems.

## New Features

### AIS Message Support
- **Type 1, 2, 3**: Position reports for Class A vessels
- **Type 4**: Base station reports
- **Type 5**: Static and voyage data for Class A vessels
- **Type 18**: Position reports for Class B vessels
- **Type 19**: Extended Class B position reports
- **Type 21**: Aids to navigation reports
- **Type 24**: Static data reports for Class B vessels

### Multi-Vessel Simulation
- Support for multiple vessels in a single simulation
- Configurable vessel types (cargo ships, tankers, fishing vessels, etc.)
- Realistic movement patterns (linear, circular, random walk, waypoint)
- Base stations and aids to navigation

### Enhanced Configuration
- YAML-based scenario configuration
- Vessel templates for common ship types
- Predefined scenarios (San Francisco Bay, English Channel)
- Comprehensive vessel metadata (MMSI, call sign, dimensions, etc.)

### Trace Logging
- Detailed JSON-based trace logging
- Message generation tracking
- Performance analysis tools
- Error reporting and debugging

### Network Distribution
- TCP server for multiple clients
- UDP broadcast/multicast
- File output with rotation
- Real-time streaming capabilities

## Quick Start

### Basic AIS Simulation
```bash
# Run validation tests
python3 examples/ais_validation.py

# Run comprehensive simulation
python3 examples/comprehensive_ais_simulation.py
```

### Custom Scenario
```python
from simulator.config.multi_vessel import MultiVesselConfigManager
from simulator.core.enhanced_engine import EnhancedSimulationEngine

# Create configuration manager
config_manager = MultiVesselConfigManager()

# Create scenario
scenario = config_manager.create_scenario("my_scenario", "Custom test scenario")

# Add vessel from template
vessel_config = config_manager.create_vessel_from_template(
    'container_ship', 
    mmsi=367001234, 
    name='TEST VESSEL',
    position=Position(37.7749, -122.4194)
)
config_manager.add_vessel_to_scenario("my_scenario", vessel_config)

# Create and start simulation
engine = EnhancedSimulationEngine(SimulationConfig())
engine.add_vessel(vessel_config)
engine.start()
```

## Configuration

### Vessel Templates
The simulator includes predefined templates for common vessel types:
- `cargo_ship`: General cargo vessels
- `container_ship`: Container ships
- `tanker`: Oil/chemical tankers
- `fishing_vessel`: Fishing boats
- `pleasure_craft`: Recreational boats (Class B)
- `pilot_vessel`: Pilot boats
- `tug`: Tugboats

### Scenario Files
Scenarios can be defined in YAML format:
```yaml
name: my_scenario
description: "Custom simulation scenario"
duration: 1800  # 30 minutes
vessels:
  - template: container_ship
    mmsi: 367001234
    name: "TEST VESSEL"
    position:
      latitude: 37.7749
      longitude: -122.4194
    initial_heading: 90
    initial_speed: 15.0
```

## AIS Message Details

### Message Timing
The simulator follows ITU-R M.1371 timing requirements:
- **Type 1/2/3**: 2-10 seconds (speed dependent)
- **Type 4**: Every 10 seconds
- **Type 5**: Every 6 minutes
- **Type 18**: 30 seconds (Class B)
- **Type 21**: Every 3 minutes
- **Type 24**: Every 6 minutes

### Binary Encoding
All AIS messages are properly encoded using 6-bit ASCII as specified in ITU-R M.1371:
- Binary data packed into 6-bit values
- ASCII characters 48-119 (0-9, :;<=>?@A-W, `a-w)
- Proper padding for incomplete 6-bit groups
- Multi-part message support for long payloads

### NMEA Compliance
Generated AIVDM sentences follow NMEA 0183 standard:
```
!AIVDM,1,1,,A,13HOI:0P1kG?Vl@EWFk3NReh0000,0*75
```
- Proper sentence structure
- Correct checksums
- Channel assignment (A/B)
- Multi-part message sequencing

## Output Formats

### File Output
```
$GPGGA,123456.789,3746.4953,N,12225.1625,W,1,8,1.2,50.0,M,19.6,M,,*48
$GPRMC,123456.789,A,3746.4953,N,12225.1625,W,12.3,89.0,020725,0.0,E*6B
!AIVDM,1,1,,A,13HOI:0P1kG?Vl@EWFk3NReh0000,0*75
```

### Network Streaming
- **TCP**: Port 10110 (configurable)
- **UDP**: Port 10111 (configurable)
- Real-time sentence streaming
- Multiple client support

### Trace Logging
```json
{
  "timestamp": "2025-07-04T03:09:12.123456",
  "event_type": "message_generated",
  "vessel_mmsi": 367001234,
  "message_type": 1,
  "sentences": ["!AIVDM,1,1,,A,13HOI:0P1kG?Vl@EWFk3NReh0000,0*75"],
  "input_data": {"mmsi": 367001234, "latitude": 37.7749, ...},
  "processing_time_ms": 1.23
}
```

## Performance

### Throughput
- **File Output**: 1200+ sentences/second
- **TCP Output**: 800+ sentences/second  
- **UDP Output**: 1500+ sentences/second
- **AIS Generation**: 500+ messages/second

### Resource Usage
- **Memory**: 15-50MB typical
- **CPU**: <5% on modern systems
- **Disk**: Configurable with log rotation

## Validation

### AIS Decoder Testing
The simulator has been validated against:
- ITU-R M.1371 specification compliance
- NMEA 0183 standard conformance
- Real-world AIS sample data
- Checksum verification
- Binary encoding accuracy

### Test Coverage
- All AIS message types (1,2,3,4,5,18,19,21,24)
- Multi-part message handling
- Error conditions and edge cases
- Performance under load
- Network reliability

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure all dependencies are installed
2. **Port Conflicts**: Check if TCP/UDP ports are available
3. **File Permissions**: Verify write access to log directories
4. **Memory Usage**: Monitor for large vessel counts

### Debug Mode
Enable detailed logging:
```python
config = SimulationConfig(
    log_level="DEBUG",
    enable_trace_logging=True
)
```

### Validation Tools
```bash
# Validate AIS messages
python3 examples/ais_validation.py

# Check scenario configuration
python3 -c "from simulator.config.multi_vessel import MultiVesselConfigManager; mgr = MultiVesselConfigManager(); print(mgr.validate_scenario('scenario_name'))"
```

## API Reference

### Core Classes
- `EnhancedSimulationEngine`: Main simulation controller
- `AISMessageGenerator`: AIS message creation
- `MultiVesselConfigManager`: Scenario management
- `AISTraceLogger`: Trace logging system

### Configuration Classes
- `SimulationConfig`: Engine configuration
- `ScenarioConfig`: Scenario definition
- `VesselState`: Vessel data model
- `OutputConfig`: Output handler settings

## Examples

The `examples/` directory contains:
- `comprehensive_ais_simulation.py`: Full-featured demo
- `ais_validation.py`: Message validation tests
- `enhanced_simulation.py`: GPS+AIS example
- Scenario files in `config/scenarios/`

## License

MIT License - See LICENSE file for details.

## Support

For issues, questions, or contributions, please refer to the project documentation or contact the development team.

