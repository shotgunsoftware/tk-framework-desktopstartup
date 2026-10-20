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
Compatibility checks between the PTR desktop app and the tk-core and tk-desktop
versions picked by the site configuration.

The site configuration can point to any version of tk-core and tk-desktop, including
versions that can't run with the Python and Qt shipped with this app. These checks
turn those failures into an error message telling the user what to upgrade, instead
of a generic crash.

The intended behavior, and why, is specified in tests/test_compatibility.py.
"""

import logging
import os
import sys

import tank
from tank.util.version import is_version_older

from shotgun_desktop.errors import (
    CoreNotCompatibleWithDesktop,
    EngineNotCompatibleWithDesktop,
    ShotgunDesktopError,
)

logger = logging.getLogger("tk-desktop.startup")

ENGINE_NAME = "tk-desktop"

# First tk-desktop release supporting Python 3 and PySide2. Older releases don't
# declare any constraint in their info.yml, so we have to check for them explicitly.
MINIMUM_ENGINE_VERSION = "v2.5.4"

UPGRADE_ENGINE = (
    "Please upgrade your site configuration's tk-desktop to the latest version."
)
UPGRADE_CORE = "Please upgrade your site configuration's tk-core to the latest version."
UPGRADE_DESKTOP = (
    "Please install the latest PTR desktop app, see the "
    "<a href='https://community.shotgridsoftware.com/t/a-new-version-of-shotgrid-desktop-has-been-released/13877'>"
    "release announcements</a>."
)
UPGRADE_LISTED = (
    "Please upgrade what is listed above, or use a version of tk-desktop compatible "
    "with it."
)


def _normalize(path):
    """
    :returns: The path, absolute and normalized for comparisons.
    """
    return os.path.normcase(os.path.abspath(path))


def _folder(*parts):
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

# Root folder of the tk-desktop engine about to be started, once known.
_engine_root = None


def _get_python_version():
    """
    :returns: The running Python version, e.g. "3.11.9".
    """
    return "{}.{}.{}".format(*sys.version_info[:3])


def ensure_engine_compatible_with_desktop(ctx, app_version):
    """
    Make sure the tk-desktop engine of the site configuration can run in this
    PTR desktop app, before its code gets imported.

    This is meant to be called from a bootstrap ``pre_engine_start_callback``, so
    after the site configuration's tk-core has been swapped in.

    :param ctx: Context the engine is about to be started in.
    :type ctx: :class:`sgtk.Context`
    :param str app_version: Version of the PTR desktop app.

    :raises EngineNotCompatibleWithDesktop: If the engine is not compatible.
    """
    global _engine_root
    try:
        # Import from the swapped tk-core, not the bundled one.
        from tank.platform.engine import get_environment_from_context

        env = get_environment_from_context(ctx.sgtk, ctx)
        descriptor = env.get_engine_descriptor(ENGINE_NAME)
        _engine_root = _folder(_normalize(descriptor.get_path()))
        check_engine_descriptor(descriptor, app_version)
    except EngineNotCompatibleWithDesktop:
        raise
    except Exception:
        # The checks must never prevent the app from starting.
        logger.warning(
            "Unable to check the %s engine compatibility, skipping.",
            ENGINE_NAME,
            exc_info=True,
        )


def check_engine_descriptor(descriptor, app_version):
    """
    Check the tk-desktop engine's version and the constraints declared in its info.yml
    (requires_core_version, requires_desktop_version and minimum_python_version)
    against what is currently running.

    :param descriptor: Descriptor of the tk-desktop engine.
    :type descriptor: :class:`sgtk.descriptor.EngineDescriptor`
    :param str app_version: Version of the PTR desktop app.

    :raises EngineNotCompatibleWithDesktop: If the engine is not compatible.
    """
    if descriptor.version.lower() != "undefined" and is_version_older(
        descriptor.version, MINIMUM_ENGINE_VERSION
    ):
        raise EngineNotCompatibleWithDesktop(
            app_version,
            "tk-desktop {} or later is required, found {}. {}".format(
                MINIMUM_ENGINE_VERSION, descriptor.version, UPGRADE_ENGINE
            ),
        )

    # Import from the swapped tk-core, so we catch the error class it raises.
    from tank.descriptor import CheckVersionConstraintsError

    try:
        descriptor.check_version_constraints(desktop_version=app_version)
    except CheckVersionConstraintsError as e:
        raise EngineNotCompatibleWithDesktop(
            app_version, "{} {}".format(e, UPGRADE_LISTED)
        )

    minimum_python_version = descriptor._get_manifest().get("minimum_python_version")
    if minimum_python_version and is_version_older(
        _get_python_version(), str(minimum_python_version)
    ):
        raise EngineNotCompatibleWithDesktop(
            app_version,
            "Requires at least Python {} but currently running {}. {}".format(
                minimum_python_version, _get_python_version(), UPGRADE_DESKTOP
            ),
        )


def get_incompatible_code_error(error, app_version):
    """
    Check if an error raised while bootstrapping looks like site configuration code
    that can't run with this version of Python, like syntax that is no longer
    supported or a module removed from the standard library.

    This is a heuristic. A genuine bug in tk-core or tk-desktop will be reported the
    same way, which is acceptable for released code.

    :param error: Exception raised while bootstrapping.
    :param str app_version: Version of the PTR desktop app.

    :returns: An error to show to the user, or None if the error is not recognized.
    :rtype: :class:`~shotgun_desktop.errors.ShotgunDesktopError`
    """
    # tk-core wraps errors raised while loading the engine, e.g. in a
    # TankLoadPluginError, so look for the original error.
    seen = set()
    while error is not None and id(error) not in seen:
        if isinstance(error, ShotgunDesktopError):
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
    if (_engine_root and path.startswith(_engine_root)) or _ENGINE_FOLDER in path:
        return EngineNotCompatibleWithDesktop(
            app_version, "{}. {}".format(error, UPGRADE_ENGINE)
        )
    if path.startswith(_BUNDLED_CORE_PATH):
        return None
    if any(folder in path for folder in _CORE_FOLDERS):
        return CoreNotCompatibleWithDesktop(
            app_version, "{}. {}".format(error, UPGRADE_CORE)
        )
    return None
