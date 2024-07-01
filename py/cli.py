import click
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
    print(hw_id, activation_code)


# Add commands to the manage group
manage.add_command(run)
manage.add_command(activate)

if __name__ == '__main__':
    manage()
