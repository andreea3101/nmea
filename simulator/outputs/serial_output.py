"""Serial output handler for NMEA sentences."""

from dataclasses import dataclass, field
from typing import Optional # Added Optional
import serial

@dataclass
class SerialPortSettings:
    """Settings for the serial port."""
    port: str = "/dev/ttyS0"
    baudrate: int = 9600
    bytesize: int = serial.EIGHTBITS
    parity: str = serial.PARITY_NONE
    stopbits: float = serial.STOPBITS_ONE
    timeout: Optional[float] = 1.0
    write_timeout: Optional[float] = 1.0
    rtscts: bool = False
    dsrdtr: bool = False
    xonxoff: bool = False
    exclusive: bool = True


@dataclass
class SerialConnectionSettings:
    """Settings for the serial connection."""
    send_interval: float = 0.1
    reconnect_delay: float = 5.0
    max_reconnect_attempts: int = 5
    line_ending: str = "\r\n"


@dataclass
class SerialOutputConfig:
    """Configuration for Serial output."""
    port_settings: SerialPortSettings
    connection_settings: SerialConnectionSettings

    def __post_init__(self):
        # Validate common settings
        if not self.port_settings.port:
            raise ValueError("Serial port must be specified.")
        if self.port_settings.baudrate <= 0:
            raise ValueError("Baudrate must be a positive integer.")
        if self.port_settings.timeout is not None and self.port_settings.timeout < 0:
            raise ValueError("Timeout cannot be negative.")
        if self.port_settings.write_timeout is not None and self.port_settings.write_timeout < 0:
            raise ValueError("Write timeout cannot be negative.")

        # Convert string representations of serial settings to their pyserial equivalents
        if isinstance(self.port_settings.bytesize, str):
            self.port_settings.bytesize = getattr(serial, self.port_settings.bytesize.upper(), serial.EIGHTBITS)
        if isinstance(self.port_settings.parity, str):
            self.port_settings.parity = getattr(serial, f"PARITY_{self.port_settings.parity.upper()}",
                                                serial.PARITY_NONE)
        if isinstance(self.port_settings.stopbits, str):
            self.port_settings.stopbits = getattr(serial,
                                                  f"STOPBITS_{self.port_settings.stopbits.upper().replace('.', '_')}",
                                                  serial.STOPBITS_ONE)

        # Line ending validation
        if not isinstance(self.connection_settings.line_ending, str):
            raise ValueError("Line ending must be a string (e.g., '\\r\\n', '\\n').")
        try:
            self.connection_settings.line_ending.encode('ascii')  # Check if it's valid ASCII
        except UnicodeEncodeError:
            raise ValueError("Line ending contains non-ASCII characters.")

    def get_serial_options(self) -> dict:
        """Returns a dictionary of options suitable for pyserial.Serial constructor."""
        return asdict(self.port_settings)

from .base import OutputHandler
import time # For reconnect delays and send intervals
import threading # For reconnection logic

