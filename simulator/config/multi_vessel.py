"""Multi-vessel configuration system for AIS and GPS simulation."""

import yaml
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from nmea_lib.types import Position
from nmea_lib.types.vessel import VesselClass, ShipType, NavigationStatus, EPFDType, AtoNType
from simulator.generators.vessel import create_default_vessel_config


@dataclass
class ScenarioConfig:
    """Configuration for a simulation scenario."""
    name: str
    description: str
    duration: Optional[float] = None  # seconds, None = infinite
    area: Optional[Dict[str, float]] = None  # lat_min, lat_max, lon_min, lon_max
    vessels: List[Dict[str, Any]] = None
    base_stations: List[Dict[str, Any]] = None
    aids_to_navigation: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.vessels is None:
            self.vessels = []
        if self.base_stations is None:
            self.base_stations = []
        if self.aids_to_navigation is None:
            self.aids_to_navigation = []


class MultiVesselConfigManager:
    """Manages configuration for multi-vessel simulations."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.scenarios: Dict[str, ScenarioConfig] = {}
        self.vessel_templates: Dict[str, Dict[str, Any]] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default vessel templates."""
        self.vessel_templates = {
            'cargo_ship': {
                'vessel_class': 'A',
                'ship_type': 70,  # Cargo ship
                'dimensions': {
                    'to_bow': 100,
                    'to_stern': 20,
                    'to_port': 10,
                    'to_starboard': 10
                },
                'initial_speed': 12.0,
                'movement': {
                    'pattern': 'linear',
                    'speed_variation': 2.0,
                    'course_variation': 5.0
                }
            },
            'container_ship': {
                'vessel_class': 'A',
                'ship_type': 70,
                'dimensions': {
                    'to_bow': 200,
                    'to_stern': 40,
                    'to_port': 15,
                    'to_starboard': 15
                },
                'initial_speed': 18.0,
                'movement': {
                    'pattern': 'linear',
                    'speed_variation': 1.5,
                    'course_variation': 3.0
                }
            },
            'tanker': {
                'vessel_class': 'A',
                'ship_type': 80,  # Tanker
                'dimensions': {
                    'to_bow': 150,
                    'to_stern': 30,
                    'to_port': 12,
                    'to_starboard': 12
                },
                'initial_speed': 14.0,
                'movement': {
                    'pattern': 'linear',
                    'speed_variation': 1.0,
                    'course_variation': 2.0
                }
            },
            'fishing_vessel': {
                'vessel_class': 'A',
                'ship_type': 30,  # Fishing
                'dimensions': {
                    'to_bow': 25,
                    'to_stern': 5,
                    'to_port': 3,
                    'to_starboard': 3
                },
                'initial_speed': 8.0,
                'movement': {
                    'pattern': 'random_walk',
                    'speed_variation': 3.0,
                    'course_variation': 30.0
                }
            },
            'pleasure_craft': {
                'vessel_class': 'B',
                'ship_type': 37,  # Pleasure craft
                'dimensions': {
                    'to_bow': 8,
                    'to_stern': 2,
                    'to_port': 1,
                    'to_starboard': 1
                },
                'initial_speed': 15.0,
                'movement': {
                    'pattern': 'waypoint',
                    'speed_variation': 5.0,
                    'course_variation': 20.0
                }
            },
            'pilot_vessel': {
                'vessel_class': 'A',
                'ship_type': 50,  # Pilot vessel
                'dimensions': {
                    'to_bow': 15,
                    'to_stern': 3,
                    'to_port': 2,
                    'to_starboard': 2
                },
                'initial_speed': 20.0,
                'movement': {
                    'pattern': 'circular',
                    'speed_variation': 4.0,
                    'course_variation': 15.0
                }
            },
            'tug': {
                'vessel_class': 'A',
                'ship_type': 52,  # Tug
                'dimensions': {
                    'to_bow': 20,
                    'to_stern': 5,
                    'to_port': 3,
                    'to_starboard': 3
                },
                'initial_speed': 10.0,
                'movement': {
                    'pattern': 'linear',
                    'speed_variation': 3.0,
                    'course_variation': 25.0
                }
            }
        }
    
    def create_scenario(self, name: str, description: str) -> ScenarioConfig:
        """Create a new scenario."""
        scenario = ScenarioConfig(name=name, description=description)
        self.scenarios[name] = scenario
        return scenario
    
    def add_vessel_to_scenario(self, scenario_name: str, vessel_config: Dict[str, Any]):
        """Add a vessel to a scenario."""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        
        self.scenarios[scenario_name].vessels.append(vessel_config)
    
    def add_base_station_to_scenario(self, scenario_name: str, base_station_config: Dict[str, Any]):
        """Add a base station to a scenario."""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        
        self.scenarios[scenario_name].base_stations.append(base_station_config)
    
    def add_aid_to_navigation_to_scenario(self, scenario_name: str, aid_nav_config: Dict[str, Any]):
        """Add an aid to navigation to a scenario."""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        
        self.scenarios[scenario_name].aids_to_navigation.append(aid_nav_config)
    
    def create_vessel_from_template(self, template_name: str, mmsi: int, name: str, 
                                  position: Position, **overrides) -> Dict[str, Any]:
        """Create a vessel configuration from a template."""
        if template_name not in self.vessel_templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Start with template
        vessel_config = self.vessel_templates[template_name].copy()
        
        # Set required fields
        vessel_config['mmsi'] = mmsi
        vessel_config['name'] = name
        vessel_config['callsign'] = f"CALL{mmsi % 10000}"
        vessel_config['initial_position'] = {
            'latitude': position.latitude,
            'longitude': position.longitude
        }
        
        # Apply overrides
        for key, value in overrides.items():
            if key in vessel_config:
                if isinstance(vessel_config[key], dict) and isinstance(value, dict):
                    vessel_config[key].update(value)
                else:
                    vessel_config[key] = value
            else:
                vessel_config[key] = value
        
        return vessel_config
    
    def create_fleet_scenario(self, name: str, fleet_config: Dict[str, Any]) -> ScenarioConfig:
        """Create a scenario with multiple vessels (fleet)."""
        scenario = self.create_scenario(name, fleet_config.get('description', f'Fleet scenario: {name}'))
        
        # Set scenario area if provided
        if 'area' in fleet_config:
            scenario.area = fleet_config['area']
        
        # Set duration if provided
        if 'duration' in fleet_config:
            scenario.duration = fleet_config['duration']
        
        # Add vessels
        for vessel_def in fleet_config.get('vessels', []):
            template = vessel_def.get('template', 'cargo_ship')
            mmsi = vessel_def['mmsi']
            name = vessel_def.get('name', f'VESSEL_{mmsi}')
            position = Position(
                vessel_def['position']['latitude'],
                vessel_def['position']['longitude']
            )
            
            # Get overrides
            overrides = {k: v for k, v in vessel_def.items() 
                        if k not in ['template', 'mmsi', 'name', 'position']}
            
            vessel_config = self.create_vessel_from_template(
                template, mmsi, name, position, **overrides
            )
            
            self.add_vessel_to_scenario(scenario.name, vessel_config)
        
        # Add base stations
        for bs_def in fleet_config.get('base_stations', []):
            self.add_base_station_to_scenario(scenario.name, bs_def)
        
        # Add aids to navigation
        for aid_def in fleet_config.get('aids_to_navigation', []):
            self.add_aid_to_navigation_to_scenario(scenario.name, aid_def)
        
        return scenario
    
    def load_scenario_from_file(self, file_path: str) -> ScenarioConfig:
        """Load scenario from YAML or JSON file."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {file_path}")
        
        with open(path, 'r') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
        
        # Create scenario
        scenario_name = data.get('name', path.stem)
        scenario = ScenarioConfig(
            name=scenario_name,
            description=data.get('description', ''),
            duration=data.get('duration'),
            area=data.get('area'),
            vessels=data.get('vessels', []),
            base_stations=data.get('base_stations', []),
            aids_to_navigation=data.get('aids_to_navigation', [])
        )
        
        self.scenarios[scenario_name] = scenario
        return scenario
    
    def save_scenario_to_file(self, scenario_name: str, file_path: str):
        """Save scenario to YAML or JSON file."""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        
        scenario = self.scenarios[scenario_name]
        path = Path(file_path)
        
        # Convert to dictionary
        data = asdict(scenario)
        
        with open(path, 'w') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(data, f, default_flow_style=False, indent=2)
            elif path.suffix.lower() == '.json':
                json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def get_scenario(self, name: str) -> Optional[ScenarioConfig]:
        """Get scenario by name."""
        return self.scenarios.get(name)
    
    def list_scenarios(self) -> List[str]:
        """List all scenario names."""
        return list(self.scenarios.keys())
    
    def list_templates(self) -> List[str]:
        """List all vessel template names."""
        return list(self.vessel_templates.keys())
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get vessel template by name."""
        return self.vessel_templates.get(name)
    
    def add_template(self, name: str, template: Dict[str, Any]):
        """Add a new vessel template."""
        self.vessel_templates[name] = template
    
    def create_random_fleet(self, name: str, vessel_count: int, area: Dict[str, float],
                           templates: Optional[List[str]] = None) -> ScenarioConfig:
        """Create a scenario with randomly positioned vessels."""
        import random
        
        if templates is None:
            templates = list(self.vessel_templates.keys())
        
        scenario = self.create_scenario(name, f'Random fleet with {vessel_count} vessels')
        scenario.area = area
        
        lat_min, lat_max = area['lat_min'], area['lat_max']
        lon_min, lon_max = area['lon_min'], area['lon_max']
        
        for i in range(vessel_count):
            # Random position within area
            lat = random.uniform(lat_min, lat_max)
            lon = random.uniform(lon_min, lon_max)
            position = Position(lat, lon)
            
            # Random template
            template = random.choice(templates)
            
            # Generate MMSI (starting from 200000000 for simulation)
            mmsi = 200000000 + i
            
            # Random heading
            heading = random.uniform(0, 360)
            
            vessel_config = self.create_vessel_from_template(
                template, mmsi, f'RANDOM_{i:03d}', position,
                initial_heading=heading
            )
            
            self.add_vessel_to_scenario(name, vessel_config)
        
        return scenario
    
    def validate_scenario(self, scenario_name: str) -> List[str]:
        """Validate scenario configuration and return list of issues."""
        if scenario_name not in self.scenarios:
            return [f"Scenario '{scenario_name}' not found"]
        
        scenario = self.scenarios[scenario_name]
        issues = []
        
        # Check for duplicate MMSIs
        mmsis = set()
        for vessel in scenario.vessels:
            mmsi = vessel.get('mmsi')
            if mmsi in mmsis:
                issues.append(f"Duplicate MMSI: {mmsi}")
            mmsis.add(mmsi)
        
        for bs in scenario.base_stations:
            mmsi = bs.get('mmsi')
            if mmsi in mmsis:
                issues.append(f"Duplicate MMSI (base station): {mmsi}")
            mmsis.add(mmsi)
        
        for aid in scenario.aids_to_navigation:
            mmsi = aid.get('mmsi')
            if mmsi in mmsis:
                issues.append(f"Duplicate MMSI (aid to navigation): {mmsi}")
            mmsis.add(mmsi)
        
        # Validate vessel configurations
        for i, vessel in enumerate(scenario.vessels):
            vessel_issues = self._validate_vessel_config(vessel, f"vessel[{i}]")
            issues.extend(vessel_issues)
        
        return issues
    
    def _validate_vessel_config(self, config: Dict[str, Any], prefix: str) -> List[str]:
        """Validate a single vessel configuration."""
        issues = []
        
        # Required fields
        required_fields = ['mmsi', 'name', 'initial_position']
        for field in required_fields:
            if field not in config:
                issues.append(f"{prefix}: Missing required field '{field}'")
        
        # MMSI validation
        mmsi = config.get('mmsi')
        if mmsi and not (100000000 <= mmsi <= 999999999):
            issues.append(f"{prefix}: Invalid MMSI {mmsi} (must be 9 digits)")
        
        # Position validation
        pos = config.get('initial_position', {})
        lat = pos.get('latitude')
        lon = pos.get('longitude')
        
        if lat is not None and not (-90 <= lat <= 90):
            issues.append(f"{prefix}: Invalid latitude {lat}")
        
        if lon is not None and not (-180 <= lon <= 180):
            issues.append(f"{prefix}: Invalid longitude {lon}")
        
        # Ship type validation
        ship_type = config.get('ship_type')
        if ship_type is not None and not (0 <= ship_type <= 99):
            issues.append(f"{prefix}: Invalid ship type {ship_type} (must be 0-99)")
        
        return issues


