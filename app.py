import logging
import queue
import sqlite3
import threading
import serial  # type: ignore

# Constants
LAY_TIME = 5  # Time to determine whether egg was laid

# Serial port configuration
SER = serial.Serial(
    port="COM3",
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=5,
)

ID_QUEUE: queue.Queue[bytes] = queue.Queue()


class EggLayProcessor:
    def __init__(self):
        self.current_id = 0
        self.counter = 0
        self.colliding_id = 0
        self.colliding_counter = 0
        self.last_id = 0

    def process_new_id(self, new_id: int) -> None:
        """Process the new ID and update counters and states."""
        if new_id == self.current_id:
            self.counter += 1
            if self.counter >= LAY_TIME:
                logging.info(f"Chicken {self.current_id} laid an egg.")
                write_event_to_db(self.current_id, "Kurnik01", "egg")
                self.counter = 0

        elif new_id == self.colliding_id:
            self.colliding_counter += 1
            if self.colliding_counter >= LAY_TIME:
                logging.info(f"Chicken {self.colliding_id} laid an egg.")
                write_event_to_db(self.colliding_id, "Kurnik01", "egg")
                self.colliding_counter = 0

        elif self.current_id == 0:
            self.current_id = new_id
            self.counter += 1
            logging.info(f"Chicken {self.current_id} entered.")

        elif self.current_id != 0 and self.colliding_id == 0:
            self.colliding_id = new_id
            self.colliding_counter += 1
            logging.info(f"Chicken {self.colliding_id} entered.")

        else:
            if self.last_id == self.current_id:
                self.colliding_id, self.colliding_counter = new_id, 1
                logging.info(f"Chicken {self.colliding_id} left.")
            else:
                self.current_id, self.counter = new_id, 1
                logging.info(f"Chicken {self.current_id} left.")

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


def data_reader() -> None:
    """Thread for reading data from the serial port."""
    while True:
        if SER.in_waiting > 0:
            data = SER.read(16)
            ID_QUEUE.put(data)


def event_processor() -> None:
    """Thread for processing events."""
    processor = EggLayProcessor()

    while True:
        try:
            reader_data = ID_QUEUE.get(timeout=1)
            new_id = convert_data_to_id(reader_data)

            processor.process_new_id(new_id)

        except queue.Empty:
            continue
        except Exception as e:
            logging.error(f"Unexpected error in event processor: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # , logging.FileHandler("egg_lay_log.log")
    )

    try:
        reader_thread = threading.Thread(target=data_reader, daemon=True)
        event_processor_thread = threading.Thread(target=event_processor, daemon=True)

        reader_thread.start()
        event_processor_thread.start()

        reader_thread.join()
        event_processor_thread.join()

    except KeyboardInterrupt:
        logging.info("Shutting down...")

    finally:
        if SER.is_open:
            SER.close()
        logging.info("Serial port closed")
