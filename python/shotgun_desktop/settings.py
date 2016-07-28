# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import os
import ConfigParser
from .logger import get_logger
from .errors import EnvironmentVariableFileLookupError, ShotgunDesktopError

logger = get_logger("settings")


class Settings(object):
    """
    Reads the optionally configured config.ini file present in the Desktop
    installer package. This file is in the root of the installed application folder on
    Linux and Windows and in Contents/Resources on MacOSX.

    The config.ini should have the following format
    [Login]
    default_login=login
    default_site=site.shotgunstudio.com
    http_proxy=http://www.someproxy.com:3128
    app_store_http_proxy=http://www.someproxy.com:3128
    [BrowserIntegration]
    enabled=1
    """

    _LOGIN = "Login"
    _BROWSER_INTEGRATION = "BrowserIntegration"

    def __init__(self, bootstrap):
        """
        Constructor.

        :param bootstrap: The application bootstrap.
        """

        self._bootstrap = bootstrap
        path = self.get_config_location()
        logger.info("Reading global settings from %s" % path)
        self._global_config = self._load_config(path)

    def _get_install_dir_config_location(self, bootstrap):
        """
        :param bootstrap: The application bootstrap.

        :returns: Path to the config.ini file within the installation folder.
        """
        if sys.platform == "darwin":
            return os.path.join(bootstrap.get_app_root(), "Contents", "Resources", "config.ini")
        else:
            return os.path.join(bootstrap.get_app_root(), "config.ini")

    def _get_desktop_dir_config_location(self, bootstrap):
        """
        :param bootstrap: The application bootstrap.

        :returns: Path to the config.ini within the desktop's user folder.
        """
        return os.path.join(
            bootstrap.get_shotgun_desktop_cache_location(),
            "config",
            "config.ini"
        )

    def _get_user_dir_config_location(self, bootstrap):
        """
        :param bootstrap: The application bootstrap.

        :returns: Path to the config.ini within the user folder.
        """
        if sys.platform == "darwin":
            return os.path.expanduser("~/Library/Preferences/Shotgun/toolkit.ini")
        elif sys.platform == "win32":
            return os.path.join(os.environ.get("APPDATA", "APPDATA_NOT_SET"), "Shotgun", "Preferences", "toolkit.ini")
        elif sys.platform.startswith("linux"):
            return os.path.expanduser("~/.shotgun/preferences/toolkit.ini")
        else:
            raise ShotgunDesktopError("Unknown platform: %s" % sys.platform)

    def _evaluate_env_var(self, var_name):
        """
        Evaluates an environment variable.

        :param var_name: Variable to evaluate.

        :returns: Value if set, None otherwise.

        :raises EnvironmentVariableFileLookupError: Raised if the variable is set, but the file doesn't
                                                    exist.
        """
        if var_name not in os.environ:
            return None

        # If the path doesn't exist, raise an error.
        raw_path = os.environ[var_name]
        path = os.path.expanduser(raw_path)
        path = os.path.expandvars(path)
        if not os.path.exists(path):
            raise EnvironmentVariableFileLookupError(var_name, raw_path)

        # Path is set and exist, we've found it!
        return path

    def get_config_location(self):
        """
        Retrieves the location of the config.ini file. It will first look inside at the
        SGTK_PREFERENCES_LOCATION variable, then SGTK_DESKTOP_CONFIG_LOCATION variable,
        then the user preferences folder, then the desktop preferences folder and
        finally the installation directory.

        :returns: The location where to read the configuration file from.
        """
        # Look inside the user folder. If it exists, return that path.

        file_locations = [
            self._evaluate_env_var("SGTK_PREFERENCES_LOCATION"),
            self._evaluate_env_var("SGTK_DESKTOP_CONFIG_LOCATION"),
            self._get_user_dir_config_location(self._bootstrap),
            self._get_desktop_dir_config_location(self._bootstrap),
        ]
        for loc in file_locations:
            if loc and os.path.exists(loc):
                return loc

        return self._get_install_dir_config_location(self._bootstrap)

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
        Dumps all the settings into the logger.

        :param logger: Logger to write the information to.
        """
        logger.info("config.ini location: %s" % self.get_config_location())
        logger.info("Default site: %s" % self.default_site)
        logger.info("Default proxy: %s" % self._get_filtered_proxy(self.default_http_proxy))
        proxy = self._get_filtered_proxy(self.default_app_store_http_proxy)
        logger.info("Default app store proxy: %s" % ("<not set>" if proxy is None else proxy))
        logger.info("Default login: %s" % self.default_login)
        logger.info("Integration enabled: %s" % self.integration_enabled)

    @property
    def default_http_proxy(self):
        """
        :returns: The default proxy.
        """
        return self._get_value(self._LOGIN, "http_proxy")

    @property
    def default_app_store_http_proxy(self):
        """
        :returns: If None, the proxy wasn't set. If an empty string, it has been forced to
        """
        # Passing PROXY_NOT_SET and getting it back means that the proxy wasn't set in the file.
        _PROXY_NOT_SET = "PROXY_NOT_SET"
        proxy = self._get_value(self._LOGIN, "app_store_http_proxy", default=_PROXY_NOT_SET)

        # If proxy wasn't set, then return None, which means Toolkit will use the value from the http_proxy
        # setting for the app store proxy.
        if proxy == _PROXY_NOT_SET:
            return None
        # If the proxy was set to a falsy value, it means it was hardcoded to be None.
        elif not proxy:
            return ""
        else:
            return proxy

    @property
    def default_site(self):
        """
        :returns: The default site.
        """
        return self._get_value(self._LOGIN, "default_site")

    @property
    def default_login(self):
        """
        :returns: The default login.
        """
        return self._get_value(self._LOGIN, "default_login")

    @property
    def integration_enabled(self):
        """
        :returns: True if the websocket should run, False otherwise.
        """
        # Any non empty string is True, so convert it to int, which will accept 0 or 1 and then
        # we'll cast the return value to a boolean.
        return bool(self._get_value(self._BROWSER_INTEGRATION, "enabled", int, True))

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
        if not self._global_config.has_section(section):
            return default
        elif not self._global_config.has_option(section, key):
            return default
        else:
            return type_cast(self._global_config.get(section, key))

    def _get_filtered_proxy(self, proxy):
        """
        :param proxy: Proxy server address for which we required credentials filtering.

        :returns: Returns the proxy settings with credentials masked.
        """
        # If there is an address available
        # If there is a username and password in the proxy string. Proxy is None when not set
        # so test that first.
        if proxy and "@" in proxy:
            # Filter out the username and password
            # Given xzy:123@localhost or xyz:12@3@locahost, this will return localhost in both cases
            return "<your credentials have been removed for security reasons>@%s" % proxy.rsplit("@", 1)[-1]
        else:
            return proxy
