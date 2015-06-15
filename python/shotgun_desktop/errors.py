# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Shotgun Desktop Errors
"""

import os
import sys


class ShotgunDesktopError(Exception):
    """
    Common base class for Shotgun Desktop errors
    """
    pass


class RequestRestartException(ShotgunDesktopError):
    """
    Short circuits all the application code for a quick exit. The user
    wants to reinitialize the app.
    """
    pass


class UpgradeCoreError(ShotgunDesktopError):
    """
    This exception notifies the catcher that the site's core needs to be upgraded in order to
    use this version of the Desktop installer.
    """
    def __init__(self, core_version, toolkit_path):
        """Constructor"""
        ShotgunDesktopError.__init__(
            self,
            "This version of the Shotgun Desktop only supports Toolkit %s and higher. "
            "Please upgrade your site core by running:\n\n%s core" %
            (core_version,
             os.path.join(toolkit_path, "tank.bat" if sys.platform == "win32" else "tank"))
        )


class ToolkitDisabledError(ShotgunDesktopError):
    """
    This exception notifies the catcher that Toolkit has not been enabled by the user on the site.
    """
    def __init__(self):
        """Constructor"""
        ShotgunDesktopError.__init__(
            self,
            "Toolkit has not been activated on your site. Please activate Toolkit before relaunching Shotgun Desktop."
        )


class UpdatePermissionsError(ShotgunDesktopError):
    """
    This exception notifies the catcher that the site's human user permissions doesn't allow
    using the Shotgun Desktop.
    """
    def __init__(self):
        """Constructor"""
        ShotgunDesktopError.__init__(
            self,
            "Sorry, you do not have enough Shotgun permissions to set up the Shotgun Desktop.\n\n"
            "Please relaunch Desktop and instead log in as an Admin user.\n\n"
            "Once the setup is complete, you can log out the Admin user and then log in as yourself."
        )


class BundledDescriptorEnvVarError(ShotgunDesktopError):
    """
    This exception notifies the catcher that the bundled descriptor in
    SGTK_DESKTOP_BUNDLED_DESCRIPTOR couldn't be parsed correctly.
    """
    def __init__(self, reason):
        ShotgunDesktopError.__init__(
            self,
            "Error parsing SGTK_DESKTOP_BUNDLED_DESCRIPTOR: %s" % reason
        )


class SitePipelineConfigurationNotFound(ShotgunDesktopError):
    """
    This exception notifiers the catcher that the site's pipeline configuration can't be found.
    """
    def __init__(self, site_config_path):
        """
        Constructor
        """
        Exception.__init__(
            self,
            "Can't find your site's pipeline configuration.\n\n"
            "This can happen if you don't have the permissions to see the Template Project or if "
            "the site's pipeline configuration id in Shotgun differs from the one at "
            "%s/config/core/pipeline_configuration.yml." % site_config_path
        )
