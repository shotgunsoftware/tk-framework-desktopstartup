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
Specification of how the PTR desktop app handles a site configuration whose tk-core
or tk-desktop can't run with the Python and Qt it ships.

Context:

- The PTR desktop app itself only runs a tk-framework-desktopstartup that is
  compatible with it. This is enforced by requires_desktop_version,
  requires_core_version and minimum_python_version in this framework's info.yml,
  when upgrading the framework.
- This framework then bootstraps into the site configuration, which can use any
  tk-core and tk-desktop version, including very old ones.
- The PTR desktop app is a UI application. When something is not compatible, the
  user must get a message telling them what to upgrade, not a crash or a stack trace.

Intentions:

1. Before importing tk-desktop, check what it declares in its info.yml against what
   is running: requires_core_version, requires_desktop_version and
   minimum_python_version. This is the generic mechanism: new constraints only need
   to be declared in tk-desktop's info.yml.
2. tk-desktop releases older than MINIMUM_ENGINE_VERSION predate Python 3 and
   PySide2 support and don't declare any constraint, so they are rejected explicitly.
   This replaces the historical tk-desktop v2.5.0 checks.
3. When the bootstrap fails with a SyntaxError (syntax no longer supported) or an
   ImportError (module removed from the standard library, e.g. Cookie, imp or
   distutils), tell the user whether the site configuration's tk-desktop or tk-core
   is the culprit, based on the file the error comes from. This keeps working as
   Python versions are dropped and added every year, without listing them. tk-core
   wraps errors raised while loading the engine, so the original error is used.
4. Errors coming from the tk-core bundled with this framework are not blamed on the
   site configuration: that core is known to be compatible.
5. The checks must never be the reason the PTR desktop app fails to start. If a check
   can't run, e.g. a core without the expected API, log it and let the bootstrap
   continue.
6. The message tells the user what to upgrade: tk-desktop, tk-core or the PTR
   desktop app itself, depending on what failed.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "python/tk-core/python")
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from shotgun_desktop import compatibility
from shotgun_desktop.errors import (
    CoreNotCompatibleWithDesktop,
    EngineNotCompatibleWithDesktop,
    ShotgunDesktopError,
)
from tank.descriptor import CheckVersionConstraintsError
from tank.util.loader import load_plugin

APP_VERSION = "v1.8.0"

ENGINE_ROOT = os.path.join(os.sep, "bundle_cache", "tk-desktop", "v2.9.0")
SITE_ENGINE_FILE = os.path.join(ENGINE_ROOT, "python", "tk_desktop", "site.py")
SITE_ENGINE_ENTRY_POINT = os.path.join(ENGINE_ROOT, "engine.py")
SITE_CORE_PYTHON = os.path.join(os.sep, "site_config", "install", "core", "python")
SITE_CORE_FILE = os.path.join(SITE_CORE_PYTHON, "tank", "__init__.py")
SITE_CORE_VENDOR_FILE = os.path.join(SITE_CORE_PYTHON, "tank_vendor", "lib.py")
BUNDLED_CORE_FILE = os.path.join(compatibility._BUNDLED_CORE_PATH, "tank", "x.py")
BUNDLED_CORE_VENDOR_FILE = os.path.join(
    compatibility._BUNDLED_CORE_PATH, "tank_vendor", "lib.py"
)
OTHER_FILE = os.path.join(os.sep, "somewhere", "else.py")


@pytest.fixture(autouse=True)
def engine_root():
    """The engine root is known once its compatibility has been checked."""
    compatibility._engine_root = compatibility._folder(
        compatibility._normalize(ENGINE_ROOT)
    )
    yield
    compatibility._engine_root = None


class MockDescriptor:
    """Mock a tk-desktop engine descriptor."""

    def __init__(self, version="v2.9.0", constraints_error=None, manifest=None):
        self.version = version
        self._constraints_error = constraints_error
        self._manifest = manifest or {}

    def get_path(self):
        return ENGINE_ROOT

    def check_version_constraints(self, desktop_version=None):
        if self._constraints_error:
            raise self._constraints_error

    def _get_manifest(self):
        return self._manifest


def _raise_from(code, filename):
    """
    Run the code as if it was located in the given file.

    :returns: The raised exception.
    """
    try:
        exec(compile(code, filename, "exec"), {})
    except Exception as e:
        return e
    raise AssertionError("The code didn't raise.")


def _ensure_compatible(descriptor):
    """Run the checks the way the bootstrap does, for the given descriptor."""
    env = MagicMock()
    env.get_engine_descriptor.return_value = descriptor
    with patch("tank.platform.engine.get_environment_from_context", return_value=env):
        compatibility.ensure_engine_compatible_with_desktop(MagicMock(), APP_VERSION)
    env.get_engine_descriptor.assert_called_once_with("tk-desktop")


