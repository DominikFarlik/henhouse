from datetime import datetime
import logging
import queue
import sqlite3
import threading
import serial
import serial.tools.list_ports

# Constants
LAY_COUNTER = 5  # Number of chip reads
LAY_TIME = 10  # Duration to determine whether egg was laid
LEAVE_TIME = 10  # Duration to determine whether chicken left

# Global variables
ID_QUEUE: queue.Queue[tuple[bytes, str]] = queue.Queue()


class EggLayProcessor:
    def __init__(self):
        self.chickens = []

    # Takes id from reader and checks its state
    def process_new_chip_id(self, new_id: int, reader_id: str) -> None:
        """Process the new ID and update counters and states."""
        found_chicken = self.check_for_egg(new_id, reader_id)
        # Appends new chicken to be processed
        if not found_chicken:
            new_chicken = {"chip_id": new_id, "enter_time": datetime.now(),
                           "reader_id": reader_id, "counter": 1, "last_read": datetime.now()}
            self.chickens.append(new_chicken)
            logging.info(f"{new_chicken["enter_time"]} - Chicken {new_id} entered on {reader_id}.")

    # Checking if chicken is constantly standing long enough on reader
    def check_for_egg(self, new_id, reader_id: str) -> bool:
        for chicken in self.chickens:
            if chicken["chip_id"] == new_id:
                chicken["counter"] += 1
                chicken["last_read"] = datetime.now()
                elapsed_time = datetime.now() - chicken["enter_time"]
                if chicken["counter"] >= LAY_COUNTER and elapsed_time.total_seconds() >= LAY_TIME:
                    write_event_to_db(chicken["chip_id"], chicken["reader_id"],
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "egg")
                    chicken["counter"] = 0
                    logging.info(f"Chicken {chicken["chip_id"]} laid an egg on {reader_id}.")
                    return True
                else:
                    return True

        return False

    def check_if_left(self) -> None:
        print("here")
        for chicken in self.chickens:
            print((datetime.now() - chicken["last_read"]).total_seconds())
            if (datetime.now() - chicken["last_read"]).total_seconds() >= LEAVE_TIME:
                logging.info(f"Chicken {chicken["chip_id"]} left {chicken["reader_id"]}.")
                write_event_to_db(chicken["chip_id"], chicken["reader_id"], 
                                  chicken["last_read"].strftime("%Y-%m-%d %H:%M:%S"), "left")
                self.chickens.pop(self.chickens.index(chicken))


def write_event_to_db(chip_id: int, reader_id: str, event_time: str, event_type: str) -> None:
    """Writes received data to the database with the current timestamp."""
    try:
        with sqlite3.connect("henhouse.db") as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO events (chip_id, reader_id, event_type, event_time) VALUES (?, ?, ?, ?)",
                (chip_id, reader_id, event_type, event_time),
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
    # Instance for processor class
    processor = EggLayProcessor()

    while True:
        try:
            reader_data, reader_id = ID_QUEUE.get(timeout=1)
            new_id = convert_data_to_id(reader_data)

            processor.process_new_chip_id(new_id, reader_id)
            processor.check_if_left()

        except queue.Empty:
            continue
        except Exception as e:
            logging.error(f"Unexpected error in event processor: {e}")


def find_serial_ports() -> list:
    """Finds all available serial ports."""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


if __name__ == "__main__":
    # Logging configuration
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
