# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from __future__ import absolute_import

import os
import sys
import logging
import traceback
import logging.handlers

__LOGGING_INITIALIZED = False
__LOGGER = None
__HANDLER = None


def initialize_logging():
    global __LOGGER
    global __HANDLER
    global __LOGGING_INITIALIZED

    if __LOGGING_INITIALIZED:
        return

    __LOGGING_INITIALIZED = True

    # platform specific locations for the log file
    if sys.platform == "darwin":
        fname = os.path.join(os.path.expanduser("~"), "Library", "Logs", "Shotgun", "tk-desktop.log")
    elif sys.platform == "win32":
        fname = os.path.join(os.environ.get("APPDATA", "APPDATA_NOT_SET"), "Shotgun", "tk-desktop.log")
    elif sys.platform.startswith("linux"):
        fname = os.path.join(os.path.expanduser("~"), ".shotgun", "logs", "tk-desktop.log")
    else:
        raise NotImplementedError("Unknown platform: %s" % sys.platform)

    # create the directory for the log file
    log_dir = os.path.dirname(fname)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # setup default logger, used in the new default exception hook
    __LOGGER = logging.getLogger("tk-desktop")
    __HANDLER = logging.handlers.RotatingFileHandler(fname, maxBytes=1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    __HANDLER.setFormatter(formatter)
    __LOGGER.addHandler(__HANDLER)

    # for the time being, keep debug logging on all the time
    # later on, we can add a command line option (--debug) or
    # environment variable to make it easy to turn on debug only
    # when needed.
    __LOGGER.setLevel(logging.DEBUG)

    # setup basic exception hook
    class _TopLevelExceptionHandler(object):
        def __init__(self):
            # save old hook
            self._current_hook = sys.excepthook

        def _handle(self, etype, evalue, etb):
            # call the original hook
            if self._current_hook:
                self._current_hook(etype, evalue, etb)

            # log the exception
            lines = traceback.format_exception(etype, evalue, etb)
            lines.insert(0, lines.pop())
            logging.getLogger("tk-desktop").error("\n".join(lines))
    sys.excepthook = _TopLevelExceptionHandler()._handle


def tear_down_logging():
    global __LOGGER
    global __HANDLER
    global __LOGGING_INITIALIZED

    if not __LOGGING_INITIALIZED:
        return

    __LOGGING_INITIALIZED = False

    __LOGGER.removeHandler(__HANDLER)
    __HANDLER = None
    __LOGGER = None
