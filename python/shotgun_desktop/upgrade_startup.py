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
import logging
from distutils.version import LooseVersion
from shotgun_desktop.location import get_location, write_location
from shotgun_desktop.desktop_message_box import DesktopMessageBox

import httplib

logger = logging.getLogger("tk-desktop.startup")


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

    current_desc = sgtk.deploy.descriptor.get_from_location_and_paths(
        sgtk.deploy.descriptor.AppDescriptor.FRAMEWORK,
        app_bootstrap.get_shotgun_desktop_cache_location(),
        os.path.join(
            app_bootstrap.get_shotgun_desktop_cache_location(), "install"
        ),
        get_location(sgtk, app_bootstrap)
    )

    # A Dev descriptor means there is nothing to update. Early out so that we don't show
    # "Getting Shotgun Desktop updates...""
    if isinstance(current_desc, sgtk.deploy.dev_descriptor.TankDevDescriptor):
        logger.info("Desktop startup using a dev descriptor, skipping update...")
        return False

    splash.set_message("Getting Shotgun Desktop updates...")
    logger.info("Getting Shotgun Desktop updates...")

    # Some clients block tank.shotgunstudio.com with a proxy. Normally, this isn't an issue
    # because those clients will be using a locked site config, which won't try to connect
    # to tank.shotgunstudio.com. The Desktop startup update code however always phones home.
    # Beacuse of this, we'll try to find the latest version but accept that it may fail.

    # Local import because sgtk can't be imported globally in the desktop startup.
    from tank_vendor.shotgun_api3.lib import httplib2

    # Backwards compatibility for pre-v0.18 versions of the core api that
    # don't contain the descriptor sub-package or associated errors.
    app_store_connection_errors = (httplib2.HttpLib2Error,
                                   httplib2.socks.HTTPError,
                                   httplib.HTTPException)
    try:
        app_store_connection_errors += (sgtk.descriptor.errors.TankAppStoreConnectionError,)
    except AttributeError:
        pass

    try:
        latest_descriptor = current_desc.find_latest_version()
    # Connection errors can occur for a variety of reasons. For example, there is no internet access
    # or there is a proxy server blocking access to the Toolkit app store
    except app_store_connection_errors, e:
        logger.warning("Could not access the TK App Store (tank.shotgunstudio.com): (%s)." % e)
        return False
    # In cases where there is a firewall/proxy blocking access to the app store, sometimes the 
    # firewall will drop the connection instead of rejecting it. The API request will timeout which
    # unfortunately results in a generic SSLError with only the message text to give us a clue why
    # the request failed. Issue a warning in this case and continue on. 
    except httplib2.ssl.SSLError, e:
        if "timed" in e.message:
            logger.warning("Could not access the TK App Store (tank.shotgunstudio.com): %s" % e)
            return False
        else:
            raise

    # check deprecation
    (is_dep, dep_msg) = latest_descriptor.get_deprecation_status()

    if is_dep:
        logger.warning(
            "This version of tk-framework-desktopstartup has been flagged as deprecated with the "
            "following status: %s" % dep_msg
        )
        return False

    # out of date check
    out_of_date = (latest_descriptor.get_version() != current_desc.get_version())

    if not out_of_date:
        logger.debug("Desktop startup does not need upgrading. Currenty running version %s" % current_desc.get_version())
        return False

    if latest_descriptor.get_version_constraints().get("min_desktop"):
        current_desktop_version = LooseVersion(app_bootstrap.get_version())
        minimal_desktop_version = LooseVersion(latest_descriptor.get_version_constraints()["min_desktop"])
        if current_desktop_version < minimal_desktop_version:
            logger.warning(
                "Cannot upgrade to the latest Desktop Startup %s. This version requires %s of the "
                "Shotgun Desktop, but you are currently running %s. Please consider upgrading your "
                "Shotgun Desktop." % (
                    latest_descriptor.get_version(), minimal_desktop_version, current_desktop_version
                )
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
    except Exception, e:
        splash.hide()
        # If there is an error updating, don't prevent the user from running the app, but let them
        # know something wrong is going on.
        logger.exception("Unexpected error when updating startup code.")
        DesktopMessageBox.critical(
            "Desktop update failed",
            "There is a new update of the Shotgun Desktop, but it couldn't be installed. Shotgun "
            "Desktop will be launched with the currently installed version of the code.\n"
            "If this problem persists, please contact Shotgun support at "
            "support@shotgunsoftware.com.\n"
            "Error: %s" % str(e))
        splash.show()
        return False
