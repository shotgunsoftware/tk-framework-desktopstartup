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


# This exception is handled on its own and doesn't have an error message associated to it, compared to other
# ShotgunDesktop errors, so we can derive from Exception directly.
class RequestRestartException(Exception):
    """
    Short circuits all the application code for a quick exit. The user
    wants to reinitialize the app.
    """
    pass


class ShotgunDesktopError(Exception):
    """
    Common base class for Shotgun Desktop errors.
    """
    def __init__(self, message):
        """Constructor"""
        Exception.__init__(
            self,
            "%s\n\n"
            "If you need help with this issue, please contact our support team at "
            "support@shotgunsoftware.com." % message
        )


class InvalidPipelineConfiguration(ShotgunDesktopError):
    """
    This exception notifies the caller that the pipeline configuration id found in Shotgun
    doesn't match the pipeline configuration found on disk.
    """

    def __init__(self, pc_entity, site_pc):
        """Constructor"""
        pc_project_id = pc_entity["project"]["id"] if pc_entity["project"] else None
        ShotgunDesktopError.__init__(
            self,
            "The pipeline configuration retrieved from Shotgun (named \"%s\" "
            "with id %d and project id %s) does not match the site configuration found on disk "
            "(named \"%s\" with id %d and project id %s). Please contact your Shotgun "
            "Administrator." %
            (pc_entity["code"], pc_entity["id"], pc_project_id,
             site_pc.get_name(), site_pc.get_shotgun_id(), site_pc.get_project_id())
        )


class UpgradeCoreError(ShotgunDesktopError):
    """
    This exception notifies the catcher that the site's core needs to be upgraded in order to
    use this version of the Desktop installer.
    """
    def __init__(self, reason, toolkit_path):
        """Constructor"""
        ShotgunDesktopError.__init__(
            self,
            "%s Please upgrade your site core by running:\n\n%s core" %
            (reason, os.path.join(toolkit_path, "tank.bat" if sys.platform == "win32" else "tank"))
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


class UnexpectedConfigFound(ShotgunDesktopError):
    """
    This exception notifies the catcher that a configuration was found on disk when none was expected.
    """
    def __init__(self, default_site_config):
        """Constructor"""
        ShotgunDesktopError.__init__(
            self,
            "A pipeline configuration was found at \"%s\" but no matching pipeline configuration was found in Shotgun.\n\n"
            "This can happen if you are not assigned to the \"Template Project\". Please contact your Shotgun "
            "Administrator to see if that is the case." % default_site_config
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
            "Once the setup is complete, you can log out the Admin user and then log in as yourself.\n\n"
            "Please note that this error can also occur when you are not assigned to the \"Template Project\"."
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
