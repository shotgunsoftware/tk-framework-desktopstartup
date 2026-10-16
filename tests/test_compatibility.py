# Copyright (c) 2026 Shotgun Software Inc.
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


@pytest.mark.parametrize("version", ["v2.5.4", "v2.9.0", "Undefined", "HEAD"])
def test_compatible_engine(version):
    """Supported or unknown engine versions are accepted."""
    compatibility.check_engine_descriptor(MockDescriptor(version), APP_VERSION)


@pytest.mark.parametrize("version", ["v2.4.12", "v2.5.0", "v2.5.3"])
def test_engine_older_than_minimum(version):
    """Engines released before Python 3 support are rejected."""
    with pytest.raises(EngineNotCompatibleWithDesktop) as e:
        compatibility.check_engine_descriptor(MockDescriptor(version), APP_VERSION)
    assert compatibility.MINIMUM_ENGINE_VERSION in str(e.value)
    assert version in str(e.value)
    assert APP_VERSION in str(e.value)


def test_engine_version_constraints_not_met():
    """The requires_*_version constraints from the engine's info.yml are reported."""
    reason = "Requires at least FPTR desktop app v9.0.0 but currently installed version is v1.8.0."
    descriptor = MockDescriptor(
        constraints_error=CheckVersionConstraintsError([reason])
    )
    with pytest.raises(EngineNotCompatibleWithDesktop) as e:
        compatibility.check_engine_descriptor(descriptor, APP_VERSION)
    assert reason in str(e.value)


def test_engine_version_constraints_check_fails():
    """An unexpected failure while checking the constraints doesn't block startup."""
    descriptor = MockDescriptor(constraints_error=TypeError("unexpected argument"))
    compatibility.check_engine_descriptor(descriptor, APP_VERSION)


def test_engine_minimum_python_version_met():
    """The minimum_python_version from the engine's info.yml is accepted."""
    descriptor = MockDescriptor(manifest={"minimum_python_version": "3.9"})
    compatibility.check_engine_descriptor(descriptor, APP_VERSION)


def test_engine_minimum_python_version_not_met():
    """The minimum_python_version from the engine's info.yml is reported."""
    descriptor = MockDescriptor(manifest={"minimum_python_version": "99.0"})
    with pytest.raises(EngineNotCompatibleWithDesktop) as e:
        compatibility.check_engine_descriptor(descriptor, APP_VERSION)
    assert "Requires at least Python 99.0" in str(e.value)


def test_ensure_engine_compatible_resolves_descriptor():
    """The engine descriptor is resolved from the context's environment."""
    env = MagicMock()
    env.get_engine_descriptor.return_value = MockDescriptor("v2.5.0")
    with patch("tank.platform.engine.get_environment_from_context", return_value=env):
        with pytest.raises(EngineNotCompatibleWithDesktop):
            compatibility.ensure_engine_compatible_with_desktop(
                MagicMock(), APP_VERSION
            )
    env.get_engine_descriptor.assert_called_once_with("tk-desktop")


def test_ensure_engine_compatible_cant_resolve_descriptor():
    """Failing to resolve the engine descriptor doesn't block startup."""
    with patch(
        "tank.platform.engine.get_environment_from_context",
        side_effect=Exception("No environment"),
    ):
        compatibility.ensure_engine_compatible_with_desktop(MagicMock(), APP_VERSION)


@pytest.mark.parametrize(
    "filename,expected",
    [
        (SITE_ENGINE_FILE, EngineNotCompatibleWithDesktop),
        (SITE_CORE_FILE, CoreNotCompatibleWithDesktop),
        (BUNDLED_CORE_FILE, None),
        (os.path.join(os.sep, "somewhere", "else.py"), None),
    ],
)
def test_incompatible_syntax(filename, expected):
    """Syntax no longer supported by Python is reported based on the file it is in."""
    error = _raise_from("print 'Python 2'", filename)
    assert isinstance(error, SyntaxError)

    # The traceback points to the importer, not to the file with the syntax error.
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
        (os.path.join(os.sep, "somewhere", "else.py"), None),
    ],
)
def test_removed_module(filename, expected):
    """Modules removed from the standard library are reported based on the importer."""
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
    """Errors other than syntax and import errors are left alone."""
    error = _raise_from("1 / 0", SITE_ENGINE_FILE)
    assert (
        compatibility.get_incompatible_code_error(
            error, error.__traceback__, APP_VERSION
        )
        is None
    )
