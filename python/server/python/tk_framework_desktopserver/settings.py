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

    _DEFAULT_PORT = 9000
    _DEFAULT_LOW_LEVEL_DEBUG_VALUE = False
    _DEFAULT_WHITELIST = "*.shotgunstudio.com"

    _BROWSER_INTEGRATION = "BrowserIntegration"
    _PORT_SETTING = "port"
    _LOW_LEVEL_DEBUG_SETTING = "low_level_debug"
    _WHITELIST_SETTING = "whitelist"
    _CERTIFICATE_FOLDER_SETTING = "certificate_folder"

    def __init__(self, location, default_certificate_folder):
        """
        Constructor.

        If the configuration file doesn't not exist, the configuration
        object will return the default values.

        :param location: Path to the configuration file. If ``None``, Toolkit's sgtk.util.UserSettings module
            will be used instead to retrieve the values.
        :param default_certificate_folder: Default location for the certificate file. This value
            is overridable for each app that can use this settings object.
        """

        self._default_certificate_folder = default_certificate_folder

        # Retrieve all the settings from the configuration file or the Tookit UserSettings object.
        if location is not None:
            config = self._load_config(location)
            port = self._get_value(
                config, self._PORT_SETTING, int
            )
            low_level_debug = bool(
                self._get_value(
                    config, self._LOW_LEVEL_DEBUG_SETTING, int
                )
            )
            whitelist = self._get_value(
                config, self._WHITELIST_SETTING
            )
            certificate_folder = self._get_value(
                config, self._CERTIFICATE_FOLDER_SETTING
            )
        else:
            from sgtk.util import UserSettings
            user_settings = UserSettings()
            port = user_settings.get_integer_setting(
                self._BROWSER_INTEGRATION, self._PORT_SETTING
            )
            low_level_debug = user_settings.get_boolean_setting(
                self._BROWSER_INTEGRATION, self._LOW_LEVEL_DEBUG_SETTING
            )
            whitelist = user_settings.get_setting(
                self._BROWSER_INTEGRATION, self._WHITELIST_SETTING
            )
            certificate_folder = user_settings.get_setting(
                self._BROWSER_INTEGRATION, self._CERTIFICATE_FOLDER_SETTING
            )

        self._port = port or self._DEFAULT_PORT
        self._low_level_debug = low_level_debug or self._DEFAULT_LOW_LEVEL_DEBUG_VALUE
        self._whitelist = whitelist or self._DEFAULT_WHITELIST
        self._certificate_folder = certificate_folder or self._default_certificate_folder

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
        return self._port

    @property
    def low_level_debug(self):
        """
        :returns: True if the server should run in low level debugging mode. False otherwise.
        """
        # Any non empty string is True, so convert it to int, which will accept 0 or 1 and then
        # we'll cast the return value to a boolean.
        return self._low_level_debug

    @property
    def whitelist(self):
        """
        :returns: The list of clients that can connect to the server.
        """
        return self._whitelist

    @property
    def certificate_folder(self):
        """
        :returns: Path to the certificate location.
        """
        return self._certificate_folder

    def dump(self, logger):
        """
        Dumps all the settings into the logger.
        """
        logger.info("Certificate folder: %s" % self.certificate_folder)
        logger.info("Low level debug: %s" % self.low_level_debug)
        logger.info("Port: %d" % self.port)
        logger.info("Whitelist: %s" % self.whitelist)

    def _get_value(self, config, key, type_cast=str):
        """
        Retrieves a value from the config.ini file. If the value is not set, returns the default.
        Since all values are strings inside the file, you can optionally cast the data to another type.

        :param config: Configuration parser holding the settings.
        :param section: Section (name between brackets) of the setting.
        :param key: Name of the setting within a section.
        ;param type_cast: Casts the value to the passed in type. Defaults to str.
        :param default: If the value is not found, returns this default value. Defauts to None.

        :returns: The appropriately type casted value if the value is found, default otherwise.
        """
        section = self._BROWSER_INTEGRATION
        if config.has_section(section) and config.has_option(section, key):
            return type_cast(self._resolve_value(config, section, key))
        else:
            return None

    def _resolve_value(self, config, section, key):
        """
        Resolves a value in the file and translates any environment variable or ~ present.

        :param config: Configuration parser holding the settings.
        :param section: Name of the section of the value.
        :param key: Key of the value to retrieve for the selection section.

        :returns: Value with ~ and any environment variable resolved.
        """
        return os.path.expandvars(
            os.path.expanduser(
                config.get(section, key)
            )
        )