# Intention 1: constraints declared in tk-desktop's info.yml.


def test_engine_version_constraints_not_met():
    """
    The requires_*_version constraints of tk-desktop are enforced, and tk-core's
    explanation is shown to the user so they know what to upgrade.
    """
    reason = (
        "Requires at least Core API v0.20.0 but currently installed version is v0.19.5."
    )
    descriptor = MockDescriptor(
        constraints_error=CheckVersionConstraintsError([reason])
    )
    with pytest.raises(EngineNotCompatibleWithDesktop) as e:
        _ensure_compatible(descriptor)
    assert reason in str(e.value)
    assert compatibility.UPGRADE_LISTED in str(e.value)


def test_engine_minimum_python_version_met():
    """
    A tk-desktop declaring a minimum_python_version older than or equal to the
    running Python starts normally.
    """
    _ensure_compatible(MockDescriptor(manifest={"minimum_python_version": "3.9"}))


def test_engine_minimum_python_version_not_met():
    """
    A tk-desktop requiring a newer Python than the one shipped with this PTR desktop
    app is rejected. This happens when a site configuration is upgraded to a
    tk-desktop dropping a Python version while users still run an older PTR desktop
    app, which is what they need to upgrade.
    """
    descriptor = MockDescriptor(manifest={"minimum_python_version": "99.0"})
    with pytest.raises(EngineNotCompatibleWithDesktop) as e:
        _ensure_compatible(descriptor)
    assert "Requires at least Python 99.0" in str(e.value)
    assert compatibility.UPGRADE_DESKTOP in str(e.value)


# Intention 2: hardcoded minimum for releases that don't declare constraints.


@pytest.mark.parametrize("version", ["v2.5.4", "v2.9.0"])
def test_compatible_engine(version):
    """tk-desktop releases supporting Python 3 and PySide2 start normally."""
    _ensure_compatible(MockDescriptor(version))


@pytest.mark.parametrize("version", ["Undefined", "HEAD"])
def test_engine_without_version(version):
    """
    Dev descriptors and git branches have no comparable version. Assume they are
    compatible: they are used by developers who know what they run.
    """
    _ensure_compatible(MockDescriptor(version))


@pytest.mark.parametrize("version", ["v2.4.12", "v2.5.0", "v2.5.3"])
def test_engine_older_than_minimum(version):
    """
    tk-desktop releases predating Python 3 support are rejected with a message
    giving the required and found versions.
    """
    with pytest.raises(EngineNotCompatibleWithDesktop) as e:
        _ensure_compatible(MockDescriptor(version))
    assert compatibility.MINIMUM_ENGINE_VERSION in str(e.value)
    assert version in str(e.value)
    assert compatibility.UPGRADE_ENGINE in str(e.value)


# Intentions 3 and 4: code that can't run with this version of Python.


@pytest.mark.parametrize(
    "filename,expected",
    [
        (SITE_ENGINE_FILE, EngineNotCompatibleWithDesktop),
        (SITE_ENGINE_ENTRY_POINT, EngineNotCompatibleWithDesktop),
        (SITE_CORE_FILE, CoreNotCompatibleWithDesktop),
        (SITE_CORE_VENDOR_FILE, CoreNotCompatibleWithDesktop),
        (BUNDLED_CORE_FILE, None),
        (BUNDLED_CORE_VENDOR_FILE, None),
        (OTHER_FILE, None),
    ],
)
def test_incompatible_syntax(filename, expected):
    """
    Syntax no longer supported by Python is blamed on the site configuration's
    tk-desktop or tk-core, based on the file containing it. The traceback of a
    SyntaxError points to the code importing the module, so it is not used.
    """
    error = _raise_from("print 'Python 2'", filename)
    assert isinstance(error, SyntaxError)

    result = compatibility.get_incompatible_code_error(error, APP_VERSION)
    if expected is None:
        assert result is None
    else:
        assert isinstance(result, expected)
        assert str(error) in str(result)


@pytest.mark.parametrize(
    "filename,expected",
    [
        (SITE_ENGINE_FILE, EngineNotCompatibleWithDesktop),
        (SITE_ENGINE_ENTRY_POINT, EngineNotCompatibleWithDesktop),
        (SITE_CORE_FILE, CoreNotCompatibleWithDesktop),
        (SITE_CORE_VENDOR_FILE, CoreNotCompatibleWithDesktop),
        (BUNDLED_CORE_FILE, None),
        (BUNDLED_CORE_VENDOR_FILE, None),
        (OTHER_FILE, None),
    ],
)
def test_removed_module(filename, expected):
    """
    Importing a module removed from the standard library is blamed on the site
    configuration's tk-desktop or tk-core, based on the file importing it.
    """
    error = _raise_from("import Cookie", filename)
    assert isinstance(error, ImportError)

    result = compatibility.get_incompatible_code_error(error, APP_VERSION)
    if expected is None:
        assert result is None
    else:
        assert isinstance(result, expected)
        assert "Cookie" in str(result)


