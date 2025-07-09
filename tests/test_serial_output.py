"""Tests for the SerialOutput handler."""

import pytest
import time
import os
import pty # For creating virtual serial ports (Unix-like specific)
import serial # For reading from the virtual serial port

from simulator.outputs.serial_output import SerialOutput, SerialOutputConfig
from simulator.outputs.factory import OutputFactory
from simulator.config.parser import ConfigParser, OutputConfig


@pytest.fixture
def virtual_serial_ports(scope="function"):
    """Creates a virtual serial port pair using pty."""
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)

    # Configure the slave port to be non-blocking for reads
    # This is important so that the test doesn't hang if data isn't immediately available.
    # import fcntl
    # flags = fcntl.fcntl(slave_fd, fcntl.F_GETFL)
    # fcntl.fcntl(slave_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    # Note: Making it non-blocking can be tricky with pty.
    # For simplicity in this initial test, we might rely on timeouts or known data lengths.

    print(f"Virtual serial port pair created: Master FD: {master_fd}, Slave: {slave_name} (FD: {slave_fd})")

    yield slave_name, master_fd  # Slave name for SerialOutput, master_fd for test to read from

    print("Closing virtual serial port pair...")
    os.close(master_fd)
    os.close(slave_fd)
    print("Virtual serial ports closed.")


@pytest.mark.skipif(not hasattr(pty, "openpty"), reason="pty module not available on this system (e.g., Windows)")
class TestSerialOutput:

    def test_serial_output_initialization(self, virtual_serial_ports):
        """Test basic initialization of SerialOutput."""
        slave_name, _ = virtual_serial_ports
        config = SerialOutputConfig(port=slave_name, baudrate=9600, timeout=0.1, write_timeout=0.1)
        handler = SerialOutput(config)
        assert handler.config.port == slave_name
        assert not handler.is_running
        assert handler.serial_port is None

    def test_serial_output_start_stop(self, virtual_serial_ports):
        """Test starting and stopping SerialOutput."""
        slave_name, _ = virtual_serial_ports
        config = SerialOutputConfig(port=slave_name, baudrate=9600, timeout=0.1, write_timeout=0.1, max_reconnect_attempts=0)
        handler = SerialOutput(config)

        try:
            handler.start()
            assert handler.is_running
            assert handler.serial_port is not None
            assert handler.serial_port.is_open
            assert handler.serial_port.port == slave_name
        finally:
            handler.stop()

        assert not handler.is_running
        # After stop, serial_port object might still exist but should be closed, or set to None
        assert handler.serial_port is None or not handler.serial_port.is_open
        # Check if the reconnect thread is cleaned up if it was ever started
        assert handler._reconnect_thread is None or not handler._reconnect_thread.is_alive()


    def test_serial_output_send_sentence(self, virtual_serial_ports):
        """Test sending a sentence over SerialOutput."""
        slave_name, master_fd = virtual_serial_ports
        config = SerialOutputConfig(
            port=slave_name,
            baudrate=9600,
            timeout=0.1,
            write_timeout=0.1,
            line_ending="\n", # Use simple newline for test reading
            max_reconnect_attempts=0
        )
        handler = SerialOutput(config)
        test_sentence = "$GPGGA,test_data*CHECKSUM"

        try:
            handler.start()
            assert handler.is_running, "Handler should be running"

            sent = handler.send_sentence(test_sentence)
            assert sent, "send_sentence should return True on success"
            assert handler.sentences_sent == 1

            # Read from the master end of the pty
            # This needs to be robust. The data might not arrive instantaneously.
            # Set a timeout for the read operation.

            # Create a serial object to read from the master_fd with appropriate settings
            # This is a bit of a hack, as master_fd is not a typical serial device path.
            # A more direct os.read might be better but can block.
            # For pty, direct os.read is the way.

            # Give some time for data to be written and available
            time.sleep(0.2) # Increased sleep

            # Read with a timeout (select can be used for non-blocking read with timeout on fd)
            # For simplicity, let's try a direct read with a small buffer.
            # This might be flaky if timing is off.
            try:
                # os.set_blocking(master_fd, False) # This might be needed
                # Ensure master_fd is non-blocking for the read attempt to avoid hangs
                # flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
                # fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                # This can be problematic as it changes global state of fd.
                # A better approach is using select.select() to check for readability.
                # For now, a simple read with a small timeout via select would be ideal,
                # but os.read() itself doesn't directly support a timeout.
                # We'll rely on the short sleep and hope the data is there.

                received_data_bytes = os.read(master_fd, 1024) # Read up to 1024 bytes
                # The sentence is sent with config.line_ending, which is "\n" for this test.
                # os.read will get "$GPGGA,test_data*CHECKSUM\n"
                # .strip() will remove the trailing "\n"
                received_data = received_data_bytes.decode('utf-8').strip()
                print(f"Received on master: '{received_data_bytes.decode('utf-8')}' -> Stripped: '{received_data}'") # Debug print
                assert received_data == test_sentence
            except BlockingIOError:
                pytest.fail("Read from master_fd blocked or no data received in non-blocking mode.")
            except Exception as e:
                pytest.fail(f"Error reading from master_fd: {e}")

        finally:
            handler.stop()

    def test_serial_config_parsing_and_factory(self, virtual_serial_ports):
        """Test parsing serial config and creating handler via factory."""
        slave_name, _ = virtual_serial_ports

        # Minimal config data for serial
        raw_config_data = {
            'outputs': [
                {
                    'type': 'serial',
                    'enabled': True,
                    'port': slave_name,
                    'baudrate': 19200,
                    'timeout': 0.05, # 50ms
                    'line_ending': "\r\n",
                    'max_reconnect_attempts': 0
                }
            ]
        }

        # Use ConfigParser to parse this snippet
        # We are interested in the OutputConfig part
        parsed_sim_config = ConfigParser.from_dict(raw_config_data)
        assert len(parsed_sim_config.output_configs) == 1

        output_conf: OutputConfig = parsed_sim_config.output_configs[0]
        assert output_conf.type == 'serial'
        assert output_conf.enabled
        assert isinstance(output_conf.config, SerialOutputConfig)
        assert output_conf.config.port == slave_name
        assert output_conf.config.baudrate == 19200
        assert output_conf.config.timeout == 0.05
        assert output_conf.config.line_ending == "\r\n"

        # Test factory creation
        handler = None
        try:
            handler = OutputFactory.create_output_handler(output_conf)
            assert isinstance(handler, SerialOutput)
            assert handler.config.port == slave_name
            assert handler.config.baudrate == 19200

            # Quick start/stop test
            handler.start()
            assert handler.is_running
        finally:
            if handler:
                handler.stop()
            assert handler is None or not handler.is_running

    def test_serial_output_reconnection_logic_disabled(self, virtual_serial_ports):
        """Test that reconnection is not attempted if max_reconnect_attempts is 0."""
        invalid_port = "/dev/nonexistentport12345"
        config = SerialOutputConfig(port=invalid_port, baudrate=9600, max_reconnect_attempts=0, reconnect_delay=0.1)
        handler = SerialOutput(config)

        handler.start() # This should fail to connect
        assert not handler.is_running
        assert handler.serial_port is None

        # Give a very short time to see if a reconnect thread might have started (it shouldn't)
        time.sleep(0.3)
        assert handler._reconnect_thread is None or not handler._reconnect_thread.is_alive()
        handler.stop() # Should be a no-op or clean up event

    # More tests could be added:
    # - Reconnection logic when enabled (mocking serial.Serial to fail and then succeed)
    # - Different configurations (parity, stopbits, etc.) - harder to verify via pty without complex reader
    # - Error handling during send (e.g., port disappears) - complex to simulate reliably

