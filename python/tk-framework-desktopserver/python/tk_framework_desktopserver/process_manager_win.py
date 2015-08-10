# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os

from process_manager import ProcessManager


class ProcessManagerWin(ProcessManager):
    """
    Windows OS Interface for Shotgun Commands.
    """
    platform_name = "windows"

    def _get_toolkit_script_name(self):
        return "shotgun.bat"

    def _get_toolkit_fallback_script_name(self):
        return "tank.bat"

    def open(self, filepath):
        """
        Opens a file with default os association or launcher found in environments. Not blocking.

        :param filepath: String file path (ex: "c:/file.mov")
        :returns: Bool If the operation was successful
        """
        self._verify_file_open(filepath)
        launcher = self._get_launcher()

        result = True
        if launcher is None:
            # Note: startfile is always async. As per docs, there is no way to retrieve exit code.
            os.startfile(filepath)
        else:
            result = self._launch_process(launcher, filepath, "Could not open file.")

        return result

    def pick_file_or_directory(self, multi=False):
        """
        Pop-up a file selection window.

        :param multi: Boolean Allow selecting multiple elements.
        :returns: List of files that were selected with file browser.
        """
        files = ProcessManager.pick_file_or_directory(self, multi)
        files = [f.replace("/", "\\") for f in files]
        # Qt returns files with / while the javascript code expects paths on Windows to use \
        return files
