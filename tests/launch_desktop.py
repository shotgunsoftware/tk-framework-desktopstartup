# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
This script allows to launch the Shotgun Desktop from any Python interpreter.
"""

import sys
import os

repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

sys.path.insert(0, os.path.join(repo_root, "python"))

import shotgun_desktop.startup


class AppBoostrap(object):
    def tear_down_logging(self):
        pass

    def get_shotgun_desktop_cache_location(self):
        # Compute the Shotgun Desktop cache folder.
        if "SHOTGUN_HOME" in os.environ:
            shotgun_desktop_user_folder = os.path.expanduser(
                os.path.expandvars(os.environ["SHOTGUN_HOME"])
            )
        elif sys.platform == "darwin":
            shotgun_desktop_user_folder = os.path.expanduser("~/Library/Caches/Shotgun")
        elif sys.platform == "win32":
            shotgun_desktop_user_folder = os.path.join(os.environ["APPDATA"], "Shotgun")
        elif sys.platform.startswith("linux"):
            shotgun_desktop_user_folder = os.path.expanduser("~/.shotgun")
        else:
            raise NotImplementedError("Unsupported os %s" % sys.platform)
        return os.path.join(shotgun_desktop_user_folder, "desktop")

    def get_startup_location_override(self):
        return None

    def get_startup_path(self):
        return repo_root

    def get_version(self):
        return "2.0.0.debug"


exit_code = -1
try:
    exit_code = shotgun_desktop.startup.main(app_bootstrap=AppBoostrap())
except Exception as e:
    print(str(e))
    raise
finally:
    os._exit(exit_code)
