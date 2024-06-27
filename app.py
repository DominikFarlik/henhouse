import logging
import queue
import sqlite3
import threading
from datetime import datetime
from dataclasses import dataclass
import requests
from requests.auth import HTTPBasicAuth
import configparser

import serial  # type: ignore
import serial.tools.list_ports  # type: ignore


@dataclass
class Chicken:
    chip_id: int
    reader_id: str
    counter: int
    enter_time: datetime
    last_read: datetime


class APIClient:
    def __init__(self, username: str, password: str, time_zone_offset: int):
        self.username = username
        self.password = password
        self.time_zone_offset = time_zone_offset
        self.record_id = self.get_starting_id_for_api()

    def get_starting_id_for_api(self) -> int:
        try:
            response = requests.get('https://itaserver-staging.mobatime.cloud/api/TimeAttendanceRecordId',
                                    auth=HTTPBasicAuth(self.username, self.password))
            response.raise_for_status()  # Ensure we raise an error for bad responses
            data = response.json()
            logging.info(f"Retrieved starting record ID: {data['LastTimeAttendanceRecordId'] + 1}")
            return data['LastTimeAttendanceRecordId'] + 1
        except requests.RequestException as e:
            logging.error(f"Failed to get starting ID from API: {e}")
            raise

    def create_api_record(self, time: str, rfid: int, record_type: int, reader_id: str) -> None:
        params = {
            "TerminalTime": time,
            "TerminalTimeZone": self.time_zone_offset,
            "IsImmediate": False,
            "TimeAttendanceRecords": [
                {
                    "RecordId": self.record_id,
                    "RecordType": record_type,
                    "RFID": rfid,
                    "Punched": datetime.now().isoformat(),
                    "HWSource": reader_id[-1]
                }
            ]
        }

        try:
            response = requests.post('https://itaserver-staging.mobatime.cloud/api/TimeAttendance',
                                     json=params,
                                     auth=HTTPBasicAuth(self.username, self.password))
            response.raise_for_status()  # Ensure we raise an error for bad responses
            logging.info(f"Successfully created API record with ID: {self.record_id}")
            self.record_id += 1  # Increment the record ID after a successful post
        except requests.RequestException as e:
            logging.error(f"Failed to create API record: {e}")
            raise


class EventProcessor:
    def __init__(self, event_queue: queue.Queue, api_client: APIClient):
        self.chickens: list[Chicken] = []
        self.event_queue = event_queue
        self.api_client = api_client
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        """Thread function to process events from the queue."""
        while self.running:
            try:
                reader_data, reader_id = self.event_queue.get(timeout=1)
                new_id = convert_data_to_id(reader_data)

                if new_id != -1:
                    self.process_new_chip_id(new_id, reader_id)
                    self.check_if_left()

            except queue.Empty:
                continue

            except Exception as e:
                logging.error(f"Unexpected error in event processor: {e}")

    def process_new_chip_id(self, new_id: int, reader_id: str) -> None:
        """Process the new ID and update counters and states."""
        found_chicken = self.check_for_egg(new_id, reader_id)
        if not found_chicken:
            chicken = Chicken(new_id, reader_id, 1, datetime.now(), datetime.now())
            self.chickens.append(chicken)
            logging.info(f"Chicken {chicken.chip_id} entered on {chicken.reader_id}.")
            write_event_to_db(
                new_id,
                reader_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "enter",
            )

            self.api_client.create_api_record(
                datetime.now().isoformat(),
                chicken.chip_id,
                0,
                chicken.reader_id
            )

    def check_for_egg(self, new_id, reader_id: str) -> bool:
        """Checking if chicken is constantly standing long enough on reader"""
        for chicken in self.chickens:
            if chicken.chip_id == new_id:
                chicken.counter += 1
                chicken.last_read = datetime.now()
                elapsed_time = datetime.now() - chicken.enter_time
                if chicken.counter >= LAY_COUNTER and elapsed_time.total_seconds() >= LAY_TIME:
                    write_event_to_db(
                        chicken.chip_id,
                        chicken.reader_id,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "egg",
                    )

                    self.api_client.create_api_record(
                        datetime.now().isoformat(),
                        chicken.chip_id,
                        9000,
                        chicken.reader_id
                    )
                    chicken.counter = 0
                    logging.info(f"Chicken {chicken.chip_id} laid an egg on {reader_id}.")
                    return True
                else:
                    return True

        return False

    def check_if_left(self) -> None:
        """Checking if chicken left the reader"""
        for chicken in self.chickens:
            if (datetime.now() - chicken.last_read).total_seconds() >= LEAVE_TIME:
                logging.info(
                    f"Chicken {chicken.chip_id} left {chicken.reader_id} "
                    f"{chicken.last_read.strftime('%Y-%m-%d %H:%M:%S')}."
                )

                write_event_to_db(
                    chicken.chip_id,
                    chicken.reader_id,
                    chicken.last_read.strftime("%Y-%m-%d %H:%M:%S"),
                    "left",
                )

                self.api_client.create_api_record(
                    chicken.last_read.isoformat(),
                    chicken.chip_id,
                    1,
                    chicken.reader_id
                )
                self.chickens.pop(self.chickens.index(chicken))

    def stop(self):
        self.running = False


def write_event_to_db(
        chip_id: int, reader_id: str, event_time: str, event_type: str
) -> None:
    """Writes received data to the database."""
    lock = threading.Lock()
    with lock:
        try:
            with sqlite3.connect(DB_PATH) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO events (chip_id, reader_id, event_type, event_time) VALUES (?, ?, ?, ?)",
                    (chip_id, reader_id, event_type, event_time),
                )
                connection.commit()
                #  logging.info(f"Event written to DB: {chip_id}, {reader_id}, {event_type}, {event_time}")
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")


def convert_data_to_id(data_to_convert: bytes) -> int:
    """Converts raw input data to an ID."""
    try:
        converted_data = data_to_convert.decode("ascii")
        raw_id = converted_data[3:11]
        converted_id = int(raw_id, 16)
        #  logging.debug(f"Converted data to ID: {converted_id}")
        return converted_id
    except (ValueError, IndexError) as e:
        logging.error(f"Error converting data to ID: {e}")
        return -1


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
        self.reader_id = f"Reader_{port_name}"
        self.event_queue = event_queue
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
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

    def close(self):
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


def read_config(filename='config.ini'):
    """Reads the configuration"""
    config = configparser.ConfigParser()
    config.read(filename)
    return config


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

    LAY_COUNTER = config.getint('Constants', 'lay_counter')
    LAY_TIME = config.getint('Constants', 'lay_time')
    LEAVE_TIME = config.getint('Constants', 'leave_time')

    DB_PATH = config.get('Database', 'file_path')

    # Automatically detect available serial ports
    serial_port_names = find_serial_ports()
    logging.info(f"Detected serial ports: {serial_port_names}")

    event_queue = queue.Queue()

    api_client = APIClient(api_username, api_password, api_timezone_offset)
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
