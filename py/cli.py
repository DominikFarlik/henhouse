import logging

import click
import requests
from requests.auth import HTTPBasicAuth
from main import main


@click.group()
def manage():
    pass


@click.command(help='Runs the main program.')
def run():
    """Run the main program."""
    try:
        main()
    except KeyboardInterrupt:
        print("Program interrupted and stopped.")


@click.command(help='By received HWID and activation key returns login credentials for api.')
@click.option('--hw_id', prompt='HWID', help='MAC address of the device.')
@click.option('--activation_code', prompt='Activation code', help='Activation code for hardware terminal.')
def activate(hw_id, activation_code):
    params = {
        "ActivationCode": activation_code
    }

    try:
        response = requests.post(f'https://itaserver-staging.mobatime.cloud/api/TerminalActivation?hw_id={hw_id}',
                                 json=params)

        data = response.json()

        print(f"Id:{data['Id']}\n"
              f"Username: {data['Username']}\n"
              f"Password: {data['Password']}\n"
              f"CustomerName: {data['CustomerName']}\n"
              f"CustomerId: {data['CustomerId']}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch API credentials: {e}")


# Add commands to the manage group
manage.add_command(run)
manage.add_command(activate)

if __name__ == '__main__':
    manage()
