"""Unit tests for NMEA library core functionality."""

import unittest
from datetime import datetime
from nmea_lib import (
    SentenceValidator, SentenceParser, SentenceFactory,
    GGASentence, RMCSentence, TalkerId, SentenceId,
    Position, NMEATime, NMEADate, Speed, SpeedUnit
)
from nmea_lib.ais.constants import AISMessageType
from nmea_lib.sentences.aivdm import AISMessageGenerator
from nmea_lib.types.vessel import VesselState, VesselNavigationData, VesselStaticData, VesselVoyageData, Position
from nmea_lib.types.datetime import NMEADateTime


class TestSentenceValidator(unittest.TestCase):
    """Test NMEA sentence validation."""
    
    def test_valid_gga_sentence(self):
        """Test validation of valid GGA sentence."""
        sentence = "$GPGGA,120044,6011.552,N,02501.941,E,1,08,2.0,28.0,M,19.6,M,,*71"
        self.assertTrue(SentenceValidator.is_valid(sentence))
    
    def test_invalid_checksum(self):
        """Test validation with invalid checksum."""
        sentence = "$GPGGA,120044,6011.552,N,02501.941,E,1,08,2.0,28.0,M,19.6,M,,*78"
        self.assertFalse(SentenceValidator.is_valid(sentence))
    
    def test_invalid_format(self):
        """Test validation with invalid format."""
        sentence = "GPGGA,120044,6011.552,N,02501.941,E,1,08,2.0,28.0,M,19.6,M,,*71"
        self.assertFalse(SentenceValidator.is_valid(sentence))
    
    def test_checksum_calculation(self):
        """Test checksum calculation."""
        sentence_body = "GPGGA,120044,6011.552,N,02501.941,E,1,08,2.0,28.0,M,19.6,M,,"
        expected_checksum = "71"
        calculated = SentenceValidator.calculate_checksum(sentence_body)
        self.assertEqual(calculated, expected_checksum)


class TestSentenceParser(unittest.TestCase):
    """Test NMEA sentence parsing."""
    
    def test_parse_gga_sentence(self):
        """Test parsing GGA sentence."""
        sentence = "$GPGGA,120044,6011.552,N,02501.941,E,1,08,2.0,28.0,M,19.6,M,,*71"
        parser = SentenceParser(sentence)
        
        self.assertTrue(parser.is_valid())
        self.assertEqual(parser.talker_id, TalkerId.GP)
        self.assertEqual(parser.sentence_id, SentenceId.GGA)
        self.assertEqual(parser.get_field(0), "120044")
        self.assertEqual(parser.get_field(1), "6011.552")
    
    def test_field_access(self):
        """Test field access methods."""
        sentence = "$GPGGA,120044,6011.552,N,02501.941,E,1,08,2.0,28.0,M,19.6,M,,*71"
        parser = SentenceParser(sentence)
        
        self.assertEqual(parser.get_int_field(5), 1)  # Fix quality
        self.assertEqual(parser.get_int_field(6), 8)  # Satellites
        self.assertEqual(parser.get_float_field(7), 2.0)  # HDOP


class TestGGASentence(unittest.TestCase):
    """Test GGA sentence implementation."""
    
    def test_parse_gga_sentence(self):
        """Test parsing complete GGA sentence."""
        sentence_str = "$GPGGA,120044,6011.552,N,02501.941,E,1,08,2.0,28.0,M,19.6,M,,*71"
        sentence = GGASentence.from_sentence(sentence_str)
        
        self.assertEqual(sentence.talker_id, TalkerId.GP)
        self.assertEqual(sentence.sentence_id, SentenceId.GGA)
        
        # Check time
        time_obj = sentence._time
        self.assertIsNotNone(time_obj)
        self.assertEqual(time_obj.hour, 12)
        self.assertEqual(time_obj.minute, 0)
        self.assertEqual(time_obj.second, 44)
        
        # Check position
        position = sentence._position
        self.assertIsNotNone(position)
        self.assertAlmostEqual(position.latitude, 60.19253333, places=6)
        self.assertAlmostEqual(position.longitude, 25.03235, places=6)
        
        # Check other fields
        self.assertEqual(sentence.get_satellites_in_use(), 8)
        self.assertEqual(sentence.get_horizontal_dilution(), 2.0)
    
    def test_create_gga_sentence(self):
        """Test creating GGA sentence from scratch."""
        sentence = GGASentence()
        
        # Set data
        sentence.set_time("120044")
        sentence.set_position(60.19253333, 25.03235)
        sentence.set_satellites_in_use(8)
        sentence.set_horizontal_dilution(2.0)
        
        # Generate sentence string
        sentence_str = sentence.to_sentence()
        self.assertTrue(sentence_str.startswith("$GPGGA"))
        self.assertTrue(SentenceValidator.is_valid(sentence_str))


