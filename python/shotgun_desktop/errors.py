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


class EngineNotCompatibleWithDesktop(ShotgunDesktopError):
    """
    This exception notifies the catcher that the site's desktop engine can't run in
    this version of the Desktop installer.
    """

    def __init__(self, app_version, reason):
        """
        Constructor

        :param str app_version: Version of the PTR desktop app.
        :param str reason: Why the engine is not compatible.
        """
        super().__init__(
            "The tk-desktop engine of your site configuration is not compatible with "
            "this PTR desktop app {} running Python {}.{}.\n"
            "\n"
            "{}\n"
            "\n"
            "Please upgrade your site configuration's tk-desktop to the latest version. "
            "See the <a href='{}'>release announcements</a> for more information.".format(
                app_version,
                sys.version_info[0],
                sys.version_info[1],
                reason,
                "https://community.shotgridsoftware.com/t/a-new-version-of-shotgrid-desktop-has-been-released/13877",
            )
        )


class CoreNotCompatibleWithDesktop(ShotgunDesktopError):
    """
    This exception notifies the catcher that the site's core can't run in this
    version of the Desktop installer.
    """

    def __init__(self, app_version, reason):
        """
        Constructor

        :param str app_version: Version of the PTR desktop app.
        :param str reason: Why the core is not compatible.
        """
        super().__init__(
            "The tk-core of your site configuration is not compatible with "
            "this PTR desktop app {} running Python {}.{}.\n"
            "\n"
            "{}\n"
            "\n"
            "Please upgrade your site configuration's tk-core to the latest version.".format(
                app_version,
                sys.version_info[0],
                sys.version_info[1],
                reason,
            )
        )
