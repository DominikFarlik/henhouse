import click
import logging
import requests  # type: ignore

from .config import set_config_path
from .save_operations import get_number_of_unsent_records


@click.group()
def cli():
    pass


@click.command(help='Runs the main program.')
@click.option('--config_path', help='./path/to/config')
def run(config_path):
    if config_path:
        set_config_path(config_path)
    from .__main__ import main
    main()


@click.command(help='Number of records that are not sent to api yet.')
def unsent_records():
    print(f"Number of unsent records to api: {get_number_of_unsent_records()}")


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


cli.add_command(activate)
cli.add_command(unsent_records)
cli.add_command(run)

cli()
