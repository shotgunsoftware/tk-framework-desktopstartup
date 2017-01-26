# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from sgtk.util import UserSettings


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

    def dump(self, logger):
        """
        Dumps Desktop settings inside the logger.

        :param logger: Logger to write the information to.
        """
        logger.info("Custom user setting for Shotgun Desktop:")
        if self.integration_enabled is None:
            logger.info("Integration enabled: <missing>")
        else:
            logger.info("Integration enabled: %s" % self.integration_enabled)

    @property
    def integration_enabled(self):
        """
        :returns: True if the websocket should run, False otherwise.
        """
        # Any non empty string is True, so convert it to int, which will accept 0 or 1 and then
        # we'll cast the return value to a boolean.
        return UserSettings().get_boolean_setting(self._BROWSER_INTEGRATION, "enabled")
