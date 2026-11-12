# Copyright (c) 2026 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Detect site configuration code that can't run with the Python shipped with the PTR
desktop app.

The site configuration can point to any version of tk-core and tk-desktop, including
versions that can't run with the Python shipped with this app. When bootstrapping
fails because of that, this turns the failure into an error message telling the user
what to upgrade, instead of a generic crash.

The intended behavior, and why, is specified in tests/test_compatibility.py.
"""

import logging
import os
from typing import Optional

import tank

from . import errors

logger = logging.getLogger("tk-desktop.startup")

UPGRADE_ENGINE = (
    "Please upgrade your site configuration's tk-desktop to the latest version."
)
UPGRADE_CORE = "Please upgrade your site configuration's tk-core to the latest version."


def _normalize(path: str) -> str:
    """
    :returns: The path, absolute and normalized for comparisons.
    """
    return os.path.normcase(os.path.abspath(path))


def _folder(*parts: str) -> str:
    """
    :returns: The folder path, normalized and with a trailing separator.
    """
    return os.path.normcase(os.path.join(*parts, ""))


_ENGINE_FOLDER = _folder("python", "tk_desktop")
_CORE_FOLDERS = [_folder("python", "tank"), _folder("python", "tank_vendor")]
# Python folder of the tk-core bundled with this framework, known to be compatible.
_BUNDLED_CORE_PATH = _folder(
    _normalize(os.path.dirname(os.path.dirname(tank.__file__)))
)


def get_incompatible_code_error(
    error: BaseException, app_version: str
) -> Optional[errors.ShotgunDesktopError]:
    """
    Check if an error raised while bootstrapping looks like site configuration code
    that can't run with this version of Python, like syntax that is no longer
    supported or a module removed from the standard library.

    This is a heuristic. A genuine bug in tk-core or tk-desktop will be reported the
    same way, which is acceptable for released code. It never raises: if the error
    can't be classified, it is logged and None is returned, so the original error is
    reported.

    :param error: Exception raised while bootstrapping.
    :param app_version: Version of the PTR desktop app.

    :returns: An error to show to the user, or None if the error is not recognized.
    """
    try:
        return _classify(error, app_version)
    except Exception:
        logger.warning("Unable to classify the bootstrap error.", exc_info=True)
        return None


def _classify(
    error: Optional[BaseException], app_version: str
) -> Optional[errors.ShotgunDesktopError]:
    """
    Implementation of :func:`get_incompatible_code_error`, which may raise.
    """
    # tk-core wraps errors raised while loading the engine, e.g. in a
    # TankLoadPluginError, so look for the original error.
    seen = set()
    while error is not None and id(error) not in seen:
        if isinstance(error, errors.ShotgunDesktopError):
            # Already a message for the user.
            return None
        if isinstance(error, (SyntaxError, ImportError)):
            break
        seen.add(id(error))
        error = error.__cause__ or error.__context__
    else:
        return None

    # For a SyntaxError, the traceback points at the code importing the module, not
    # at the module itself.
    filename = error.filename if isinstance(error, SyntaxError) else None
    error_traceback = error.__traceback__
    if not filename and error_traceback:
        while error_traceback.tb_next:
            error_traceback = error_traceback.tb_next
        filename = error_traceback.tb_frame.f_code.co_filename
    if not filename:
        return None

    path = _normalize(filename)
    if _ENGINE_FOLDER in path:
        return errors.EngineNotCompatibleWithDesktop(
            app_version, "{}. {}".format(error, UPGRADE_ENGINE)
        )
    if path.startswith(_BUNDLED_CORE_PATH):
        return None
    if any(folder in path for folder in _CORE_FOLDERS):
        return errors.CoreNotCompatibleWithDesktop(
            app_version, "{}. {}".format(error, UPGRADE_CORE)
        )
    return None
