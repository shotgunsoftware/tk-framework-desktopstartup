# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os

from tk_framework_desktopserver import Settings, MissingConfigurationFileError, get_logger


def get_settings(configuration):
    """
    Retrieves the location of the config.ini file for the standalone apps. It will first look at the
    command line arguments. If the file specified on the command line doesn't exist, an error will
    be thrown. Then the SGTK_BROWSER_INTEGRATION_CONFIG_LOCATION environment variable will be evaluated.
    If the value points to a non existing path, an error will be thrown. Then the config.ini
    file in the current folder will be parsed. If the file is missing, a settings object with only
    default settings will be returned.

    :param configuration: Path to the configuration path. Can be None.

    :returns: The location where to read the configuration file from.

    :raises MissingConfigurationFileError: Raised when the user supplied configuration file
        doesn't exist on disk.
    """

    # First check the command line.
    if configuration is not None:
        location = configuration
    # Then check the environment variable.
    elif "SGTK_BROWSER_INTEGRATION_CONFIG_LOCATION" in os.environ:
        location = os.environ["SGTK_BROWSER_INTEGRATION_CONFIG_LOCATION"]
    else:
        # Nothing has been found!
        location = None

    # If the user specified a location and it doesn't exist, raise an error.
    if location and not os.path.exists(location):
        raise MissingConfigurationFileError(location)

    # Create an absolute path to the file.
    app_dir = os.path.abspath(os.path.dirname(__file__))

    # If no location was specified, simply read from the local directory.
    if location is None:
        location = os.path.join(app_dir, "config.ini")

    get_logger("settings").debug("Using configuration file at '%s'" % location)
    return Settings(
        location,
        # Go back up a folder to retrieve the root of the package and drill
        # into the resource files to look for the keys
        os.path.join(
            os.path.dirname(app_dir),
            "resources", "keys"
        )
    )
