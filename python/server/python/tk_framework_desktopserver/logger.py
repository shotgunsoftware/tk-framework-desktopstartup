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
    if not child_logger:
        return logging.getLogger("tk-framework-desktopserver")
    else:
        return logging.getLogger("tk-framework-desktopserver.%s" % child_logger)
