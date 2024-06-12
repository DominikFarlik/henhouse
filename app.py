import serial  # type: ignore
import json
import os
import logging

json_file = 'eggs.json'
egg_lay_time = 50

# Params for port
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=5
)


# Saving laid egg to a file
def write_id_to_file(id_to_save: int) -> None:
    data_list = []

    # Checks if file exists
    if os.path.exists(json_file):
        with open(json_file, 'r') as file:
            try:
                data_list = json.load(file)
            except json.JSONDecodeError:
                data_list = []

    # Check if id is already in file
    id_exists = False
    for item in data_list:
        if item['id'] == id_to_save:
            item['eggs'] += 1
            id_exists = True
            break

    # If id isn't already in file add
    if not id_exists:
        data_list.append({'id': id_to_save, 'eggs': 1})

    # Writing to a file
    with open(json_file, 'w') as file:
        json.dump(data_list, file, indent=4)


# Converting raw input to id
def convert_data_to_id(data_to_convert: bytes) -> int:
    converted_data = data_to_convert.decode('ascii')
    raw_id = converted_data[3:11]
    converted_id = int(raw_id, 16)
    return converted_id


if __name__ == "__main__":
    # Logging config
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler('egg_lay_log.log')])

    last_id = 0
    current_id = 0
    counter = 0
    colliding_id = 0
    colliding_counter = 0

    try:
        while True:
            if ser.in_waiting > 0:
                data = ser.read(16)
                new_id = convert_data_to_id(data)

                # Counting same chicken ids for specific duration
                if new_id == current_id:
                    if counter >= egg_lay_time:
                        write_id_to_file(current_id)
                        logging.info(f"Chicken {current_id} just laid an egg.")
                        counter = 0
                    else:
                        counter += 1

                # Counting another chicken, if there's 2 nearby
                elif new_id == colliding_id:
                    if colliding_counter >= egg_lay_time:
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

    except KeyboardInterrupt:
        logging.info("Port closed")

    finally:
        ser.close()
