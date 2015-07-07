# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from optparse import OptionParser
import os
import logging


class IntegrationTestBootstrap(object):

    def __init__(self, test_folder):
        # Make sure test folder is clean
        self._test_folder = test_folder

        # Set up logging
        self._handlers = [
            logging.StreamHandler(),
            logging.FileHandler(self.get_logfile_location(), "w")
        ]
        self._logger = logging.getLogger("tk-desktop")
        self.add_logger_to_logfile(self._logger)

        # Mock some code from the shotgun_desktop to control where files are written.
        shotgun_desktop.paths.get_local_site_config_path = lambda x: os.path.join(
            self._test_folder,
            "site"
        )

        # Do not actually launch the engine ui
        shotgun_desktop.startup._run_engine = lambda *args: None

    def get_logfile_location(self):
        return os.path.join(self._test_folder, "test.log")

    def get_startup_path(self):
        return os.path.join(
            os.path.dirname(__file__), # integraton_tests
            "..", # tests
            "..", # root of package
            "python"
        )

    def add_logger_to_logfile(self, logger):
        for h in self._handlers:
            logger.addHandler(h)
        logger.setLevel(logging.ERROR)

    def get_startup_location_override(self):
        return None

    def update_startup(self):
        pass

    def clear_startup_location(self):
        pass

    def get_version(self):
        return "1.2"

    def tear_down_logging(self):
        pass

    def runs_bundled_startup(self):
        return True

    def get_shotgun_desktop_cache_location(self):
        return os.path.join(
            self._test_folder,
            "cache"
        )


def main():

    parser = OptionParser()
    parser.add_option("--test-folder", help="folder where the test will read data from", dest="test_folder")
    parser.add_option("--test-name", help="name of the test being executed.", dest="test_name")

    (options, args) = parser.parse_args()

    bootstrap = IntegrationTestBootstrap(options.test_folder)
    app, splash = shotgun_desktop.startup.__init_app()

    shotgun_desktop.startup.__launch_app(app, splash, ShotgunAuthenticator().get_user().create_sg_connection(), bootstrap)


if __name__ == '__main__':
    try:
        import shotgun_desktop.paths
        import shotgun_desktop.startup
        from tank_vendor.shotgun_authentication import ShotgunAuthenticator
        main()
    except Exception, e:
        print "Exception:%s,%s" % (e.__class__.__name__, e.message.encode("base64"))
