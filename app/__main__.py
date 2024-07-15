import logging
import queue
import threading
import click
import configparser
import requests  # type: ignore

from .config import set_config_path
from .event_processor import EventProcessor
from .serial_reader import SerialPortReader, find_serial_ports
from .save_operations import resend_failed_records, compare_api_db_id, database_initialization, con, \
    get_number_of_unsent_records


def main() -> None:
    # Logging configuration
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # , logging.FileHandler("egg_lay_log.log")
    )

    # Automatically detect available serial ports
    serial_port_names = find_serial_ports()

    event_queue: queue.Queue = queue.Queue()

    event_processor = EventProcessor(event_queue)

    # Create SerialPortReader instances
    serial_port_readers = [
        SerialPortReader(port_name, event_queue)
        for port_name in serial_port_names
    ]

    stop_event = threading.Event()
    api_resend_thread = threading.Thread(target=resend_failed_records, args=(stop_event,))

    # if database is not in project, is added
    database_initialization()

    # checking if ids from db and api are matching
    compare_api_db_id()

    try:
        # Start the EventProcessor thread
        event_processor.start()

        api_resend_thread.start()

        # Start all reader threads
        for reader in serial_port_readers:
            reader.start()

        # Join all reader threads
        for reader in serial_port_readers:
            reader.thread.join()

        # Join the processor thread
        event_processor.thread.join()

        api_resend_thread.join()

    except KeyboardInterrupt:
        logging.info("Shutting down...")

    finally:
        stop_event.set()
        for reader in serial_port_readers:
            reader.close()
        event_processor.stop()
        con.close()
        logging.info("Serial ports closed")
