# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import os

class DesktopserverFramework(sgtk.platform.Framework):

    ##########################################################################################
    # init and destroy

    def init_framework(self):
        self.log_debug("%s: Initializing..." % self)
        self.server = None

    def destroy_framework(self):
        self.log_debug("%s: Destroying..." % self)

    def start_server(self, debug=False, start_reactor=True):
        """
        Start shotgun web server, listening to websocket connections.

        :param debug: Boolean Show debug output. Will also Start local web server to test client pages.
        :param start_reactor: Boolean Start threaded reactor
        """
        tk_server = self.import_module("tk_server")
        key_path = os.path.join(os.path.dirname(tk_server.__file__), "../../resources/keys")
        self.server = tk_server.Server()
        self.server.start(debug, key_path, start_reactor)

    def stop_server(self):
        if self.server:
            self.server.stop()
