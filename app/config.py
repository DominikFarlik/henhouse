import configparser


def read_config(filename='./config_path.ini'):
    """Reads the configuration"""
    config = configparser.ConfigParser()
    config.read(filename)
    path_to_config = config.get('Path', 'config')

    config = configparser.ConfigParser()
    config.read(path_to_config)
    return config
