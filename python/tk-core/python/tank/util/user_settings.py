# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
User settings management.
"""

import os
import ConfigParser
import urllib

from .local_file_storage import LocalFileStorageManager
from .errors import EnvironmentVariableFileLookupError, TankError
from .. import LogManager
from .singleton import Singleton


logger = LogManager.get_logger(__name__)


class UserSettings(Singleton):
    """
    Handles finding and loading the user settings for Toolkit. The settings are cached in memory
    so the user settings object can be instantiated multiple times without any issue.

    All the settings are returned as strings. If a setting is missing from the file, ``None`` will
    be returned. If the setting is present but has no value, an empty string will be returned.

    As of this writing, settings can only be updated by editing the ``ini`` file manually.
    """

    _LOGIN = "Login"

    def _init_singleton(self):
        """
        Singleton initialization.
        """
        self._path = self._compute_config_location()
        logger.debug("Reading user settings from %s" % self._path)

        self._user_config = self._load_config(self._path)

        # Log the default settings
        logger.debug("Default site: %s", self._to_friendly_str(self.default_site))
        logger.debug("Default login: %s", self._to_friendly_str(self.default_login))

        self._settings_proxy = self._get_settings_proxy()
        self._system_proxy = None
        if self._settings_proxy is not None:
            logger.debug("Shotgun proxy (from settings): %s", self._get_filtered_proxy(self._settings_proxy))
        else:
            self._system_proxy = self._get_system_proxy()
            if self._system_proxy is not None:
                logger.debug("Shotgun proxy (from system): %s", self._get_filtered_proxy(self._system_proxy))
            else:
                logger.debug("Shotgun proxy: <missing>")

        proxy = self._get_filtered_proxy(self.app_store_proxy)
        logger.debug("App Store proxy: %s", self._to_friendly_str(proxy))

    @property
    def path(self):
        """
        Retrieves the path to the current user settings file.
        """
        return self._path

    @property
    def shotgun_proxy(self):
        """
        Retrieves the value from the ``http_proxy`` setting.

        If the setting is missing from Toolkit.ini, the environment is scanned for variables named
        ``http_proxy``, in case insensitive way. If both lowercase and uppercase environment
        variables exist (and disagree), lowercase is preferred.

        When the method cannot find such environment variables:
        - for Mac OS X, it will look for proxy information from Mac OS X System Configuration,
        - for Windows, it will look for proxy information from Windows Systems Registry.

        .. note:: There is a restriction when looking for proxy information from
                  Mac OS X System Configuration or Windows Systems Registry:
                  in these cases, Toolkit does not support the use of proxies
                  which require authentication (username and password).
        """

        # Return the configuration settings http proxy string when it is specified;
        # otherwise, return the operating system http proxy string.
        if self._settings_proxy is not None:
            return self._settings_proxy
        else:
            return self._system_proxy

    @property
    def app_store_proxy(self):
        """
        Retrieves the value from the ``app_store_http_proxy`` setting.
        """
        return self.get_setting(self._LOGIN, "app_store_http_proxy")

    @property
    def default_site(self):
        """
        Retrieves the value from the ``default_site`` setting.
        """
        return self.get_setting(self._LOGIN, "default_site")

    @property
    def default_login(self):
        """
        Retrieves the value from the ``default_login`` setting.
        """
        return self.get_setting(self._LOGIN, "default_login")

    def get_setting(self, section, name):
        """
        Provides access to any setting, including ones in user defined sections.

        :param str section: Name of the section to retrieve the setting from. Do not include the brackets.
        :param str name: Name of the setting under the provided section.

        :returns: The setting's value if found, ``None`` if the setting is missing from the file or
            an empty string if the setting is present but has no value associated.
        :rtype: str
        """
        if not self._user_config.has_section(section) or not self._user_config.has_option(section, name):
            return None

        value = os.path.expanduser(
            os.path.expandvars(
                self._user_config.get(section, name)
            )
        )
        return value.strip()

    # Unfortunately here for get_boolean_setting and get_integer_setting we're replicating some of the
    # logic from the ConfigParser class. We have to do this because ConfigParser doesn't expand environment
    # variables which is a requirement here, so get_setting does the job of using expandvars so everything
    # gets expanded and then the get_*_setting methods so the necessary casting.

    # This is taken from RawConfigParser. Values are copied in case future Python implementation
    # rename this. (like Python 3, not that this is going to be an issue in the foreseable future. :p)
    _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                       '0': False, 'no': False, 'false': False, 'off': False}

    def get_boolean_setting(self, section, name):
        """
        Provides access to any setting, including ones in user defined sections, and casts it
        into a boolean.

        Values ``1``, ``yes``, ``true`` and ``on`` are converted to ``True`` while ``0``, ``no``,
        ``false``and ``off`` are converted to false. Case is insensitive.

        :param str section: Name of the section to retrieve the setting from. Do not include the brackets.
        :param str name: Name of the setting under the provided section.

        :returns: Boolean if the value is valid, None if not set.
        :rtype: bool

        :raises TankError: Raised if the value is not one of the accepted values.
        """
        value = self.get_setting(section, name)
        if value is None:
            return None

        if value.lower() in self._boolean_states:
            return self._boolean_states[value.lower()]
        else:
            raise TankError(
                "Invalid value '%s' in '%s' for setting '%s' in section '%s': expecting one of '%s'." % (
                    value, self._path, name, section, "', '".join(self._boolean_states.keys())
                )
            )

    def get_integer_setting(self, section, name):
        """
        Provides access to any setting, including ones in user defined sections, and casts it
        into an integer.

        :param str section: Name of the section to retrieve the setting from. Do not include the brackets.
        :param str name: Name of the setting under the provided section.

        :returns: Boolean if the value is valid, None if not set.
        :rtype: bool

        :raises TankError: Raised if the value is not one of the accepted values.
        """
        value = self.get_setting(section, name)
        if value is None:
            return None

        try:
            return int(value)
        except ValueError:
            raise TankError(
                "Invalid value '%s' in '%s' for setting '%s' in section '%s': expecting integer." % (
                    value, self._path, name, section
                )
            )

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

    def _compute_config_location(self):
        """
        Retrieves the location of the ``config.ini`` file. It will look in multiple locations:

            - The ``SGTK_PREFERENCES_LOCATION`` environment variable.
            - The ``SGTK_DESKTOP_CONFIG_LOCATION`` environment variable.
            - The Shotgun folder.
            - The Shotgun Desktop folder.

        :returns: The location where to read the configuration file from.
        """

        # This is the default location.
        default_location = os.path.join(
            LocalFileStorageManager.get_global_root(LocalFileStorageManager.PREFERENCES),
            "toolkit.ini"
        )

        # This is the complete list of paths we need to test.
        file_locations = [
            self._evaluate_env_var("SGTK_PREFERENCES_LOCATION"),
            self._evaluate_env_var("SGTK_DESKTOP_CONFIG_LOCATION"),
            # Default location first
            default_location,
            # This is the location set by users of the Shotgun Desktop in the past.
            os.path.join(
                LocalFileStorageManager.get_global_root(
                    LocalFileStorageManager.CACHE,
                    LocalFileStorageManager.CORE_V17
                ),
                "desktop", "config", "config.ini"
            )
        ]

        # Search for the first path that exists and then use it.
        for loc in file_locations:
            if loc and os.path.exists(loc):
                return loc

        # Nothing was found, just use the default location even tough it's empty.
        return default_location

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

    def _get_settings_proxy(self):
        """
        Retrieves the configuration settings http proxy.

        :returns: The configuration settings http proxy string or ``None`` when it is not specified.
        """
        return self.get_setting(self._LOGIN, "http_proxy")

    def _get_system_proxy(self):
        """
        Retrieves the operating system http proxy.

        First, the method scans the environment for variables named http_proxy, in case insensitive way.
        If both lowercase and uppercase environment variables exist (and disagree), lowercase is preferred.

        When the method cannot find such environment variables:
        - for Mac OS X, it will look for proxy information from Mac OS X System Configuration,
        - for Windows, it will look for proxy information from Windows Systems Registry.

        .. note:: There is a restriction when looking for proxy information from
                  Mac OS X System Configuration or Windows Systems Registry:
                  in these cases, the Toolkit does not support the use of proxies
                  which require authentication (username and password).

        :returns: The operating system http proxy string or ``None`` when it is not defined.
        """

        # Get the dictionary of scheme to proxy server URL mappings; for example:
        #     {"http": "http://foo:bar@74.50.63.111:80", "https": "http://74.50.63.111:443"}
        # "getproxies" scans the environment for variables named <scheme>_proxy, in case insensitive way.
        # When it cannot find it, for Mac OS X it looks for proxy information from Mac OSX System Configuration,
        # and for Windows it looks for proxy information from Windows Systems Registry.
        # If both lowercase and uppercase environment variables exist (and disagree), lowercase is preferred.
        # Note the following restriction: "getproxies" does not support the use of proxies which
        # require authentication (user and password) when looking for proxy information from
        # Mac OSX System Configuration or Windows Systems Registry.
        system_proxies = urllib.getproxies()

        # Get the http proxy when it exists in the dictionary.
        proxy = system_proxies.get("http")

        if proxy:
            # Remove any spurious "http://" from the http proxy string.
            proxy = proxy.replace("http://", "", 1)

        return proxy

    def _to_friendly_str(self, value):
        """
        Converts the value into a meaningful value for the user if the setting is missing or
        empty.

        :returns: If None, returns ``<missing>``. If an empty string, returns ``<empty>`. Otherwise
            returns the value as is.
        """
        if value is None:
            return "<missing>"
        elif value is "":
            return "<empty>"
        else:
            return value
