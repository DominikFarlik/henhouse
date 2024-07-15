import configparser

config_path = './data/config.ini'


def read_config() -> configparser.ConfigParser:
    """Reads the configuration"""
    config = configparser.ConfigParser()
    config.read(config_path)
    print(config_path)
    return config


def set_config_path(new_path: str):
    global config_path
    config_path = new_path
    print(config_path)