class SerialOutput(OutputHandler):
    """Serial port output handler for NMEA sentences."""

    def __init__(self, config: SerialOutputConfig):
        """Initialize Serial output handler."""
        super().__init__()
        self.config = config
        self.serial_port: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._reconnect_thread: Optional[threading.Thread] = None
        self._last_send_time: float = 0.0

    def start(self) -> None:
        """Start the serial output handler."""
        if self.is_running:
            return

        self._stop_event.clear()
        print(f"Attempting to start serial output on {self.config.port} at {self.config.baudrate} baud.")
        try:
            self._connect()
            self.is_running = True
            self.start_time = time.time() # Record start time
            print(f"Serial output started on {self.config.port}")
        except serial.SerialException as e:
            self.is_running = False
            print(f"Failed to open serial port {self.config.port}: {e}")
            # Optionally, start reconnection attempts if configured
            if self.config.max_reconnect_attempts != 0:
                 self._start_reconnect_thread()
            # raise RuntimeError(f"Failed to start serial output: {e}") # Or handle more gracefully

    def _connect(self) -> None:
        """Establish serial connection."""
        if self.serial_port and self.serial_port.is_open:
            return # Already connected

        try:
            self.serial_port = serial.Serial(**self.config.get_serial_options())
            # Ensure DTR/RTS are set if not using hardware flow control, some devices need them.
            if not self.config.rtscts:
                 self.serial_port.dtr = True
                 self.serial_port.rts = True
            print(f"Successfully connected to serial port {self.config.port}.")
        except serial.SerialException as e:
            print(f"Error connecting to {self.config.port}: {e}")
            if self.serial_port:
                self.serial_port.close()
            self.serial_port = None
            raise # Re-raise to be caught by start() or _reconnect_loop()

    def stop(self) -> None:
        """Stop the serial output handler."""
        if not self.is_running and not (self._reconnect_thread and self._reconnect_thread.is_alive()):
            return

        print(f"Stopping serial output on {self.config.port}...")
        self._stop_event.set()

        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=self.config.reconnect_delay + 1)
            self._reconnect_thread = None

        with self._lock:
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.close()
                    print(f"Serial port {self.config.port} closed.")
                except Exception as e:
                    print(f"Error closing serial port {self.config.port}: {e}")
            self.serial_port = None

        self.is_running = False
        print("Serial output stopped.")

    def send_sentence(self, sentence: str) -> bool:
        """Send NMEA sentence to the serial port."""
        if not self.is_running or not self.serial_port or not self.serial_port.is_open:
            # If not running but trying to send, it could be due to a connection issue.
            # Reconnection logic will handle this if enabled.
            if not self.is_running and self.config.max_reconnect_attempts != 0 and not (self._reconnect_thread and self._reconnect_thread.is_alive()):
                print("Serial port not connected. Attempting to reconnect...")
                self._start_reconnect_thread() # Try to bring it back up
            return False

        with self._lock:
            if not self.serial_port or not self.serial_port.is_open:
                return False # Should be caught by the check above, but as a safeguard

            # Enforce minimum send interval
            current_time = time.time()
            if current_time - self._last_send_time < self.config.send_interval:
                time.sleep(self.config.send_interval - (current_time - self._last_send_time))

            try:
                # Strip sentence then append configured line ending
                full_sentence = sentence.strip() + self.config.line_ending
                self.serial_port.write(full_sentence.encode('utf-8'))
                self.serial_port.flush() # Ensure data is sent
                self.sentences_sent += 1
                self.last_sentence_time = time.time() # Record time of last successful send
                self._last_send_time = time.time()
                return True
            except serial.SerialTimeoutException as e:
                print(f"Serial write timeout on {self.config.port}: {e}")
                self._handle_send_error()
                return False
            except serial.SerialException as e:
                print(f"Serial error on {self.config.port} during send: {e}")
                self._handle_send_error()
                return False
            except Exception as e:
                print(f"Unexpected error sending data on {self.config.port}: {e}")
                self._handle_send_error()
                return False

    def _handle_send_error(self):
        """Handles errors during sending, potentially triggering reconnection."""
        self.is_running = False # Mark as not running to stop further sends until reconnected
        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception:
                pass # Ignore errors during close if already in error state
        self.serial_port = None

        if not self._stop_event.is_set() and self.config.max_reconnect_attempts != 0:
            print("Connection lost. Attempting to reconnect...")
            self._start_reconnect_thread()

    def _start_reconnect_thread(self):
        """Starts the reconnection thread if not already running."""
        with self._lock: # Protect access to _reconnect_thread
            if not self._reconnect_thread or not self._reconnect_thread.is_alive():
                self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
                self._reconnect_thread.start()
                print("Reconnection thread started.")

    def _reconnect_loop(self) -> None:
        """Periodically attempts to reconnect to the serial port."""
        attempts = 0
        max_attempts = self.config.max_reconnect_attempts

        while not self._stop_event.is_set() and \
              (max_attempts == -1 or attempts < max_attempts):

            if self.is_running: # Should not happen if called from error, but good check
                break

            attempts += 1
            print(f"Reconnection attempt {attempts}/{max_attempts if max_attempts != -1 else 'infinite'} for {self.config.port}...")

            try:
                with self._lock: # Ensure exclusive access for connection attempt
                    self._connect() # Try to connect
                    self.is_running = True # If connect succeeds
                    self.start_time = time.time()
                    print(f"Successfully reconnected to {self.config.port}.")
                # If successful, break the loop
                break
            except serial.SerialException as e:
                print(f"Reconnect attempt {attempts} failed: {e}")
                # Wait for the configured delay or until stop_event is set
                self._stop_event.wait(self.config.reconnect_delay)
            except Exception as e: # Catch any other unexpected errors during connect
                print(f"Unexpected error during reconnect attempt {attempts}: {e}")
                self._stop_event.wait(self.config.reconnect_delay)

        if not self.is_running and not self._stop_event.is_set():
            print(f"Failed to reconnect to {self.config.port} after {attempts} attempts. Stopping reconnection attempts.")
        elif self._stop_event.is_set():
             print("Reconnection attempts stopped by stop event.")

        # Clean up the thread reference once done, if it was this thread
        with self._lock:
            if self._reconnect_thread == threading.current_thread():
                 self._reconnect_thread = None
                 print("Reconnection thread finished.")


    def get_status(self) -> dict:
        """Get serial output status."""
        status = super().get_status()
        with self._lock:
            status.update({
                'port': self.config.port,
                'baudrate': self.config.baudrate,
                'is_open': self.serial_port.is_open if self.serial_port else False,
                'reconnecting': self._reconnect_thread.is_alive() if self._reconnect_thread else False,
            })
        return status

    def __str__(self) -> str:
        """String representation."""
        state = "RUNNING" if self.is_running else "STOPPED"
        if not self.is_running and self._reconnect_thread and self._reconnect_thread.is_alive():
            state = "RECONNECTING"
        details = f"{self.config.port}@{self.config.baudrate}bps"
        return f"SerialOutput({state}, {details}, {self.sentences_sent} sentences)"

    def __del__(self):
        """Ensure resources are released."""
        self.stop()
