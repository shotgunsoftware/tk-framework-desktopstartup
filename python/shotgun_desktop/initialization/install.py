# Copyright (c) 2015 Shotgun Software Inc.
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
import uuid
import errno
import shutil
import tempfile
import traceback

from .zipfilehelper import unzip_file
from distutils.version import LooseVersion

from PySide import QtCore

from shotgun_api3 import Shotgun

from .. import utils
from . import constants
from . import shotgun
from ..logger import get_logger


class InstallThread(QtCore.QThread):

    def __init__(self):
        QtCore.QThread.__init__(self)
        self._auth = None
        self._logger = get_logger("initialization.install")
        self._error_message = None

    def wait(self):
        """
        Waits for the install thread to finish.

        :raises Exception: Thrown if the thread ended due to an error.
        """
        QtCore.QThread.wait(self)
        if self._error_message is not None:
            raise Exception(self._error_message)

    def set_install_folder(self, folder):
        self._sgtk_folder = folder

    def set_shotgun_info(self, connection, script_user):
        self._connection = connection
        self._server_url = connection.base_url
        self._sg_proxy = connection.config.raw_http_proxy
        self._script_user = script_user

    def set_app_store_info(
        self,
        script, key,
        app_store_current_script_user_entity,
        actual_app_store_http_proxy, app_store_http_proxy_setting
    ):
        """
        Sets app store connection parameters.

        :param script: Script name to authenticate to the App Store.
        :param key: Script key to authenticate to the App Store.
        :param app_store_current_script_user_entity: Entity for the App Store script user.
        :param actual_app_store_http_proxy: Proxy server to use when connecting to the App Store.
        :param app_store_http_proxy_setting: Raw value of the proxy server setting to write to shotgun.yml
            If None, nothing will be written. If empty string, null will be written. If non-empty, will be written
            as is.
        """
        self._app_store_script = script
        self._app_store_key = key
        self._app_store_current_script_user_entity = app_store_current_script_user_entity
        self._actual_app_store_http_proxy = actual_app_store_http_proxy
        self._app_store_http_proxy_setting = app_store_http_proxy_setting

    def set_locations(self, location):
        self._location = location

    def set_executables(self, executables):
        self._executables = executables

    def run(self):
        if os.path.exists(self._sgtk_folder):
            self._logger.info("Install directory already exists: '%s'" % self._sgtk_folder)
            return

        try:
            self.create_structure()
            self.install_core()
        except Exception, e:
            self._logger.exception("Error installing core.")
            self._error_message = str(e)
        else:
            self._logger.debug("Done")
        finally:
            if self._auth is not None:
                utils.sudo_end(self._auth)
                self._auth = None

    def create_structure(self):
        self._logger.debug("Creating install directory...")

        # Figure out if we need to mkdir with elevated privs
        try:
            os.makedirs(self._sgtk_folder, 0775)
            elevate = False
        except OSError, e:
            if e.errno != errno.EACCES:
                raise
            elevate = True

        if elevate:
            self._auth = utils.sudo_start()

            touch = lambda path: utils.sudo_touch(self._auth, path)
            mkdir = lambda path, mode: utils.sudo_mkdir(self._auth, path, mode)
            chmod = lambda path, mode: utils.sudo_chmod(self._auth, path, mode)

            # redo the mkdir since it failed above
            mkdir(self._sgtk_folder, 0775)
        else:
            mkdir = os.makedirs
            chmod = os.chmod
            touch = lambda path: open(path, "a").close()

        mkdir(os.path.join(self._sgtk_folder, "config"), 0775)
        mkdir(os.path.join(self._sgtk_folder, "config", "core"), 0775)

        mkdir(os.path.join(self._sgtk_folder, "install"), 0775)
        mkdir(os.path.join(self._sgtk_folder, "install", "core"), 0777)
        mkdir(os.path.join(self._sgtk_folder, "install", "core.backup"), 0777)
        mkdir(os.path.join(self._sgtk_folder, "install", "engines"), 0777)
        mkdir(os.path.join(self._sgtk_folder, "install", "apps"), 0777)
        mkdir(os.path.join(self._sgtk_folder, "install", "frameworks"), 0777)

        # create configuration files
        self._logger.debug("Creating configuration files...")

        sg_config_location = os.path.join(self._sgtk_folder, "config", "core", "shotgun.yml")
        touch(sg_config_location)
        chmod(sg_config_location, 0777)
        fh = open(sg_config_location, "wt")
        fh.write("# Shotgun Pipeline Toolkit configuration file\n")
        fh.write("# this file was automatically created\n")
        fh.write("\n")
        fh.write("host: %s\n" % self._server_url)
        if self._script_user:
            fh.write("api_script: %s\n" % self._script_user["firstname"])
            fh.write("api_key: %s\n" % self._script_user["salted_password"])
        if self._sg_proxy:
            fh.write("http_proxy: %s\n" % self._sg_proxy)
        else:
            fh.write("http_proxy: null\n")

        # If the proxy is to be set, set it.
        if self._app_store_http_proxy_setting:
            fh.write("app_store_http_proxy: %s\n" % self._app_store_http_proxy_setting)
        # If the proxy is to be hardcoded to none, write null
        elif self._app_store_http_proxy_setting == "":
            fh.write("app_store_http_proxy: null\n")
        # Otherwise we'll inherit whatever proxy setting that came from http_proxy.

        fh.write("\n")
        fh.write("# End of file.\n")
        fh.close()

        if shotgun.is_script_user_required(self._connection):
            # Core won't be able to use session user and password for authenticating,
            # so store the appstore tokens instead.
            sg_config_location = os.path.join(self._sgtk_folder, "config", "core", "app_store.yml")
            touch(sg_config_location)
            chmod(sg_config_location, 0777)
            fh = open(sg_config_location, "wt")
            fh.write("# Shotgun Pipeline Toolkit configuration file\n")
            fh.write("# this file was automatically created\n")
            fh.write("\n")
            fh.write("host: %s\n" % constants.SGTK_APP_STORE)
            fh.write("api_script: %s\n" % self._app_store_script)
            fh.write("api_key: %s\n" % self._app_store_key)
            if self._sg_proxy is None:
                fh.write("http_proxy: null\n")
            else:
                fh.write("http_proxy: %s\n" % self._sg_proxy)
            fh.write("\n")
            fh.write("# End of file.\n")
            fh.close()

        # location script
        sg_code_location = os.path.join(self._sgtk_folder, "config", "core", "install_location.yml")
        touch(sg_code_location)
        chmod(sg_code_location, 0777)
        fh = open(sg_code_location, "wt")
        fh.write("# Shotgun Pipeline Toolkit configuration file\n")
        fh.write("# This file was automatically created\n")
        fh.write("\n")
        fh.write("# This file stores the location on disk where this\n")
        fh.write("# configuration is located. It is needed to ensure\n")
        fh.write("# that deployment works correctly on all os platforms.\n")
        fh.write("\n")

        for (curr_platform, path) in self._location.items():
            fh.write("%s: '%s'\n" % (curr_platform, path))

        fh.write("\n")
        fh.write("# End of file.\n")
        fh.close()

        # write separate files containing the interpreter string for each platform
        for x in self._executables:
            sg_config_location = os.path.join(self._sgtk_folder, "config", "core", "interpreter_%s.cfg" % x)
            touch(sg_config_location)
            chmod(sg_config_location, 0777)
            fh = open(sg_config_location, "wt")
            fh.write(self._executables[x])
            fh.close()

    def install_core(self):
        # download latest core from the app store
        sg_studio_version = ".".join([str(x) for x in self._connection.server_info["version"]])

        sg_app_store = Shotgun(
            constants.SGTK_APP_STORE, self._app_store_script, self._app_store_key,
            http_proxy=self._actual_app_store_http_proxy
        )

        (latest_core, core_path) = self._download_core(
            sg_studio_version, sg_app_store,
            self._server_url, self._app_store_current_script_user_entity)

        self._logger.debug("Now installing Shotgun Pipeline Toolkit Core")
        sys.path.insert(0, core_path)
        try:
            import _core_upgrader
            sgtk_install_folder = os.path.join(self._sgtk_folder, "install")
            _core_upgrader.upgrade_tank(sgtk_install_folder, self._logger)
        except Exception, e:
            self._logger.exception("Could not run upgrade script! Error reported: %s" % e)
            return

        # now copy some of the files into key locations in the core area
        self._logger.debug("Installing binary wrapper scripts...")
        src_dir = os.path.join(self._sgtk_folder, "install", "core", "setup", "root_binaries")
        # pre-013 check
        if not os.path.exists(src_dir):
            self._logger.error(
                "Looks like you are trying to download an old version "
                "of the Shotgun Pipeline Toolkit!")
            return

        # need to make sure we can write to the install dir
        if self._auth is not None:
            utils.sudo_chmod(self._auth, self._sgtk_folder, 0777)

        for file_name in os.listdir(src_dir):
            src_file = os.path.join(src_dir, file_name)
            tgt_file = os.path.join(self._sgtk_folder, file_name)
            shutil.copy(src_file, tgt_file)
            os.chmod(tgt_file, 0775)

        # put permissions back
        if self._auth is not None:
            utils.sudo_chmod(self._auth, self._sgtk_folder, 0775)

        # report back to app store that activation has completed
        data = {}
        data["description"] = "%s: Sgtk was activated" % self._server_url
        data["event_type"] = "TankAppStore_Activation_Complete"
        data["entity"] = latest_core
        data["user"] = self._app_store_current_script_user_entity
        data["project"] = constants.SGTK_APP_STORE_DUMMY_PROJECT
        sg_app_store.create("EventLogEntry", data)

    def _download_core(self, sg_studio_version, sg_app_store, studio_url, app_store_current_script_user_entity):
        """
        Downloads the latest core from the app store.
        Returns a path to the unpacked code in a tmp location
        """
        self._logger.debug("Finding the latest version of the Core API...")

        if os.environ.get("TANK_QA_ENABLED"):
            latest_filter = [["sg_status_list", "is_not", "bad" ]]
        else:
            latest_filter = [["sg_status_list", "is_not", "rev" ],
                             ["sg_status_list", "is_not", "bad" ]]

        latest_core = sg_app_store.find_one(
            constants.SGTK_CORE_VERSION_ENTITY,
            filters=latest_filter,
            fields=["sg_min_shotgun_version", "code", constants.SGTK_CODE_PAYLOAD_FIELD],
            order=[{"field_name": "created_at", "direction": "desc"}])
        if latest_core is None:
            raise Exception("Cannot find a version of the core system to download!"
                            "Please contact support!")

        # make sure that the min shotgun version is higher than our current version
        min_sg_version = latest_core["sg_min_shotgun_version"]
        if min_sg_version:
            if min_sg_version.startswith("v"):
                min_sg_version = min_sg_version[1:]
            # there is a sg min version required - make sure we have that!
            if LooseVersion(min_sg_version) > LooseVersion(sg_studio_version):
                # todo - handle this gracefully.
                raise Exception("Your shotgun installation is version %s "
                                "but the Sgtk Core (%s) requires version %s. "
                                "Please contact support." % (sg_studio_version,
                                                             latest_core["code"],
                                                             min_sg_version))

        # for debugging allow pointing at an arbitrary core directory
        if "SGTK_CORE_DEBUG_LOCATION" in os.environ:
            self._logger.debug("Using debug core from '%s'" % os.environ["SGTK_CORE_DEBUG_LOCATION"])
            return (latest_core, os.path.expanduser(os.path.expandvars(os.environ["SGTK_CORE_DEBUG_LOCATION"])))
        # download Sgtk code
        if latest_core[constants.SGTK_CODE_PAYLOAD_FIELD] is None:
            raise Exception("Cannot find an Sgtk binary bundle for %s. Please contact support" % latest_core["code"])

        self._logger.debug("Downloading Toolkit Core API %s from the App Store..." % latest_core["code"])

        zip_tmp = os.path.join(tempfile.gettempdir(), "%s_sgtk_core.zip" % uuid.uuid4().hex)
        extract_tmp = os.path.join(tempfile.gettempdir(), "%s_sgtk_unzip" % uuid.uuid4().hex)

        # now have to get the attachment id from the data we obtained. This is a bit hacky.
        # data example for the payload field, as returned by the query above:
        # {'url': 'http://tank.shotgunstudio.com/file_serve/attachment/21', 'name': 'tank_core.zip',
        #  'content_type': 'application/zip', 'link_type': 'upload'}
        #
        # grab the attachment id off the url field and pass that to the download_attachment()
        # method below.

        try:
            attachment_id = int(latest_core[constants.SGTK_CODE_PAYLOAD_FIELD]["url"].split("/")[-1])
        except:
            raise Exception("Could not extract attachment id from data %s" % latest_core)

        bundle_content = sg_app_store.download_attachment(attachment_id)
        fh = open(zip_tmp, "wb")
        fh.write(bundle_content)
        fh.close()

        self._logger.debug("Download complete, now extracting content...")
        # unzip core zip file to temp location and run updater
        unzip_file(zip_tmp, extract_tmp)

        # write a custom event to the shotgun event log to indicate that a download has happened.
        data = {}
        data["description"] = "%s: Core API was downloaded" % studio_url
        data["event_type"] = "TankAppStore_CoreApi_Download"
        data["entity"] = latest_core
        data["user"] = app_store_current_script_user_entity
        data["project"] = constants.SGTK_APP_STORE_DUMMY_PROJECT
        data["attribute_name"] = constants.SGTK_CODE_PAYLOAD_FIELD
        sg_app_store.create("EventLogEntry", data)

        return (latest_core, extract_tmp)
