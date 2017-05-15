# -*- coding: utf-8 -*-

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
import sys
import optparse


def _parse_options():
    """
    Parses the command line for options.

    :returns An OptionParser with attributes debug and configuration.
    """
    parser = optparse.OptionParser()
    parser.add_option(
        "--debug", action="store_true", default=False,
        help="prints debugging message from the server on the console"
    )
    parser.add_option(
        "-c", "--configuration", action="store", default=None,
        help="location of the configuration file"
    )

    options, _ = parser.parse_args()

    return options


def main():
    """
    Main.
    """

    # Configure the app.
    options = _parse_options()
    # Create the logger and dump the settings.
    app_logger = logger.get_logger(options.debug)

    # Read the settings and print them out.
    app_settings = settings.get_settings(options.configuration)
    app_logger.info("Starting server with the following configuration:")
    app_settings.dump(app_logger)

    try:
        # Start the server
        server = Server(
            low_level_debug=app_settings.low_level_debug,
            keys_path=app_settings.certificate_folder,
            port=app_settings.port,
            whitelist=app_settings.whitelist
        )
        server.start()
    except BrowserIntegrationError, e:
        if options.debug:
            app_logger.exception("There was an error while running the browser integration.")
        else:
            app_logger.error(e)
        return

    # Enables CTRL-C to kill this process even tough Qt doesn't know how to play nice with Python.
    # As per this stack overflow comment
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Start the main Qt event loop.
    from PySide import QtGui
    app = QtGui.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.exec_()


if __name__ == '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../python"))

    # Import settings here since it wasn't in the Python path before.
    import settings
    import logger

    from tk_framework_desktopserver import Server, BrowserIntegrationError
    main()
