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
Flow Production Tracking Errors
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
    Common base class for Flow Production Tracking errors.
    """

    def __init__(self, message, support_required=False):
        """
        :param message: Error message to display.
        :param optional_support: Indicates if the epilog should mention that contacting support is optional
             or required to resolve this issue.
        """

        if support_required:
            support_message = (
                "Please <a href={}>contact support</a> to resolve this issue.".format(
                    sgtk.support_url
                )
            )
        else:
            support_message = (
                "If you need help with this issue, please <a href={}>contact support</a>."
            ).format(sgtk.support_url)
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
            'The pipeline configuration retrieved from Flow Production Tracking (named "%s" '
            "with id %d and project id %s) does not match the site configuration found on disk "
            '(named "%s" with id %d and project id %s). Please contact your Flow Production Tracking '
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
                    toolkit_path,
                    "tank.bat" if sgtk.util.is_windows() else "tank",
                ),
            ),
        )


class UpgradeCorePython3Error(ShotgunDesktopError):
    """
    This exception notifies the catcher that the site's core needs to be upgraded in order to
    use this version of the Desktop installer, due to a Python 3 incompatibility.
    """

    def __init__(self):
        """Constructor"""
        ShotgunDesktopError.__init__(
            self,
            "You are running a pre v0.19.x version of tk-core, "
            "which is not compatible with Python 3.\n"
            "Please upgrade your site configuration's tk-core to v0.19.5 or greater.",
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


class EngineNotCompatibleWithDesktop16(ShotgunDesktopError):
    def __init__(self, app_version):
        super().__init__(
            "Your version of tk-desktop is not compatible with this PTR desktop app {}.\n"
            "\n"
            "Please upgrade your site configuration's tk-desktop to v2.5.9+ or "
            "download PTR desktop app 1.5.9 or earlier <a href='{}'>here</a>".format(
                app_version,
                "https://community.shotgridsoftware.com/t/a-new-version-of-shotgrid-desktop-has-been-released/13877/99999",
            )
        )
