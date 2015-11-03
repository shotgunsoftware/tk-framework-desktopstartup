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
import ConfigParser

from . import logger

logger = logger.get_logger("settings")


class Settings(object):
    """
    Reads the optionally configured configuration file present in the Desktop
    installer package. This file is in the root of the installed application folder on
    Linux and Windows and in Contents/Resources on MacOSX.

    The configuration file should have the following format:
    [BrowserIntegration]
    port=9000
    debug=1
    whitelist=*.shotgunstudio.com
    certificate_folder=/path/to/the/certificate
    """

    _BROWSER_INTEGRATION = "BrowserIntegration"

    def __init__(self, location, default_certificate_folder):
        """
        Constructor.

        If the configuration file doesn't not exist, the configuration
        object will return the default values.

        :param location: Path to the configuration file.
        :param default_certificate_folder: Default location for the certificate file. This value
            is overridable for each app that can use this settings object.
        """
        self._config = self._load_config(location)
        self._default_certificate_folder = default_certificate_folder

    def _load_config(self, path):
        """
        Loads the configuration at a given location and returns it.

        :param path: Path to the configuration to load.

        :returns: A ConfigParser instance with the contents from the configuration file.
        """
        config = ConfigParser.SafeConfigParser()
        if os.path.exists(path):
            config.read(path)
        return config

    @property
    def port(self):
        """
        :returns: The port to listen on for incoming websocket requests.
        """
        return self._get_value(self._BROWSER_INTEGRATION, "port", int, 9000)

    @property
    def low_level_debug(self):
        """
        :returns: True if the server should run in low level debugging mode. False otherwise.
        """
        # Any non empty string is True, so convert it to int, which will accept 0 or 1 and then
        # we'll cast the return value to a boolean.
        return bool(self._get_value(self._BROWSER_INTEGRATION, "low_level_debug", int, False))

    @property
    def whitelist(self):
        """
        :returns: The list of clients that can connect to the server.
        """
        return self._get_value(self._BROWSER_INTEGRATION, "whitelist", default="*.shotgunstudio.com")

    @property
    def certificate_folder(self):
        """
        :returns: Path to the certificate location.
        """
        return self._get_value(
            self._BROWSER_INTEGRATION, "certificate_folder", default=self._default_certificate_folder
        )

    def dump(self, logger):
        """
        Dumps all the settings into the logger.
        """
        logger.info("Certificate folder: %s" % self.certificate_folder)
        logger.info("Low level debug: %s" % self.low_level_debug)
        logger.info("Port: %d" % self.port)
        logger.info("Whitelist: %s" % self.whitelist)

    def _get_value(self, section, key, type_cast=str, default=None):
        """
        Retrieves a value from the config.ini file. If the value is not set, returns the default.
        Since all values are strings inside the file, you can optionally cast the data to another type.

        :param section: Section (name between brackets) of the setting.
        :param key: Name of the setting within a section.
        ;param type_cast: Casts the value to the passed in type. Defaults to str.
        :param default: If the value is not found, returns this default value. Defauts to None.

        :returns: The appropriately type casted value if the value is found, default otherwise.
        """
        if not self._config.has_section(section):
            return default
        elif not self._config.has_option(section, key):
            return default
        else:
            return type_cast(self._resolve_value(section, key))

    def _resolve_value(self, section, key):
        """
        Resolves a value in the file and translates any environment variable or ~ present.

        :param section: Name of the section of the value.
        :param key: Key of the value to retrieve for the selection section.

        :returns: Value with ~ and any environment variable resolved.
        """
        return os.path.expandvars(
            os.path.expanduser(
                self._config.get(section, key)
            )
        )
