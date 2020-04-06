# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from shotgun_desktop.location import write_location, get_startup_descriptor
from shotgun_desktop.desktop_message_box import DesktopMessageBox
from sgtk.descriptor import CheckVersionConstraintsError

from sgtk import LogManager

logger = LogManager.get_logger(__name__)

from distutils.version import LooseVersion


def _get_server_version(connection):
    """
    Retrieves the server version from the connection.

    :param connection: Connection we want the server version from.

    :returns: Tuple of (major, minor) versions.
    """
    sg_major_ver = connection.server_info["version"][0]
    sg_minor_ver = connection.server_info["version"][1]
    sg_patch_ver = connection.server_info["version"][2]

    return LooseVersion("%d.%d.%d" % (sg_major_ver, sg_minor_ver, sg_patch_ver))


def _supports_get_from_location_and_paths(sgtk):
    """
    Tests if the descriptor factory in core supports non-pipeline configuration based
    setups.

    :param sgtk: The Toolkit API handle.

    :returns: True if the sgtk.deploy.descriptor.get_from_location_and_paths is available,
        False otherwise.
    """
    return hasattr(sgtk.deploy.descriptor, "get_from_location_and_paths")


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
    # "Getting Shotgun Desktop updates...", but keep going nonetheless, as it allows
    # to stress the code even in dev mode. Calls to download will be noops anyway.
    if current_desc.is_dev():
        logger.info("Desktop startup using a dev descriptor, skipping update...")
        return False
    else:
        splash.set_message("Getting Shotgun Desktop updates...")
        logger.info("Getting Shotgun Desktop updates...")

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
    out_of_date = latest_descriptor.get_version() != current_desc.get_version()

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
            "Shotgun Desktop update failed",
            "There is a new update of the Shotgun Desktop, but it couldn't be installed. Shotgun "
            "Desktop will be launched with the currently installed version of the code.\n"
            "If this problem persists, please contact Shotgun support at "
            "support@shotgunsoftware.com.\n"
            "Error: %s" % str(e),
        )
        splash.show()
        return False
