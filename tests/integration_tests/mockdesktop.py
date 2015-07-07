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
import sys

# Set up logging
_handlers = [
    logging.StreamHandler()
]
_logger = logging.getLogger("tk-desktop")
_logger.addHandler(_handlers[0])


class IntegrationTestBootstrap(object):

    def __init__(self, test_folder):
        # Make sure test folder is clean
        self._test_folder = test_folder
        _handlers.append(logging.FileHandler(self.get_logfile_location(), "w"))
        self.add_logger_to_logfile(_logger)
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
        global _handlers
        for h in _handlers:
            if h not in logger.handlers:
                logger.addHandler(h)
        logger.setLevel(logging.DEBUG)

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
    parser.add_option("--reset-site", help="site configuration will be reset.")
    (options, args) = parser.parse_args()

    bootstrap = IntegrationTestBootstrap(options.test_folder)
    sg_auth = shotgun_desktop.startup.import_shotgun_authentication_from_path(bootstrap)

    app, splash = shotgun_desktop.startup.__init_app()
    connection = sg_auth.ShotgunAuthenticator().get_user().create_sg_connection()
    try:
        shotgun_desktop.startup.__launch_app(app, splash, connection, bootstrap)
    except:
        _logger.exception("Exception thrown!")
        raise


if __name__ == '__main__':
    try:
        sys.path.insert(
            0,
            os.path.join(os.path.dirname(__file__), "..", "..", "python")
        )
        import shotgun_desktop.paths
        import shotgun_desktop.startup

        main()
    except Exception, e:
        _logger.debug("Exception:%s,%s" % (e.__class__.__name__, e.message.encode("base64")))
