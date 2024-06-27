import configparser


def read_config(filename='../config.ini'):
    """Reads the configuration"""
    config = configparser.ConfigParser()
    config.read(filename)
    return config
