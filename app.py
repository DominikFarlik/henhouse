import serial


def write_id_to_file(id):
    pass


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
            data = ser.read(16)
            print(f"Raw data:{data}")
            data = str(data)
            data = data[8:-11]
            data = int(data, 16)
            if new_id == data:
                if counter > 50:
                    write_id_to_file(data)
                else:
                    counter += 1
            else:
                new_id = data
                counter = 1
            print(f"Id: {data} {counter}")

except KeyboardInterrupt:
    print("Port uzavren")

finally:
    ser.close()
