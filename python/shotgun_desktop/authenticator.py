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
import sys
import shotgun_desktop.paths
import ConfigParser


def get_configured_shotgun_authenticator(sg_auth_module):
    """
    Returns a Shotgun Authenticator configured to read the optional config.ini file stored in the
    install to provide default host and login for first time users of the app as well as configuring
    the http proxy.
    """

    # Since the shotgun_authenticatioin module is uuid-loaded, it needs to be passed as a parameter
    # to this method and the class be locally defined instead of the module being imported globally
    # and the class defined globally as well.
    class DesktopAuthenticationManager(sg_auth_module.DefaultsManager):
        """
        Provides default host and login for first time users of the Desktop application as well as
        an http proxy.
        """

        def __init__(self):
            """
            Constructor. Reads the optionally configured config.ini file present in the Desktop
            installer package. This file is in the root of the installed application folder on
            Linux and Windows and in Contents/Resources on MacOSX.

            The config.ini should have the following format
            [Login]
            default_login=login
            default_site=site.shotgunstudio.com
            http_proxy=http://www.someproxy.com:3128
            """
            super(DesktopAuthenticationManager, self).__init__()
            self._default_login = None
            self._default_host = None
            self._default_http_proxy = None

            # Load up login config if it exists

            if "SGTK_DEFAULT_LOGIN_DEBUG_LOCATION" in os.environ:
                login_config = os.environ["SGTK_DEFAULT_LOGIN_DEBUG_LOCATION"]
            elif sys.platform == "darwin":
                login_config = os.path.join(shotgun_desktop.paths.get_shotgun_app_root(), "Contents", "Resources", "config.ini")
            else:
                login_config = os.path.join(shotgun_desktop.paths.get_shotgun_app_root(), "config.ini")
            if os.path.exists(login_config):
                # Try to load default login, site, and proxy from config
                config = ConfigParser.SafeConfigParser({"default_login": None, "default_site": None, "http_proxy": None})
                config.read(login_config)
                if config.has_section("Login"):
                    default_login = config.get("Login", "default_login", raw=True)
                    default_host = config.get("Login", "default_site", raw=True)
                    http_proxy = config.get("Login", "http_proxy", raw=True)

                    # Update the default values
                    if default_login is not None:
                        self._default_login = os.path.expandvars(default_login)
                    if default_host is not None:
                        self._default_host = os.path.expandvars(default_host)
                    if http_proxy is not None:
                        self._default_http_proxy = os.path.expandvars(http_proxy)

        def get_host(self):
            """
            If there is no current host, returns the host configured in config.ini.

            :returns: The default host string.
            """
            host = super(DesktopAuthenticationManager, self).get_host()
            if host:
                return host
            else:
                return self._default_host

        def get_login(self):
            """
            If there is no current login, returns the login configured in config.ini.

            :returns: The default login string.
            """
            login = super(DesktopAuthenticationManager, self).get_login()
            if login:
                return login
            else:
                return self._default_login

        def get_http_proxy(self):
            """
            If there is no current http proxy, returns the http proxy configured in config.ini.

            :returns: The default http proxy string.
            """
            http_proxy = super(DesktopAuthenticationManager, self).get_http_proxy()
            if http_proxy:
                return http_proxy
            else:
                return self._default_http_proxy

    return sg_auth_module.ShotgunAuthenticator(DesktopAuthenticationManager())
