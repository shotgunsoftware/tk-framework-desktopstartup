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
Reports errors happening before tk-core and its Qt support are loaded, so the usual
error handling can't run.

This module must only use the Python standard library, and must never raise.
"""

import importlib
import os
import sys

TITLE = "Flow Production Tracking Error"


def _import_qt_widgets():
    """
    Import the QtWidgets module of a Qt binding, preferring the one the PTR desktop
    app already loaded.

    :returns: Tuple of the binding description, e.g. "PySide6 6.8.3", and its QtWidgets
        module, or (None, None) if no binding can be imported.
    """
    names = ["PySide6", "PySide2"]
    names.sort(key=lambda name: name not in sys.modules)
    for name in names:
        try:
            binding = importlib.import_module(name)
            qt_widgets = importlib.import_module(name + ".QtWidgets")
        except Exception:
            continue
        return "{} {}".format(name, getattr(binding, "__version__", "")), qt_widgets
    return None, None


def report_core_not_loaded(core_path, error):
    """
    Report that the tk-core used by this framework can't be loaded with the Python
    and Qt of the PTR desktop app: on stderr for users running the app from a
    terminal, and in a dialog if a Qt binding is available.

    :param str core_path: Path to the tk-core used by this framework.
    :param error: The error raised while loading it.
    """
    try:
        binding, qt_widgets = _import_qt_widgets()
        if "SGTK_CORE_LOCATION" in os.environ:
            advice = (
                "SGTK_CORE_LOCATION is set: make sure it points to a tk-core "
                "compatible with this PTR desktop app."
            )
        else:
            advice = "Please install the latest PTR desktop app."
        message = (
            "The PTR desktop app can't start: the tk-core at {} can't run with "
            "Python {}.{} and {}.\n\nError: {}\n\n{}".format(
                core_path,
                sys.version_info[0],
                sys.version_info[1],
                binding or "no Qt binding",
                error,
                advice,
            )
        )
    except Exception as e:
        qt_widgets = None
        message = "The PTR desktop app can't start: {}".format(e)

    try:
        if sys.stderr:
            sys.stderr.write("{}: {}\n".format(TITLE, message))
            sys.stderr.flush()
    except Exception:
        pass

    try:
        if qt_widgets:
            app = qt_widgets.QApplication.instance() or qt_widgets.QApplication(
                sys.argv
            )
            qt_widgets.QMessageBox.critical(None, TITLE, message)
    except Exception:
        pass