# Predefined scenarios
def create_san_francisco_bay_scenario() -> Dict[str, Any]:
    """Create a scenario for San Francisco Bay area, now with Class B and AtoN."""
    return {
        'name': 'san_francisco_bay_extended',
        'description': 'Multi-vessel simulation in San Francisco Bay with Class B and AtoN',
        'duration': 3600,  # 1 hour
        'area': {
            'lat_min': 37.7,
            'lat_max': 37.9,
            'lon_min': -122.5,
            'lon_max': -122.3
        },
        'vessels': [
            {
                'template': 'container_ship',
                'mmsi': 367001234,
                'name': 'EVER FORWARD',
                'position': {'latitude': 37.8, 'longitude': -122.4},
                'initial_heading': 90,
                'initial_speed': 15.0
            },
            {
                'template': 'tanker',
                'mmsi': 367005678,
                'name': 'CHEVRON STAR',
                'position': {'latitude': 37.75, 'longitude': -122.45},
                'initial_heading': 270,
                'initial_speed': 12.0
            },
            {
                'template': 'fishing_vessel', # This is Class A as per default templates
                'mmsi': 367009012,
                'name': 'PACIFIC DAWN',
                'position': {'latitude': 37.85, 'longitude': -122.35},
                'movement': {
                    'pattern': 'random_walk',
                    'bounds': {
                        'lat_min': 37.8,
                        'lat_max': 37.9,
                        'lon_min': -122.4,
                        'lon_max': -122.3
                    }
                }
            },
            {
                'template': 'pilot_vessel', # This is Class A
                'mmsi': 367003456,
                'name': 'SF PILOT 1',
                'position': {'latitude': 37.82, 'longitude': -122.42},
                'movement': {
                    'pattern': 'circular',
                    'circle': {
                        'center': {'latitude': 37.82, 'longitude': -122.42},
                        'radius': 500  # meters
                    }
                }
            },
            # ADDED: Class B Vessel (e.g., pleasure craft)
            {
                'template': 'pleasure_craft', # This template is Class B
                'mmsi': 368000001, # Example Class B MMSI (ensure unique)
                'name': 'BAY CRUISER',
                'position': {'latitude': 37.78, 'longitude': -122.38},
                'initial_heading': 45,
                'initial_speed': 8.0,
                # 'vessel_class': VesselClass.CLASS_B, # Template should define this.
                                                      # If VesselClass is not auto-imported, this might cause an error.
                                                      # The template 'pleasure_craft' already sets vessel_class = 'B'.
                'movement': {
                    'pattern': 'waypoint',
                    'waypoints': [
                        {'latitude': 37.78, 'longitude': -122.38},
                        {'latitude': 37.79, 'longitude': -122.37},
                        {'latitude': 37.77, 'longitude': -122.36},
                    ],
                    'loop': True
                }
            }
        ],
        'base_stations': [
            {
                'mmsi': 3669999, # Standard USCG Base Station MMSI (MID 366, type 99, number 99)
                'name': 'SF_BASE_1',
                'position': {'latitude': 37.8, 'longitude': -122.4}
            }
        ],
        # ADDED: Aids to Navigation
        'aids_to_navigation': [
            {
                'mmsi': 993670001, # AtoN MMSI: 99 + MID (367 for US) + unique number
                'name': 'SF_ATON_EAST_CHANNEL_BUOY',
                'aton_type': AtoNType.STARBOARD_HAND_MARK.value, # Example: Starboard hand mark
                'position': {'latitude': 37.81, 'longitude': -122.36},
                'epfd_type': EPFDType.GPS.value,
                'virtual_aton': False,
                'off_position': False,
                'dimensions': { # Optional: physical dimensions of the AtoN structure
                    'to_bow': 2, 'to_stern': 2, 'to_port': 2, 'to_starboard': 2
                }
            },
            {
                'mmsi': 993670002,
                'name': 'SF_ATON_BRIDGE_CENTER_VIRTUAL',
                'aton_type': AtoNType.REFERENCE_POINT.value, # Example: Reference point
                'position': {'latitude': 37.8197, 'longitude': -122.4783}, # Approx. Golden Gate center
                'epfd_type': EPFDType.GPS.value,
                'virtual_aton': True,
                'off_position': False
                # No dimensions for virtual AtoN
            }
        ]
    }


