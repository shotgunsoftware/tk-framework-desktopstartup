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
Specification of how the PTR desktop app reports a site configuration whose tk-core
or tk-desktop can't run with the Python it ships.

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

1. When the bootstrap fails with a SyntaxError (syntax no longer supported) or an
   ImportError (module removed from the standard library, e.g. Cookie, imp or
   distutils), tell the user whether the site configuration's tk-desktop or tk-core
   is the culprit, based on the file the error comes from. This keeps working as
   Python versions are dropped and added every year, without listing them. tk-core
   wraps errors raised while loading the engine, so the original error is used.
2. Errors coming from the tk-core bundled with this framework are not blamed on the
   site configuration: that core is known to be compatible.
3. Other errors, and errors already meant for the user, are reported as is.
4. The message tells the user what to upgrade, and gives the PTR desktop app and
   Python versions.
5. This only runs when the bootstrap already failed, and must never hide that
   failure: if the error can't be classified, the original error is reported.
"""

import os
import pathlib
import sys
import typing
from unittest.mock import patch

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
from tank.util.loader import load_plugin

APP_VERSION = "v1.8.0"

ENGINE_ROOT = os.path.join(os.sep, "bundle_cache", "tk-desktop", "v2.9.0")
SITE_ENGINE_FILE = os.path.join(ENGINE_ROOT, "python", "tk_desktop", "site.py")
SITE_CORE_PYTHON = os.path.join(os.sep, "site_config", "install", "core", "python")
SITE_CORE_FILE = os.path.join(SITE_CORE_PYTHON, "tank", "__init__.py")
SITE_CORE_VENDOR_FILE = os.path.join(SITE_CORE_PYTHON, "tank_vendor", "lib.py")
BUNDLED_CORE_FILE = os.path.join(compatibility._BUNDLED_CORE_PATH, "tank", "x.py")
BUNDLED_CORE_VENDOR_FILE = os.path.join(
    compatibility._BUNDLED_CORE_PATH, "tank_vendor", "lib.py"
)
OTHER_FILE = os.path.join(os.sep, "somewhere", "else.py")

CLASSIFICATION = [
    (SITE_ENGINE_FILE, EngineNotCompatibleWithDesktop),
    (SITE_CORE_FILE, CoreNotCompatibleWithDesktop),
    (SITE_CORE_VENDOR_FILE, CoreNotCompatibleWithDesktop),
    (BUNDLED_CORE_FILE, None),
    (BUNDLED_CORE_VENDOR_FILE, None),
    (OTHER_FILE, None),
]


def _raise_from(code: str, filename: str) -> Exception:
    """
    Run the code as if it was located in the given file.

    :returns: The raised exception.
    """
    try:
        exec(compile(code, filename, "exec"), {})
    except Exception as e:
        return e
    raise AssertionError("The code didn't raise.")


# Intentions 1 and 2: code that can't run with this version of Python.


@pytest.mark.parametrize("filename,expected", CLASSIFICATION)
def test_incompatible_syntax(filename: str, expected: typing.Optional[type]) -> None:
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


@pytest.mark.parametrize("filename,expected", CLASSIFICATION)
def test_removed_module(filename: str, expected: typing.Optional[type]) -> None:
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
def test_engine_load_error_wrapped_by_core(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, code: str
) -> None:
    """
    tk-core loads the engine's entry point with load_plugin(), which wraps any error
    in a TankLoadPluginError. The original error, raised by the engine's code, is the
    one to classify.
    """
    engine_root = tmp_path / "tk-desktop" / "v2.9.0"
    package = engine_root / "python" / "tk_desktop"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(code)
    entry_point = engine_root / "engine.py"
    entry_point.write_text("import tk_desktop\n")
    monkeypatch.syspath_prepend(str(engine_root / "python"))
    monkeypatch.delitem(sys.modules, "tk_desktop", raising=False)

    with pytest.raises(Exception) as e:
        load_plugin(str(entry_point), object)
    assert type(e.value).__name__ == "TankLoadPluginError"

    result = compatibility.get_incompatible_code_error(e.value, APP_VERSION)
    assert isinstance(result, EngineNotCompatibleWithDesktop)
    assert compatibility.UPGRADE_ENGINE in str(result)


# Intention 3: other errors are reported as is.


def test_other_errors_not_reported() -> None:
    """
    Other errors are genuine bugs, not incompatibilities, and are reported as is.
    """
    error = _raise_from("1 / 0", SITE_ENGINE_FILE)
    assert compatibility.get_incompatible_code_error(error, APP_VERSION) is None


def test_desktop_errors_not_reported() -> None:
    """
    Errors already meant for the user are shown as is, even if they happened while
    handling an import error.
    """
    try:
        try:
            raise ImportError("No module named 'Cookie'")
        except ImportError:
            raise ShotgunDesktopError("Invalid pipeline configuration.")
    except ShotgunDesktopError as e:
        error = e
    assert compatibility.get_incompatible_code_error(error, APP_VERSION) is None


# Intention 4: user facing messages.


@pytest.mark.parametrize(
    "error_class,component",
    [
        (EngineNotCompatibleWithDesktop, "tk-desktop engine"),
        (CoreNotCompatibleWithDesktop, "tk-core"),
    ],
)
def test_error_message(error_class: type, component: str) -> None:
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
def test_incompatible_code_advice(filename: str, advice: str) -> None:
    """Code that can't run asks to upgrade the component it belongs to."""
    error = _raise_from("import Cookie", filename)
    result = compatibility.get_incompatible_code_error(error, APP_VERSION)
    assert advice in str(result)


# Intention 5: never hide the original error.


def test_classification_never_raises() -> None:
    """
    If the error can't be classified, None is returned so the caller re-raises the
    original error, instead of replacing it with an error raised by the
    classification.
    """
    error = _raise_from("import Cookie", SITE_CORE_FILE)
    with patch.object(compatibility, "_normalize", side_effect=RuntimeError("Bug")):
        assert compatibility.get_incompatible_code_error(error, APP_VERSION) is None
