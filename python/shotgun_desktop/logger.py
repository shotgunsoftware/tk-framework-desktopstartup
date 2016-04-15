# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


import logging

def get_logger(name=None):
    """
    Returns a logger named after the name parameter.

    :param name: name of the logger. Can be None.

    :returns: A Python logger named tk-desktop.<name>
    """
    if name:
        return logging.getLogger("tk-desktop.%s" % name)
    else:
        return logging.getLogger("tk-desktop")
