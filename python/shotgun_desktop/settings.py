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
from .logger import get_logger

logger = get_logger("settings")


class Settings(object):
    """
    Reads the optionally configured config.ini file present in the Desktop
    installer package. This file is in the root of the installed application folder on
    Linux and Windows and in Contents/Resources on MacOSX.

    The config.ini should have the following format
    [BrowserIntegration]
    enabled=1
    """

    _BROWSER_INTEGRATION = "BrowserIntegration"

    def __init__(self):
        """
        Constructor.
        """
        # FIXME: Violating API, need to figure out how we'll find toolkit.ini from outside core.
        from sgtk.util.user_settings import UserSettings
        self._path = UserSettings().location
        logger.info("Reading global settings from %s" % self._path)
        self._global_config = self._load_config(self._path)

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

    def dump(self, logger):
        """
        Dumps Desktop settings inside the logger.

        :param logger: Logger to write the information to.
        """
        logger.info("config.ini/toolkit.ini location: %s" % self._path)
        logger.info("Integration enabled: %s" % self.integration_enabled)

    @property
    def location(self):
        """
        :returns str: Path to the configuration file.
        """
        return self._path

    @property
    def integration_enabled(self):
        """
        :returns: True if the websocket should run, False otherwise.
        """
        # Any non empty string is True, so convert it to int, which will accept 0 or 1 and then
        # we'll cast the return value to a boolean.
        if self._global_config.has_option(self._BROWSER_INTEGRATION, "enabled"):
            self._global_config.getboolean(self._BROWSER_INTEGRATION, "enabled")
        else:
            return True
