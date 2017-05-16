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

import tk_framework_desktopserver


def get_logger(debug):
    """
    Configures the logging for the app.

    :param debug: True if debug is needed, False otherwise.

    :returns: The root logger for the app.
    """
    # Make sure logger output goes to stdout
    logger = tk_framework_desktopserver.get_logger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(name)s.%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    return logger
