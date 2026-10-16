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
Specification of how FlowPT Desktop handles a site configuration whose tk-core or
tk-desktop can't run with the Python and Qt it ships.

Context:

- FlowPT Desktop itself only runs a tk-framework-desktopstartup that is compatible
  with it. This is enforced by requires_desktop_version, requires_core_version and
  minimum_python_version in this framework's info.yml, when upgrading the framework.
- This framework then bootstraps into the site configuration, which can use any
  tk-core and tk-desktop version, including very old ones.
- FlowPT Desktop is a UI application. When something is not compatible, the user must
  get a message telling them what to upgrade, not a crash or a stack trace.

Intentions:

1. Before importing tk-desktop, check what it declares in its info.yml against what
   is running: requires_core_version, requires_desktop_version and
   minimum_python_version. This is the generic mechanism: new constraints only need
   to be declared in tk-desktop's info.yml.
2. tk-desktop releases older than MINIMUM_ENGINE_VERSION predate Python 3 and
   PySide2 support and don't declare any constraint, so they are rejected explicitly.
   This replaces the historical tk-desktop v2.0.0, v2.1.0 and v2.5.0 checks.
3. When the bootstrap fails with a SyntaxError (syntax no longer supported) or an
   ImportError (module removed from the standard library, e.g. Cookie, imp or
   distutils), tell the user whether the site configuration's tk-desktop or tk-core
   is the culprit, based on the file the error comes from. This keeps working as
   Python versions are dropped and added every year, without listing them.
4. Errors coming from the tk-core bundled with this framework are not blamed on the
   site configuration: that core is known to be compatible.
5. The checks must never be the reason FlowPT Desktop fails to start. If a check
   can't run, e.g. a core without the expected API, log it and let the bootstrap
   continue.
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
)
from tank.descriptor import CheckVersionConstraintsError

APP_VERSION = "v1.8.0"

SITE_ENGINE_FILE = os.path.join(
    os.sep, "bundle_cache", "tk-desktop", "v2.0.0", "python", "tk_desktop", "engine.py"
)
SITE_CORE_FILE = os.path.join(
    os.sep, "site_config", "install", "core", "python", "tank", "__init__.py"
)
BUNDLED_CORE_FILE = os.path.join(compatibility._BUNDLED_CORE_PATH, "__init__.py")
OTHER_FILE = os.path.join(os.sep, "somewhere", "else.py")


class MockDescriptor:
    """Mock a tk-desktop engine descriptor."""

    def __init__(self, version="v2.9.0", constraints_error=None, manifest=None):
        self.version = version
        self._constraints_error = constraints_error
        self._manifest = manifest or {}

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


# Intention 1: constraints declared in tk-desktop's info.yml.


def test_engine_version_constraints_not_met():
    """
    The requires_*_version constraints of tk-desktop are enforced, and tk-core's
    explanation is shown to the user so they know what to upgrade.
    """
    reason = "Requires at least FPTR desktop app v9.0.0 but currently installed version is v1.8.0."
    descriptor = MockDescriptor(
        constraints_error=CheckVersionConstraintsError([reason])
    )
    with pytest.raises(EngineNotCompatibleWithDesktop) as e:
        compatibility.check_engine_descriptor(descriptor, APP_VERSION)
    assert reason in str(e.value)


def test_engine_minimum_python_version_met():
    """
    A tk-desktop declaring a minimum_python_version older than or equal to the
    running Python starts normally.
    """
    descriptor = MockDescriptor(manifest={"minimum_python_version": "3.9"})
    compatibility.check_engine_descriptor(descriptor, APP_VERSION)


def test_engine_minimum_python_version_not_met():
    """
    A tk-desktop requiring a newer Python than the one shipped with this FlowPT
    Desktop is rejected. This happens when a site configuration is upgraded to a
    tk-desktop dropping a Python version while users still run an older FlowPT
    Desktop.
    """
    descriptor = MockDescriptor(manifest={"minimum_python_version": "99.0"})
    with pytest.raises(EngineNotCompatibleWithDesktop) as e:
        compatibility.check_engine_descriptor(descriptor, APP_VERSION)
    assert "Requires at least Python 99.0" in str(e.value)


def test_ensure_engine_compatible_resolves_descriptor():
    """
    The checks run on the tk-desktop the site configuration is about to start,
    resolved from the context's environment, before its code is imported.
    """
    env = MagicMock()
    env.get_engine_descriptor.return_value = MockDescriptor("v2.5.0")
    with patch("tank.platform.engine.get_environment_from_context", return_value=env):
        with pytest.raises(EngineNotCompatibleWithDesktop):
            compatibility.ensure_engine_compatible_with_desktop(
                MagicMock(), APP_VERSION
            )
    env.get_engine_descriptor.assert_called_once_with("tk-desktop")


