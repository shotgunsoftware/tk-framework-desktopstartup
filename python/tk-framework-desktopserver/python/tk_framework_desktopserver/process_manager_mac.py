# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from process_manager import ProcessManager


class ProcessManagerMac(ProcessManager):
    """
    Mac OS Interface for Shotgun Commands.
    """

    platform_name = "mac"

    def open(self, filepath):
        """
        Opens a file with default os association or launcher found in environments. Not blocking.

        :param filepath: String file path (ex: "c:/file.mov")
        :returns: Bool If the operation was successful
        """
        self._verify_file_open(filepath)
        launcher = self._get_launcher()

        if launcher is None:
            launcher = "open"

        return self._launch_process(launcher, filepath, "Could not open file.")
