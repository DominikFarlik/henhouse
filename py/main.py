import logging
import queue

from event_processor import EventProcessor
from api_client import APIClient
from serial_reader import SerialPortReader, find_serial_ports
from config import read_config

if __name__ == "__main__":
    # Logging configuration
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # , logging.FileHandler("egg_lay_log.log")
    )

    # Read configuration from INI file
    config = read_config()

    api_username = config.get('API', 'username')
    api_password = config.get('API', 'password')
    api_timezone_offset = config.getint('API', 'timezone_offset')

    api_client = APIClient(api_username, api_password, api_timezone_offset)

    # Automatically detect available serial ports
    serial_port_names = find_serial_ports()

    event_queue = queue.Queue()

    event_processor = EventProcessor(event_queue, api_client)

    # Create SerialPortReader instances
    serial_port_readers = [
        SerialPortReader(port_name, event_queue)
        for port_name in serial_port_names
    ]

    try:
        # Start the EventProcessor thread
        event_processor.start()

        # Start all reader threads
        for reader in serial_port_readers:
            reader.start()

        # Join all reader threads
        for reader in serial_port_readers:
            reader.thread.join()

        # Join the processor thread
        event_processor.thread.join()

    except KeyboardInterrupt:
        logging.info("Shutting down...")

    finally:
        for reader in serial_port_readers:
            reader.close()
        event_processor.stop()
        logging.info("Serial ports closed")
