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


def get_configured_shotgun_authenticator(sg_auth_module, settings):
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
            super(DesktopAuthenticationManager, self).__init__()
            self._default_login = settings.default_login
            self._default_host = settings.default_site
            self._default_http_proxy = settings.default_http_proxy

            # Update the default values
            if self._default_login is not None:
                self._default_login = os.path.expandvars(self._default_login)
            if self._default_host is not None:
                self._default_host = os.path.expandvars(self._default_host)
            if self._default_http_proxy is not None:
                self._default_http_proxy = os.path.expandvars(self._default_http_proxy)

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
