# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from .message import Message
from .logger import get_logger
from twisted.internet import reactor


class MessageHost(object):
    """
    Message Host Interface for the Shotgun API. We don't pass the actual websocket host directly in order to make
    sure that the API communicates with the client using the proper protocol.
    """

    def __init__(self, host, message):
        """
        Message Host Constructor

        :param host: WebSocketServerProtocol instance of actual host to communicate with.
        :param message: Message related to this host communication.
        """
        self._host = host
        self._message = message         # Message context that initiated this communication

    def reply(self, data):
        """
        Reply to current message.

        :param data: Object to send
        """

        message = Message(self._message["id"], self._host.PROTOCOL_VERSION)
        message.reply(data)

        self._send_message(message.data)

    def _send_message(self, data):
        # Writing to a protocol is not thread safe and must be called from reactor thread.
        reactor.callFromThread(lambda: self._host.json_reply(data))

    def report_error(self, error_message, error_data=None):
        """
        Report an error to the client relative to message context.

        :param error_message: String error message
        :param data: Optional object data to send in reply
        """
        get_logger().info("Websocket client error: %s" % error_message)
        message = Message(self._message["id"], self._host.PROTOCOL_VERSION)
        message.error(error_message, error_data)

        self._send_message(message.data)
