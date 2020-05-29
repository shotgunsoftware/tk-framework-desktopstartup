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
import sgtk


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

    _SUPPORT_EMAIL = "support@shotgunsoftware.com"

    def __init__(self, message, support_required=False):
        """
        :param message: Error message to display.
        :param optional_support: Indicates if the epilog should mention that contacting support is optional
             or required to resolve this issue.
        """

        if support_required:
            support_message = "Please contact {0} to resolve this issue.".format(
                self._SUPPORT_EMAIL
            )
        else:
            support_message = (
                "If you need help with this issue, please contact {0}."
            ).format(self._SUPPORT_EMAIL)
        Exception.__init__(self, "%s\n\n%s" % (message, support_message))


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
            'The pipeline configuration retrieved from Shotgun (named "%s" '
            "with id %d and project id %s) does not match the site configuration found on disk "
            '(named "%s" with id %d and project id %s). Please contact your Shotgun '
            "Administrator."
            % (
                pc_entity["code"],
                pc_entity["id"],
                pc_project_id,
                site_pc.get_name(),
                site_pc.get_shotgun_id(),
                site_pc.get_project_id(),
            ),
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
            "%s Please upgrade your site core by running:\n\n%s core"
            % (
                reason,
                os.path.join(
                    toolkit_path, "tank.bat" if sgtk.util.is_windows() else "tank",
                ),
            ),
        )


class UpgradeEngine200Error(ShotgunDesktopError):
    """
    This exception notifies the catcher that the site's desktop engine needs to be upgraded in order
    to use this version of the Desktop installer.
    """

    def __init__(self, reason, toolkit_path):
        """Constructor"""
        ShotgunDesktopError.__init__(
            self,
            "%s Please upgrade your site engine by running:\n\n%s updates site"
            % (
                reason,
                os.path.join(
                    toolkit_path, "tank.bat" if sgtk.util.is_windows() else "tank"
                ),
            ),
        )


class UpgradeEngine253Error(ShotgunDesktopError):
    """
    This exception notifies the catcher that the site's desktop engine needs to be upgraded in order
    to use this version of the Desktop installer.
    """

    def __init__(self):
        """Constructor"""
        ShotgunDesktopError.__init__(
            self,
            "It appears your site configuration is running a tk-desktop engine meant "
            "for Shotgun Desktop 1.5.7.\n"
            "\n"
            "You need to upgrade the tk-desktop engine to v2.5.3+ in your site configuration or "
            "install Shotgun Desktop 1.5.7.",
        )


class ToolkitDisabledError(ShotgunDesktopError):
    """
    This exception notifies the catcher that Toolkit has not been enabled by the user on the site.
    """

    def __init__(self):
        """Constructor"""
        ShotgunDesktopError.__init__(
            self,
            "Toolkit has not been activated on your site. Please activate Toolkit before relaunching Shotgun Desktop.",
        )


class MissingPython3SupportError(ShotgunDesktopError):
    def __init__(self):
        """
        """
        super(MissingPython3SupportError, self).__init__(
            "The tk-desktop engine in your site configuration may not support Python 3.\n"
            "\n"
            "You need to upgrade the tk-desktop engine to v2.5.1+ in your site configuration or "
            "launch the Shotgun Desktop in Python 2 mode."
        )
