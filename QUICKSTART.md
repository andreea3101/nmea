# Quick Start Guide - Python NMEA Simulator

## 1. Installation (30 seconds)

```bash
# Extract the archive
unzip nmea-simulator.zip
cd nmea-simulator

# Install dependencies
pip3 install pyyaml

# Verify installation
python3 -m unittest tests.test_nmea_lib -v
```

## 2. Run Your First Simulation (1 minute)

```bash
# Basic file output simulation
python3 examples/simple_simulation.py
```

You should see output like:
```
NMEA Simulator - Simple Example
========================================
Vessel: Example Vessel
Initial position: 37.774900, -122.419400
Initial speed: 5.0 knots
Duration: 60 seconds

Starting simulation...
[   5.0s] Pos: 37.775077, -122.419233 Speed: 5.4kts Heading: 45.9° Sentences: 8
[  10.0s] Pos: 37.775221, -122.419069 Speed: 5.6kts Heading: 44.2° Sentences: 18
...
```

Check the generated file:
```bash
head -10 nmea_output.log
```

## 3. Test Network Distribution (2 minutes)

```bash
# Run network simulation with TCP and UDP
python3 examples/network_simulation.py
```

In another terminal, test TCP connection:
```bash
telnet localhost 10110
```

You should see live NMEA sentences streaming.

## 4. Customize Your Simulation (5 minutes)

Edit the configuration:
```bash
cp config/example_config.yaml config/my_config.yaml
nano config/my_config.yaml
```

Change parameters like:
- `initial_position`: Your desired starting location
- `initial_speed`: Vessel speed in knots
- `duration`: How long to run
- `sentences`: Which NMEA types to generate

## 5. Common Use Cases

### Marine Software Testing
```yaml
# High-frequency, precise simulation
sentences:
  - type: GGA
    rate: 10.0  # 10Hz for high precision
  - type: RMC
    rate: 1.0   # 1Hz for navigation
```

### Training and Demonstration
```yaml
# Slow, visible movement
simulation:
  time_factor: 10.0  # 10x speed
vessel:
  initial_speed: 20.0  # Fast movement
```

### Network Distribution
```yaml
outputs:
  - type: tcp
    port: 10110
  - type: udp
    port: 10111
    broadcast: true
```

## 6. Validation

Verify your NMEA output:
```bash
python3 -c "
from nmea_lib import SentenceValidator
with open('nmea_output.log') as f:
    valid_count = 0
    total_count = 0
    for line in f:
        if line.startswith('\$'):
            total_count += 1
            if SentenceValidator.is_valid(line.strip()):
                valid_count += 1
    print(f'Valid sentences: {valid_count}/{total_count}')
"
```

## Need Help?

- Check `README.md` for detailed documentation
- Look at `config/` directory for example configurations
- Review `examples/` directory for usage patterns
- Run unit tests: `python3 -m unittest tests.test_nmea_lib -v`