def create_english_channel_scenario() -> Dict[str, Any]:
    """Create a scenario for English Channel shipping."""
    return {
        'name': 'english_channel',
        'description': 'High-density shipping in English Channel',
        'duration': 7200,  # 2 hours
        'area': {
            'lat_min': 50.5,
            'lat_max': 51.0,
            'lon_min': 1.0,
            'lon_max': 2.0
        },
        'vessels': [
            {
                'template': 'container_ship',
                'mmsi': 235001234,
                'name': 'MAERSK ESSEX',
                'position': {'latitude': 50.7, 'longitude': 1.2},
                'initial_heading': 60,
                'initial_speed': 20.0
            },
            {
                'template': 'container_ship',
                'mmsi': 255005678,
                'name': 'CMA CGM MARCO POLO',
                'position': {'latitude': 50.8, 'longitude': 1.8},
                'initial_heading': 240,
                'initial_speed': 18.0
            },
            {
                'template': 'tanker',
                'mmsi': 235009012,
                'name': 'BRITISH EMERALD',
                'position': {'latitude': 50.6, 'longitude': 1.5},
                'initial_heading': 90,
                'initial_speed': 14.0
            }
        ]
    }


# Factory function
def create_config_manager() -> MultiVesselConfigManager:
    """Create a new configuration manager."""
    return MultiVesselConfigManager()

