import os
import asyncio
from config.config_loader import read_config, get_project_dir, load_config


default_config_file = "config.yaml"
config_file_valid = False


def check_config_file():
    global config_file_valid
    if config_file_valid:
        return
    """
    Simplified configuration check, just reminds the user about config file usage
    """
    custom_config_file = get_project_dir() + "data/." + default_config_file
    if not os.path.exists(custom_config_file):
        raise FileNotFoundError(
            "Cannot find data/.config.yaml file. Please follow the tutorial to confirm this configuration file exists"
        )

    # Check whether to read configuration from API
    config = asyncio.run(load_config())
    if config.get("read_config_from_api", False):
        print("Reading configuration from API")
        old_config_origin = read_config(custom_config_file)
        if old_config_origin.get("selected_module") is not None:
            error_msg = "Your configuration file seems to contain both console and local configuration:\n"
            error_msg += "\nSuggestions:\n"
            error_msg += "1. Copy the config_from_api.yaml file from the root directory to the data directory and rename it to .config.yaml\n"
            error_msg += "2. Configure the API address and key according to the tutorial\n"
            raise ValueError(error_msg)
    config_file_valid = True
