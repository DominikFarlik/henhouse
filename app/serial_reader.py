import logging
import queue
import threading
import serial  # type: ignore
import serial.tools.list_ports  # type: ignore
from .config import read_config

config = read_config()


class SerialPortReader:
    def __init__(self, port_name: str, event_queue: queue.Queue):
        self.serial_port = serial.Serial(
            port=port_name,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=5,
        )
        self.reader_id: int = config.getint('Readers', port_name)
        self.event_queue = event_queue
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def run(self) -> None:
        """Thread for reading data from the serial port."""
        while self.running:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(16)
                    #  logging.debug(f"Data read from {self.reader_id}: {data}")
                    self.event_queue.put((data, self.reader_id))

            except serial.SerialException as e:
                logging.error(f"Serial exception on {self.reader_id}: {e}")
                break

            except Exception as e:
                logging.error(f"Unexpected exception on {self.reader_id}: {e}")
                break

    def close(self) -> None:
        self.running = False
        if self.serial_port.is_open:
            self.serial_port.close()
            logging.info(f"Serial port {self.reader_id} closed")


def find_serial_ports() -> list:
    """Finds all available serial ports."""
    ports = serial.tools.list_ports.comports()
    port_list = [port.device for port in ports]
    logging.info(f"Available serial ports: {port_list}")
    return port_list