# To run tests from CLI:
# Ensure pyserial and pytest are installed.
# In the project root:
# python -m pytest tests/test_serial_output.py
#
# Note on pty:
# The pty module creates a pseudo-terminal. The master end (master_fd) is what your test
# uses to simulate the other side of the serial communication (e.g., a device reading NMEA data).
# The slave end (identified by slave_name, e.g., /dev/pts/X) is what SerialOutput connects to.
# Reading from master_fd can sometimes be tricky regarding blocking/non-blocking I/O and timing.
# The current read in test_serial_output_send_sentence is basic and might need refinement
# for robustness, e.g., using select.select for checking readability before os.read.
#
# For Windows, these tests relying on `pty` will be skipped. A different fixture
# would be needed, potentially using a library like `com0com` (which requires prior setup)
# or by extensively mocking `serial.Serial`.

# Add a config for a test that expects failure to open port
@pytest.mark.skipif(not hasattr(pty, "openpty"), reason="pty module not available on this system")
def test_serial_output_start_failure_bad_port(capfd):
    """Test SerialOutput start failure with a clearly invalid port name (not just non-existent)."""
    # Using a port name that is syntactically invalid for pyserial on most systems,
    # or one that pty wouldn't create.
    # This test is more about pyserial raising an error that SerialOutput handles.
    config = SerialOutputConfig(port="INVALID_PORT_!@#$", baudrate=9600, max_reconnect_attempts=0)
    handler = SerialOutput(config)

    handler.start() # Should attempt to connect, fail, and not start reconnect thread

    assert not handler.is_running
    assert handler.serial_port is None

    # Check logs (optional, but good for diagnostics)
    # captured = capfd.readouterr()
    # assert "Failed to open serial port" in captured.out or "Error connecting to" in captured.out

    handler.stop() # Should be clean

    # Test with a port that might exist but we can't access (permission errors)
    # This is harder to reliably test without specific environment setup.
    # For now, focusing on non-existent and syntactically invalid.

```
