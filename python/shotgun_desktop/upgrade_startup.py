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
from shotgun_desktop.location import write_location, get_startup_descriptor
from shotgun_desktop.desktop_message_box import DesktopMessageBox
from sgtk.descriptor import CheckVersionConstraintsError

from sgtk import LogManager

logger = LogManager.get_logger(__name__)


def _supports_get_from_location_and_paths(sgtk):
    """
    Tests if the descriptor factory in core supports non-pipeline configuration based
    setups.

    :param sgtk: The Toolkit API handle.

    :returns: True if the sgtk.deploy.descriptor.get_from_location_and_paths is available,
        False otherwise.
    """
    return hasattr(sgtk.deploy.descriptor, "get_from_location_and_paths")


def _out_of_date_check(latest_descriptor, current_desc):
    """
    Check if the version is out of date, this prevents an upgrade of the startup logic
    in the event that it detects PTR desktop app is running on Python 2.

    :param latest_descriptor:`sgtk.descriptor.FrameworkDescriptor` instance with the latest startup descriptor.
    :param current_desc:`sgtk.descriptor.FrameworkDescriptor` instance with the current startup descriptor.

    :returns: True if the startup version is outdated in comparison with the latest available version on the
              appstore. False otherwise.
    """

    # If we're running in Python 2 and if the bundled framework exists on disk,
    # returns False to avoid upgrade the startup logic.
    if sys.version_info[0] < 3 and os.path.exists(current_desc.get_path()):
        logger.debug(
            "Using Python version '%s'"
            % ".".join(str(i) for i in sys.version_info[0:3])
        )
        logger.debug(
            "Desktop startup is Currently running version %s"
            % current_desc.get_version(),
        )
        return False
    return latest_descriptor.get_version() != current_desc.get_version()


def upgrade_startup(splash, sgtk, app_bootstrap):
    """
    Tries to upgrade the startup logic. If an update is available, it will be donwloaded to the
    local cache directory and the startup descriptor will be updated.

    :param app_bootstrap: Application bootstrap instance, used to update the startup descriptor.

    :returns: True if an update was downloaded and the descriptor updated, False otherwise.
    """

    # It is possible to launch the app with a version of core
    # that doesn't support the functionality needed to update
    # the startup code.
    if not _supports_get_from_location_and_paths(sgtk):
        return False

    sg = sgtk.get_authenticated_user().create_sg_connection()

    current_desc = get_startup_descriptor(sgtk, sg, app_bootstrap)

    logger.debug("Testing for remote access: %s", current_desc)

    if not current_desc.has_remote_access():
        logger.info("Could not update %r: remote access not available.", current_desc)
        return False

    # A Dev descriptor means there is nothing to update. Do not print out
    # "Getting Flow Production Tracking updates...", but keep going nonetheless, as it allows
    # to stress the code even in dev mode. Calls to download will be noops anyway.
    if current_desc.is_dev():
        logger.info("Desktop startup using a dev descriptor, skipping update...")
        return False
    else:
        splash.set_message("Getting Flow Production Tracking updates...")
        logger.info("Getting Flow Production Tracking updates...")

    try:
        latest_descriptor = current_desc.find_latest_version()
    except Exception as e:
        logger.exception("Could not access the TK App Store (tank.shotgunstudio.com):")
        return False

    # check deprecation
    (is_dep, dep_msg) = latest_descriptor.get_deprecation_status()

    if is_dep:
        logger.warning(
            "This version of tk-framework-desktopstartup has been flagged as deprecated with the "
            "following status: %s" % dep_msg
        )
        return False

    # out of date check
    out_of_date = _out_of_date_check(latest_descriptor, current_desc)
    logger.debug("version is out of date: %s", out_of_date)
    if not out_of_date:
        logger.debug(
            "Desktop startup is up to date. Currently running version %s"
            % current_desc.get_version()
        )
        return False

    # Check constraints.
    try:
        latest_descriptor.check_version_constraints(
            desktop_version=app_bootstrap.get_version()
        )
    except CheckVersionConstraintsError as e:
        logger.warning(
            "Cannot upgrade to the latest Desktop Startup %s. %s",
            latest_descriptor.version,
            e,
        )
        return False

    try:
        # Download the update
        latest_descriptor.download_local()

        # create required shotgun fields
        latest_descriptor.ensure_shotgun_fields_exist()

        # run post install hook
        latest_descriptor.run_post_install()

        # write the descriptor location
        write_location(latest_descriptor)

        # update the startup so next restart we start with the just downloaded code.
        app_bootstrap.update_startup(latest_descriptor)
        return True
    except Exception as e:
        splash.hide()
        # If there is an error updating, don't prevent the user from running the app, but let them
        # know something wrong is going on.
        logger.exception("Unexpected error when updating startup code.")
        DesktopMessageBox.critical(
            "Flow Production Tracking update failed",
            "There is a new update of the Flow Production Tracking, but it couldn't be installed. Flow Production Tracking "
            "Desktop will be launched with the currently installed version of the code.\n"
            "If this problem persists, please <a href='%s'>contact</a> Flow Production Tracking support.\n"
            "\n"
            "Error: %s" % (sgtk.support_url, str(e)),
        )
        splash.show()
        return False
