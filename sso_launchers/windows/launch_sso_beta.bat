0<0# : ^
"""
@echo off
"C:\Program Files\Shotgun\Python"\python.exe "%~f0" %*
pause
goto :EOF
"""

import os
import sys
import urllib2
import zipfile
import tempfile
import shutil
import subprocess

branch_name = "feature/sso"
branch_file_name = branch_name.replace("/", "-")

DESKTOP_STARTUP_URL = "https://github.com/shotgunsoftware/tk-framework-desktopstartup/archive/%s.zip" % branch_name


def _get_shotgun_home():
    if sys.platform == "darwin":
        shotgun_home = os.path.expanduser("~/Library/Caches/Shotgun.sso.beta")
    elif sys.platform == "win32":
        shotgun_home = os.path.expandvars(r"$APPDATA\Shotgun.sso.beta")
    else:
        shotgun_home = os.path.expanduser("~/.shotgun.sso.beta")

    print "Shotgun Desktop will write files to %s." % shotgun_home

    return shotgun_home


def _download_desktop_startup(shotgun_home):

    if "SGTK_DESKTOP_STARTUP_LOCATION" in os.environ:
        return os.path.expanduser(os.environ["SGTK_DESKTOP_STARTUP_LOCATION"]), False

    # Make sure the folder in which we'll create temp dirs exists.
    parent_folder = os.path.join(shotgun_home, "tk-framework-desktopstartup")
    if not os.path.exists(parent_folder):
        os.makedirs(parent_folder)

    temp_folder = tempfile.mkdtemp(dir=parent_folder)
    print "Downloading tk-framework-desktopstartup at %s from %s" % (temp_folder, DESKTOP_STARTUP_URL)

    downloaded_zip = os.path.join(temp_folder, "%s.zip" % branch_file_name)
    with open(downloaded_zip, "wb") as fh:
        fh.write(urllib2.urlopen(DESKTOP_STARTUP_URL).read())

    with open(downloaded_zip, "rb") as fh:
        archive = zipfile.ZipFile(downloaded_zip)
        archive.extractall(temp_folder)

    return os.path.join(temp_folder, "tk-framework-desktopstartup-%s" % branch_file_name), True


def _get_sg_desktop_executable():

    if sys.platform == "darwin":
        return "/Applications/Shotgun.app/Contents/MacOS/Shotgun"
    elif sys.platform == "win32":
        return r"C:\PRogram Files\Shotgun\Shotgun.exe"
    else:
        return "/opt/Shotgun/Shotgun"


def _launch_shotgun_desktop(shotgun_home, desktop_startup_location):

    descriptor = "sgtk:descriptor:path?path=$SGTK_DESKTOP_STARTUP_LOCATION/python/bundle_cache/tk-config-basic"

    os.environ["SGTK_DESKTOP_STARTUP_LOCATION"] = desktop_startup_location
    os.environ["SHOTGUN_HOME"] = shotgun_home
    os.environ["SHOTGUN_DESKTOP_CONFIG_FALLBACK_DESCRIPTOR"] = descriptor

    subprocess.Popen([_get_sg_desktop_executable()], env=os.environ).communicate()


def main():

    shotgun_home = _get_shotgun_home()

    desktop_startup_location, can_wipe = _download_desktop_startup(shotgun_home)
    try:
        _launch_shotgun_desktop(shotgun_home, desktop_startup_location)
    finally:
        if can_wipe:
            shutil.rmtree(desktop_startup_location)


if __name__ == "__main__":
    main()
