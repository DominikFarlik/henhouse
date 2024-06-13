import json
import logging
import os
import queue
import sqlite3
import threading

import serial  # type: ignore

json_file = "eggs.json"
LAY_TIME = 5  # Time to determine whether egg was laid

# Params for port
SER = serial.Serial(
    port="/dev/ttyUSB0",
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=5,
)

ID_QUEUE: queue.Queue = queue.Queue()


def write_event_to_db(chip_id, reader_id, event_type):
    connection = sqlite3.connect("henhouse.db")
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO events (chip_id, reader_id, event_type) VALUES (?, ?, ?)",
        (chip_id, reader_id, event_type),
    )

    connection.commit()
    connection.close()


# Saving laid egg to a file
def write_id_to_file(id_to_save: int) -> None:
    data_list = []

    # Checks if file exists
    if os.path.exists(json_file):
        with open(json_file, "r") as file:
            try:
                data_list = json.load(file)
            except json.JSONDecodeError:
                data_list = []

    # Check if id is already in file
    id_exists = False
    for item in data_list:
        if item["id"] == id_to_save:
            item["eggs"] += 1
            id_exists = True
            break

    # If id isn't already in file add
    if not id_exists:
        data_list.append({"id": id_to_save, "eggs": 1})

    # Writing to a file
    with open(json_file, "w") as file:
        json.dump(data_list, file, indent=4)


# Converting raw input to id
def convert_data_to_id(data_to_convert: bytes) -> int:
    converted_data = data_to_convert.decode("ascii")
    raw_id = converted_data[3:11]
    converted_id = int(raw_id, 16)
    return converted_id


# Thread for reading data
def data_reader():
    while True:
        if SER.in_waiting > 0:
            data = SER.read(16)
            ID_QUEUE.put(data)


# Thread for processing events
def event_processor():
    current_id = 0
    counter = 0
    colliding_id = 0
    colliding_counter = 0

    while True:
        try:
            # Connection to db
            connect = sqlite3.connect("henhouse.db")
            cursor = connect.cursor()

            # Loading data from queue
            reader_data = ID_QUEUE.get(timeout=1)
            new_id = convert_data_to_id(reader_data)

            # Counting same chicken ids for defined duration
            if new_id == current_id:
                if counter >= LAY_TIME:
                    write_id_to_file(current_id)
                    logging.info(f"Chicken {current_id} just laid an egg.")
                    counter = 0
                    write_event_to_db(current_id, "Kurnik01", "egg")
                    connect.commit()

                else:
                    counter += 1

            # Counting another chicken, if there's 2 nearby reader
            elif new_id == colliding_id:
                if colliding_counter >= LAY_TIME:
                    write_id_to_file(colliding_id)
                    logging.info(f"Chicken {colliding_id} just laid an egg.")
                    colliding_counter = 0
                else:
                    colliding_counter += 1

            else:
                # New ID encountered, swap current and colliding states
                colliding_id = current_id
                colliding_counter = counter
                current_id = new_id
                counter = 1

            logging.debug(f"ID: {current_id}, Counter: {counter}")
            if colliding_id:
                logging.debug(f"ID2: {colliding_id}, Counter: {colliding_counter}")

        except queue.Empty:
            continue


if __name__ == "__main__":
    # Logging config
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # , logging.FileHandler("egg_lay_log.log")
    )

    # cursor.execute("INSERT INTO events (chip_id, reader_id, event_type) VALUES (?, ?, ?)", (255, "Kurnik01", "egg"))

    try:
        # Splitting code to 2 threads for reading and processing data
        reader_thread = threading.Thread(target=data_reader, daemon=True)
        event_processor_thread = threading.Thread(target=event_processor, daemon=True)

        reader_thread.start()
        event_processor_thread.start()

        reader_thread.join()
        event_processor_thread.join()

    except KeyboardInterrupt:
        logging.info("Port closed")

    finally:
        SER.close()
