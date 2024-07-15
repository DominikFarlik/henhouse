import logging
import queue
import threading
import click
import configparser
import requests  # type: ignore

from .event_processor import EventProcessor
from .serial_reader import SerialPortReader, find_serial_ports

from .save_operations import resend_failed_records, compare_api_db_id, database_initialization, con, \
    get_number_of_unsent_records


def main() -> None:
    # Logging configuration
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # , logging.FileHandler("egg_lay_log.log")
    )

    # Automatically detect available serial ports
    serial_port_names = find_serial_ports()

    event_queue: queue.Queue = queue.Queue()

    event_processor = EventProcessor(event_queue)

    # Create SerialPortReader instances
    serial_port_readers = [
        SerialPortReader(port_name, event_queue)
        for port_name in serial_port_names
    ]

    stop_event = threading.Event()
    api_resend_thread = threading.Thread(target=resend_failed_records, args=(stop_event,))

    # if database is not in project, is added
    database_initialization()

    # checking if ids from db and api are matching
    compare_api_db_id()

    try:
        # Start the EventProcessor thread
        event_processor.start()

        api_resend_thread.start()

        # Start all reader threads
        for reader in serial_port_readers:
            reader.start()

        # Join all reader threads
        for reader in serial_port_readers:
            reader.thread.join()

        # Join the processor thread
        event_processor.thread.join()

        api_resend_thread.join()

    except KeyboardInterrupt:
        logging.info("Shutting down...")

    finally:
        stop_event.set()
        for reader in serial_port_readers:
            reader.close()
        event_processor.stop()
        con.close()
        logging.info("Serial ports closed")


@click.group()
def cli():
    pass


@click.command(help='Runs the main program.')
def run():
    """Run the main program."""
    try:
        main()
    except KeyboardInterrupt:
        print("Program interrupted and stopped.")


@click.command(help='Number of records that are not sent to api yet.')
def unsent_records():
    print(f"Number of unsent records to api: {get_number_of_unsent_records()}")


@click.command(help='Change location of config file.')
@click.option('--path', prompt='path', help='./path/to/config')
def change_config_path(path):
    config = configparser.ConfigParser()
    config['Path'] = {'config': path}
    with open('./config_path.ini', 'w') as configfile:
        config.write(configfile)
    logging.info(f"Path changed to {path}")


@click.command(help='Receive HWID and activation key, returns login credentials for api.')
@click.option('--hw_id', prompt='HWID', help='MAC address of the device.')
@click.option('--activation_code', prompt='Activation code', help='Activation code for hardware terminal.')
def activate(hw_id, activation_code):
    """Return login credentials for api."""
    params = {
        "ActivationCode": activation_code
    }

    try:
        response = requests.post(f'https://itaserver-staging.mobatime.cloud/api/TerminalActivation?hw_id={hw_id}',
                                 json=params)

        data = response.json()

        if response.status_code == 200:
            print(f"Id: {data['Id']}\n"
                  f"Username: {data['Username']}\n"
                  f"Password: {data['Password']}\n"
                  f"CustomerName: {data['CustomerName']}\n"
                  f"CustomerId: {data['CustomerId']}")
        else:
            logging.error(f"HTTP {response.status_code}: {data.get("Message")}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch API credentials: {e}")
        raise RuntimeError(f"Failed to fetch API credentials: {e}")


cli.add_command(run)
cli.add_command(activate)
cli.add_command(unsent_records)
cli.add_command(change_config_path)


if __name__ == "__main__":
    cli()
