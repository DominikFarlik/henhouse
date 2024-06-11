import serial
import json
import os

json_file = 'eggs.json'
egg_lay_time = 50


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


# Parametry pro serial
ser = serial.Serial(
    port='COM3',
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=5
)

new_id = 0
counter = 0

try:
    while True:
        if ser.in_waiting > 0:

            # data z ctecky
            data = ser.read(16)
            id = convert_data_to_id(data)

            if new_id == id:
                if counter >= egg_lay_time:
                    write_id_to_file(id)
                    print(f"Slepice {id} prave snesla vejce.")
                    counter = 0
                else:
                    counter += 1
            else:
                new_id = id
                counter = 1
            print(f"Id: {id} {counter}")

except KeyboardInterrupt:
    print("Port uzavren")

finally:
    ser.close()