# Intention 2: hardcoded minimum for releases that don't declare constraints.


@pytest.mark.parametrize("version", ["v2.5.4", "v2.9.0"])
def test_compatible_engine(version):
    """tk-desktop releases supporting Python 3 and PySide2 start normally."""
    compatibility.check_engine_descriptor(MockDescriptor(version), APP_VERSION)


@pytest.mark.parametrize("version", ["Undefined", "HEAD"])
def test_engine_without_version(version):
    """
    Dev descriptors and git branches have no comparable version. Assume they are
    compatible: they are used by developers who know what they run.
    """
    compatibility.check_engine_descriptor(MockDescriptor(version), APP_VERSION)


@pytest.mark.parametrize("version", ["v2.4.12", "v2.5.0", "v2.5.3"])
def test_engine_older_than_minimum(version):
    """
    tk-desktop releases predating Python 3 support are rejected with a message
    giving the required and found versions.
    """
    with pytest.raises(EngineNotCompatibleWithDesktop) as e:
        compatibility.check_engine_descriptor(MockDescriptor(version), APP_VERSION)
    assert compatibility.MINIMUM_ENGINE_VERSION in str(e.value)
    assert version in str(e.value)


# Intentions 3 and 4: code that can't run with this version of Python.


@pytest.mark.parametrize(
    "filename,expected",
    [
        (SITE_ENGINE_FILE, EngineNotCompatibleWithDesktop),
        (SITE_CORE_FILE, CoreNotCompatibleWithDesktop),
        (BUNDLED_CORE_FILE, None),
        (OTHER_FILE, None),
    ],
)
def test_incompatible_syntax(filename, expected):
    """
    Syntax no longer supported by Python is blamed on the site configuration's
    tk-desktop or tk-core, based on the file containing it.
    """
    error = _raise_from("print 'Python 2'", filename)
    assert isinstance(error, SyntaxError)

    # The traceback of a SyntaxError points to the code importing the module, not
    # to the module itself, so it must not be used to find the culprit.
    importer_traceback = _raise_from("1 / 0", SITE_ENGINE_FILE).__traceback__
    result = compatibility.get_incompatible_code_error(
        error, importer_traceback, APP_VERSION
    )
    if expected is None:
        assert result is None
    else:
        assert isinstance(result, expected)
        assert str(error) in str(result)


@pytest.mark.parametrize(
    "filename,expected",
    [
        (SITE_ENGINE_FILE, EngineNotCompatibleWithDesktop),
        (SITE_CORE_FILE, CoreNotCompatibleWithDesktop),
        (BUNDLED_CORE_FILE, None),
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

    result = compatibility.get_incompatible_code_error(
        error, error.__traceback__, APP_VERSION
    )
    if expected is None:
        assert result is None
    else:
        assert isinstance(result, expected)
        assert "Cookie" in str(result)


def test_other_errors_not_reported():
    """
    Other errors are genuine bugs, not incompatibilities, and are reported as is.
    """
    error = _raise_from("1 / 0", SITE_ENGINE_FILE)
    assert (
        compatibility.get_incompatible_code_error(
            error, error.__traceback__, APP_VERSION
        )
        is None
    )


# Intention 5: checks never prevent FlowPT Desktop from starting.


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


def test_engine_version_constraints_check_fails():
    """
    If the site configuration's tk-core can't check the constraints, e.g. its API
    is different, skip that check.
    """
    descriptor = MockDescriptor(constraints_error=TypeError("unexpected argument"))
    compatibility.check_engine_descriptor(descriptor, APP_VERSION)


def test_engine_manifest_unreadable():
    """If the tk-desktop manifest can't be read, skip the Python version check."""
    descriptor = MockDescriptor()
    descriptor._get_manifest = MagicMock(side_effect=Exception("No manifest"))
    compatibility.check_engine_descriptor(descriptor, APP_VERSION)


# User facing messages.


@pytest.mark.parametrize(
    "error_class,component",
    [
        (EngineNotCompatibleWithDesktop, "tk-desktop"),
        (CoreNotCompatibleWithDesktop, "tk-core"),
    ],
)
def test_error_message(error_class, component):
    """
    Messages say which component of the site configuration to upgrade, and give the
    FlowPT Desktop and Python versions and the reason, so support can diagnose the
    issue from a screenshot.
    """
    message = str(error_class(APP_VERSION, "Some reason."))
    assert "upgrade your site configuration's {}".format(component) in message
    assert "FlowPT Desktop {}".format(APP_VERSION) in message
    assert "Python {}.{}".format(*sys.version_info[:2]) in message
    assert "Some reason." in message
