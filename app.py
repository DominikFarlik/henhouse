import logging
import queue
import sqlite3
import threading
import serial
import serial.tools.list_ports

# Constants
LAY_TIME = 5  # Time to determine whether egg was laid

# Global variables
ID_QUEUE: queue.Queue[tuple[bytes, str]] = queue.Queue()

class EggLayProcessor:
    def __init__(self):
        self.current_id = 0
        self.counter = 0
        self.colliding_id = 0
        self.colliding_counter = 0
        self.last_id = 0

    def process_new_id(self, new_id: int, reader_id: str) -> None:
        """Process the new ID and update counters and states."""
        if new_id == self.current_id:
            self.counter += 1
            if self.counter >= LAY_TIME:
                logging.info(f"Chicken {self.current_id} laid an egg on {reader_id}.")
                write_event_to_db(self.current_id, reader_id, "egg")
                self.counter = 0

        elif new_id == self.colliding_id:
            self.colliding_counter += 1
            if self.colliding_counter >= LAY_TIME:
                logging.info(f"Chicken {self.colliding_id} laid an egg on {reader_id}.")
                write_event_to_db(self.colliding_id, reader_id, "egg")
                self.colliding_counter = 0

        elif self.current_id == 0:
            self.current_id = new_id
            self.counter += 1
            logging.info(f"Chicken {self.current_id} entered on {reader_id}.")

        elif self.current_id != 0 and self.colliding_id == 0:
            self.colliding_id = new_id
            self.colliding_counter += 1
            logging.info(f"Chicken {self.colliding_id} entered on {reader_id}.")

        else:
            if self.last_id == self.current_id:
                self.colliding_id, self.colliding_counter = new_id, 1
                logging.info(f"Chicken {self.colliding_id} left on {reader_id}.")
            else:
                self.current_id, self.counter = new_id, 1
                logging.info(f"Chicken {self.current_id} left on {reader_id}.")

        self.last_id = new_id

        if self.current_id == new_id:
            logging.debug(f"ID: {self.current_id}, Counter: {self.counter}")
        elif self.colliding_id == new_id:
            logging.debug(f"ID2: {self.colliding_id}, Counter: {self.colliding_counter}")


def write_event_to_db(chip_id: int, reader_id: str, event_type: str) -> None:
    """Writes received data to the database."""
    try:
        with sqlite3.connect("henhouse.db") as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO events (chip_id, reader_id, event_type) VALUES (?, ?, ?)",
                (chip_id, reader_id, event_type),
            )
            connection.commit()
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
        return converted_id
    except (ValueError, IndexError) as e:
        logging.error(f"Error converting data to ID: {e}")
        return -1


class SerialPortReader:
    def __init__(self, port_name: str):
        self.serial_port = serial.Serial(
            port=port_name,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=5,
        )
        self.reader_id = f"Reader_{port_name}"
        self.thread = threading.Thread(target=self.data_reader, daemon=True)

    def start(self):
        self.thread.start()

    def data_reader(self) -> None:
        """Thread for reading data from the serial port."""
        while True:
            if self.serial_port.in_waiting > 0:
                data = self.serial_port.read(16)
                ID_QUEUE.put((data, self.reader_id))

    def close(self):
        if self.serial_port.is_open:
            self.serial_port.close()


def event_processor() -> None:
    """Thread for processing events."""
    processor = EggLayProcessor()

    while True:
        try:
            reader_data, reader_id = ID_QUEUE.get(timeout=1)
            new_id = convert_data_to_id(reader_data)

            processor.process_new_id(new_id, reader_id)

        except queue.Empty:
            continue
        except Exception as e:
            logging.error(f"Unexpected error in event processor: {e}")


def find_serial_ports() -> list:
    """Finds all available serial ports."""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # , logging.FileHandler("egg_lay_log.log")
    )

    # Automatically detect available serial ports
    serial_port_names = find_serial_ports()
    logging.info(f"Detected serial ports: {serial_port_names}")

    # Create SerialPortReader instances
    serial_port_readers = [SerialPortReader(port_name) for port_name in serial_port_names]

    try:
        # Start all reader threads
        for reader in serial_port_readers:
            reader.start()

        # Start the event processor thread
        event_processor_thread = threading.Thread(target=event_processor, daemon=True)
        event_processor_thread.start()

        # Join all reader threads
        for reader in serial_port_readers:
            reader.thread.join()
        event_processor_thread.join()

    except KeyboardInterrupt:
        logging.info("Shutting down...")

    finally:
        for reader in serial_port_readers:
            reader.close()
        logging.info("Serial ports closed")
