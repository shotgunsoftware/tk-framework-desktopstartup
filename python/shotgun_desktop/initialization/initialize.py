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
import tempfile

from . import install
from . import shotgun
from .. import paths
from .. logger import get_logger


def initialize(splash, connection, app_store_http_proxy):
    """ initialize toolkit for this computer for a single site """
    logger = get_logger("initialization")

    # grab the paths that will be used during the install
    temp_dir = tempfile.mkdtemp(prefix="tk-desktop")
    temp_site_root = os.path.join(temp_dir, "site")

    logger.debug("temp site install: %s", temp_site_root)
    splash.show()
    splash.set_message("Getting site details...")

    if shotgun.is_script_user_required(connection):
        # get the toolkit script to connect as
        toolkit_script = shotgun.get_or_create_script(connection)
        if toolkit_script is None:
            raise RuntimeError("did not get toolkit script")
    else:
        toolkit_script = None

    # Compute the proxy that needs to be used to access the App Store.
    actual_app_store_proxy = shotgun.get_app_store_http_proxy(connection, app_store_http_proxy)

    # grab the login to the app store
    app_store_script = shotgun.get_app_store_credentials(connection, actual_app_store_proxy)
    if app_store_script is None:
        raise RuntimeError("did not get app store script")

    # translate platform for locations and executables
    if sys.platform == "darwin":
        current_plat_name = "Darwin"
    elif sys.platform == "win32":
        current_plat_name = "Windows"
    elif sys.platform.startswith("linux"):
        current_plat_name = "Linux"
    else:
        raise RuntimeError("unknown platform: %s" % sys.platform)

    locations = {
        "Darwin": "",
        "Windows": "",
        "Linux": "",
    }
    locations[current_plat_name] = temp_site_root

    executables = {
        "Darwin": "/Applications/Shotgun.app/Contents/Resources/Python/bin/python",
        "Windows": "C:\\Program Files\\Shotgun\\Python\\python.exe",
        "Linux": "/opt/Shotgun/Python/bin/python",
    }
    executables[current_plat_name] = paths.get_python_path()

    # have all info, pass it to the installer thread
    splash.details = "Installing Toolkit core..."
    installer = install.InstallThread()
    installer.set_install_folder(temp_site_root)
    installer.set_shotgun_info(
        connection,
        toolkit_script
    )
    installer.set_app_store_info(
        app_store_script["firstname"],
        app_store_script["salted_password"],
        app_store_script,
        actual_app_store_proxy,
        app_store_http_proxy
    )
    installer.set_locations(locations)
    installer.set_executables(executables)

    # run the thread
    logger.debug("starting installer")
    installer.start()
    installer.wait()

    return temp_site_root
