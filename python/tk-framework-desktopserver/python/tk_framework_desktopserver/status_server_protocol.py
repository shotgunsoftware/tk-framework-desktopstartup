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
import json
import re
import datetime
from urlparse import urlparse

from shotgun_api import ShotgunAPI
from message_host import MessageHost
from message import Message

from autobahn import websocket
from autobahn.twisted.websocket import WebSocketServerProtocol


class StatusServerProtocol(WebSocketServerProtocol):
    """
    ***UN-SECURED*** Server Protocol.

    Used to acknowledge secure server presence and report certificate errors.

                        DO NO SEND ANY IMPORTANT INFORMATION FROM THIS PROTOCOL!
    """

    # Error codes
    CONNECTED = 202
    SSL_CERTIFICATE_INVALID = 401
    CONNECTION_LOST = 499
    SSL_NO_CERTIFICATE_FILE = 1000

    # Variable used to pass along error message between secure server and status server
    serverStatus = 202

    def __init__(self):
        pass

    def onConnect(self, request):
        pass

    def onMessage(self, payload, isBinary):
        """
        Called by 'WebSocketServerProtocol' when we receive a message from the websocket

        Entry point into our Shotgun API.

        :param payload: String Message payload
        :param isBinary: If the message is in binary format
        """

        # We don't currently handle any binary messages
        if isBinary:
            return

        message = payload.decode("utf8")

        if message == "get_last_error":
            self.sendMessage(str(StatusServerProtocol.serverStatus), False)
        elif message == "ping":
            self.sendMessage("acknowledged", False)
