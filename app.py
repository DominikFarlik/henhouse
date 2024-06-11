import serial
import json
import os

json_file = 'eggs.json'
egg_lay_time = 50

# Parametry pro serial
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=5
)


# Ulozeni sneseneho vejce do souboru
def write_id_to_file(new_id):
    data_list = []

    # Kontrola, zda soubor existuje
    if os.path.exists(json_file):
        with open(json_file, 'r') as file:
            try:
                data_list = json.load(file)
            except json.JSONDecodeError:
                data_list = []

    # Kontrola, zda je id v souboru
    id_exists = False
    for item in data_list:
        if item['id'] == new_id:
            item['eggs'] += 1
            id_exists = True
            break

    # Pokud id v souboru neni, je pridano
    if not id_exists:
        data_list.append({'id': new_id, 'eggs': 1})

    # Zapis do souboru
    with open(json_file, 'w') as file:
        json.dump(data_list, file, indent=4)


# Prevod dat z ctecky na id
def convert_data_to_id(data):
    print(f"Raw data:{data}")
    data = str(data)
    data = data[8:-11]
    converted_id = int(data, 16)
    return converted_id


if __name__ == "__main__":
    last_id = None
    current_id = None
    counter = 0
    colliding_id = None
    colliding_counter = 0

    try:
        while True:
            if ser.in_waiting > 0:
                data = ser.read(16)
                new_id = convert_data_to_id(data)

                if new_id == current_id:
                    if counter >= egg_lay_time:
                        write_id_to_file(current_id)
                        print(f"Slepice {current_id} prave snesla vejce.")
                        counter = 0
                    else:
                        counter += 1
                elif new_id == colliding_id:
                    if colliding_counter >= egg_lay_time:
                        write_id_to_file(colliding_id)
                        print(f"Slepice {colliding_id} prave snesla vejce.")
                        colliding_counter = 0
                    else:
                        colliding_counter += 1
                else:
                    # New ID encountered, swap current and colliding states
                    colliding_id = current_id
                    colliding_counter = counter
                    current_id = new_id
                    counter = 1

                print(f"Current ID: {current_id}, Counter: {counter}")
                if colliding_id:
                    print(f"Colliding ID: {colliding_id}, Counter: {colliding_counter}")

    except KeyboardInterrupt:
        print("Port uzavren")

    finally:
        ser.close()
