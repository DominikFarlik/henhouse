import queue
import threading
import datetime
from dataclasses import dataclass
import logging
from .config import read_config
from .save_operations import save_record

config = read_config()

LAY_COUNTER = config.getint('Constants', 'lay_counter')
LAY_TIME = config.getint('Constants', 'lay_time')
LEAVE_TIME = config.getint('Constants', 'leave_time')


@dataclass
class Chicken:
    chip_id: int
    reader_id: int
    counter: int
    enter_time: datetime.datetime
    last_read: datetime.datetime


class EventProcessor:
    def __init__(self, event_queue: queue.Queue):
        self.chickens: list[Chicken] = []
        self.event_queue = event_queue
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

    def process_new_chip_id(self, new_id: int, reader_id: int) -> None:
        """Process the new ID and update counters and states."""
        found_chicken = self.check_for_egg(new_id, reader_id)
        if not found_chicken:
            chicken = Chicken(new_id, reader_id, 1, datetime.datetime.now(), datetime.datetime.now())
            self.chickens.append(chicken)
            logging.info(f"Chicken {chicken.chip_id} entered on {chicken.reader_id}.")
            save_record(chicken.chip_id, chicken.reader_id, datetime.datetime.now().isoformat(), 0)

    def check_for_egg(self, new_id, reader_id: int) -> bool:
        """Checking if chicken is constantly standing long enough on reader"""
        for chicken in self.chickens:
            if chicken.chip_id == new_id:
                chicken.counter += 1
                chicken.last_read = datetime.datetime.now()
                elapsed_time = datetime.datetime.now() - chicken.enter_time
                if chicken.counter >= LAY_COUNTER and elapsed_time.total_seconds() >= LAY_TIME:
                    save_record(chicken.chip_id, chicken.reader_id, datetime.datetime.now().isoformat(), 9000)
                    chicken.counter = 0
                    logging.info(f"Chicken {chicken.chip_id} laid an egg on {reader_id}.")
                    return True
                else:
                    return True

        return False

    def check_if_left(self) -> None:
        """Checking if chicken left the reader"""
        for chicken in self.chickens:
            if (datetime.datetime.now() - chicken.last_read).total_seconds() >= LEAVE_TIME:
                logging.info(
                    f"Chicken {chicken.chip_id} left {chicken.reader_id} "
                    f"{chicken.last_read.strftime('%Y-%m-%d %H:%M:%S')}."
                )
                save_record(chicken.chip_id, chicken.reader_id, chicken.last_read.isoformat(), 1)

                self.chickens.pop(self.chickens.index(chicken))

    def stop(self):
        self.running = False


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