class TestRMCSentence(unittest.TestCase):
    """Test RMC sentence implementation."""
    
    def test_parse_rmc_sentence(self):
        """Test parsing complete RMC sentence."""
        sentence_str = "$GPRMC,120044,A,6011.552,N,02501.941,E,000.0,360.0,160705,006.1,E,A*11"
        sentence = RMCSentence.from_sentence(sentence_str)
        
        self.assertEqual(sentence.talker_id, TalkerId.GP)
        self.assertEqual(sentence.sentence_id, SentenceId.RMC)
        
        # Check position
        position = sentence._position
        self.assertIsNotNone(position)
        self.assertAlmostEqual(position.latitude, 60.19253333, places=6)
        
        # Check speed and course
        speed = sentence.get_speed()
        self.assertIsNotNone(speed)
        self.assertEqual(speed.value, 0.0)
        
        course = sentence.get_course()
        self.assertIsNotNone(course)
        self.assertEqual(course.value, 360.0)
        
        # Check date
        date_obj = sentence._date
        self.assertIsNotNone(date_obj)
        self.assertEqual(date_obj.day, 16)
        self.assertEqual(date_obj.month, 7)
        self.assertEqual(date_obj.year, 2005)


class TestPosition(unittest.TestCase):
    """Test Position data type."""
    
    def test_nmea_conversion(self):
        """Test NMEA format conversion."""
        position = Position(60.19253333, 25.03235)
        lat_str, lat_hem, lon_str, lon_hem = position.to_nmea()
        
        self.assertEqual(lat_str, "6011.5520")
        self.assertEqual(lat_hem, "N")
        self.assertEqual(lon_str, "02501.9410")
        self.assertEqual(lon_hem, "E")
        
        # Test round-trip conversion
        position2 = Position.from_nmea(lat_str, lat_hem, lon_str, lon_hem)
        self.assertAlmostEqual(position.latitude, position2.latitude, places=6)
        self.assertAlmostEqual(position.longitude, position2.longitude, places=6)
    
    def test_distance_calculation(self):
        """Test distance calculation between positions."""
        pos1 = Position(60.0, 25.0)
        pos2 = Position(61.0, 25.0)
        
        distance = pos1.distance_to(pos2)
        # Approximately 111 km for 1 degree latitude
        self.assertGreater(distance, 100000)
        self.assertLess(distance, 120000)


class TestNMEATime(unittest.TestCase):
    """Test NMEA time handling."""
    
    def test_time_parsing(self):
        """Test time parsing from NMEA format."""
        time_obj = NMEATime.from_nmea("120044.123")
        
        self.assertEqual(time_obj.hour, 12)
        self.assertEqual(time_obj.minute, 0)
        self.assertEqual(time_obj.second, 44)
        self.assertEqual(time_obj.microsecond, 123000)
    
    def test_time_formatting(self):
        """Test time formatting to NMEA format."""
        time_obj = NMEATime(12, 0, 44, 123000)
        
        self.assertEqual(time_obj.to_nmea(), "120044.123")
        self.assertEqual(time_obj.to_nmea(include_fractional=False), "120044")


class TestAIVDMSentence(unittest.TestCase):
    """Test AIVDM sentence generation."""

    def test_generate_type_9(self):
        """Test generating a Type 9 Standard SAR Aircraft Position Report."""
        # Create a mock vessel state for a SAR aircraft
        nav_data = VesselNavigationData(
            position=Position(latitude=34.567, longitude=-118.123),
            sog=250.0,  # Speed in knots
            cog=123.4,
            heading=120,
            nav_status=0,
            rot=0,
            timestamp=25,
            position_accuracy=1,
            raim=0,
            radio_status=0
        )
        # SAR aircraft specific data
        nav_data.altitude = 1500  # Altitude in meters

        static_data = VesselStaticData(mmsi=987654321)
        voyage_data = VesselVoyageData()

        vessel_state = VesselState(
            static_data=static_data,
            navigation_data=nav_data,
            voyage_data=voyage_data,
            timestamp_sim=NMEADateTime.from_datetime(datetime(2023, 1, 1, 12, 0, 44)).to_datetime(),
        )

        # Generate the Type 9 message
        generator = AISMessageGenerator()
        sentences, _ = generator.generate_message(
            message_type=AISMessageType.STANDARD_SAR_AIRCRAFT_POSITION_REPORT,
            vessel_data=vessel_state,
            channel='A'
        )

        # Validate the generated sentence
        self.assertEqual(len(sentences), 1)
        sentence = sentences[0]
        self.assertTrue(sentence.startswith("!AIVDM,1,1,,A,"))
        self.assertTrue(SentenceValidator.is_valid(sentence))

        # Further checks can be added here to decode the payload and verify the data
        # For example, extract payload, decode from 6-bit, and check fields.
        # This is a basic test to ensure the generator runs and produces a valid sentence.


if __name__ == '__main__':
    unittest.main()

