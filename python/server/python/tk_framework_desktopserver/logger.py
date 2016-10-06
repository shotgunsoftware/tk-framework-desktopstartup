# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import logging


def get_logger(child_logger=None):
    """
    Returns the logger used by this framework.
    """
    # Follow 0.18 naming convention so the logging is picked up automatically by the new framework.
    # Note that Toolkit is not available during startup of the Desktop 1.x so we can't rely on the API
    # to build a proper logger name.
    if not child_logger:
        return logging.getLogger("sgtk.ext.tk-framework-desktopserver")
    else:
        return logging.getLogger("sgtk.ext.tk-framework-desktopserver.%s" % child_logger)