@pytest.mark.parametrize("code", ["print 'Python 2'", "import Cookie"])
def test_engine_load_error_wrapped_by_core(tmp_path, code):
    """
    tk-core loads the engine's entry point with load_plugin(), which wraps any error
    in a TankLoadPluginError. The original error is the one to classify.
    """
    engine_root = tmp_path / "tk-desktop" / "v2.9.0"
    engine_root.mkdir(parents=True)
    entry_point = engine_root / "engine.py"
    entry_point.write_text(code)
    compatibility._engine_root = compatibility._folder(
        compatibility._normalize(str(engine_root))
    )

    with pytest.raises(Exception) as e:
        load_plugin(str(entry_point), object)
    assert type(e.value).__name__ == "TankLoadPluginError"

    result = compatibility.get_incompatible_code_error(e.value, APP_VERSION)
    assert isinstance(result, EngineNotCompatibleWithDesktop)
    assert compatibility.UPGRADE_ENGINE in str(result)


def test_other_errors_not_reported():
    """
    Other errors are genuine bugs, not incompatibilities, and are reported as is.
    """
    error = _raise_from("1 / 0", SITE_ENGINE_FILE)
    assert compatibility.get_incompatible_code_error(error, APP_VERSION) is None


def test_desktop_errors_not_reported():
    """
    Errors already meant for the user, e.g. raised by the checks before the engine
    starts, are shown as is even if they happened while handling an import error.
    """
    try:
        try:
            raise ImportError("No module named 'Cookie'")
        except ImportError:
            raise ShotgunDesktopError("Invalid pipeline configuration.")
    except ShotgunDesktopError as e:
        error = e
    assert compatibility.get_incompatible_code_error(error, APP_VERSION) is None


# Intention 5: checks never prevent the PTR desktop app from starting.


def test_ensure_engine_compatible_cant_resolve_descriptor():
    """
    If the tk-desktop descriptor can't be resolved, skip the checks and let the
    bootstrap report its own, more accurate, error.
    """
    with patch(
        "tank.platform.engine.get_environment_from_context",
        side_effect=Exception("No environment"),
    ):
        compatibility.ensure_engine_compatible_with_desktop(MagicMock(), APP_VERSION)


@pytest.mark.parametrize(
    "descriptor",
    [
        # The version can't be compared.
        MockDescriptor(version=None),
        # The site configuration's tk-core API is different.
        MockDescriptor(constraints_error=TypeError("unexpected argument")),
    ],
)
def test_engine_check_fails(descriptor):
    """If a check fails unexpectedly, skip the checks."""
    _ensure_compatible(descriptor)


def test_engine_manifest_unreadable():
    """If the tk-desktop manifest can't be read, skip the Python version check."""
    descriptor = MockDescriptor()
    descriptor._get_manifest = MagicMock(side_effect=Exception("No manifest"))
    _ensure_compatible(descriptor)


# Intention 6: user facing messages.


@pytest.mark.parametrize(
    "error_class,component",
    [
        (EngineNotCompatibleWithDesktop, "tk-desktop engine"),
        (CoreNotCompatibleWithDesktop, "tk-core"),
    ],
)
def test_error_message(error_class, component):
    """
    Messages say which component of the site configuration is not compatible, and
    give the PTR desktop app and Python versions and the reason, so support can
    diagnose the issue from a screenshot.
    """
    message = str(error_class(APP_VERSION, "Some reason."))
    assert "The {} of your site configuration".format(component) in message
    assert "PTR desktop app {}".format(APP_VERSION) in message
    assert "Python {}.{}".format(*sys.version_info[:2]) in message
    assert "Some reason." in message


@pytest.mark.parametrize(
    "filename,advice",
    [
        (SITE_ENGINE_FILE, compatibility.UPGRADE_ENGINE),
        (SITE_CORE_FILE, compatibility.UPGRADE_CORE),
    ],
)
def test_incompatible_code_advice(filename, advice):
    """Code that can't run asks to upgrade the component it belongs to."""
    error = _raise_from("import Cookie", filename)
    result = compatibility.get_incompatible_code_error(error, APP_VERSION)
    assert advice in str(result)
