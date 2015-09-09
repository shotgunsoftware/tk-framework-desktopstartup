# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import os
import threading

from server_protocol import ServerProtocol

from twisted.internet import reactor, ssl
from twisted.python import log

from autobahn.twisted.websocket import WebSocketServerFactory, listenWS

from .errors import MissingCertificate


class Server:
    _DEFAULT_PORT = 9000
    _DEFAULT_KEYS_PATH = "../resources/keys"
    _DEFAULT_WHITELIST = "*.shotgunstudio.com"

    def __init__(self, port=None, debug=True, whitelist=None, keys_path=None):
        """
        Constructor.
        """
        self._port = port or self._DEFAULT_PORT
        self._keys_path = keys_path or self._DEFAULT_KEYS_PATH
        self._whitelist = whitelist or self._DEFAULT_WHITELIST
        self._debug = debug

        if self._debug:
            log.startLogging(sys.stdout)

    def _raise_if_missing_certificate(self, certificate_path):
        """
        Raises an exception is a certificate file is missing.

        :param certificate_path: Path to the certificate file.

        :raises Exception: Thrown if the certificate file is missing.
        """
        if not os.path.exists(certificate_path):
            raise MissingCertificate("Missing certificate file: %s" % certificate_path)

    def _start_server(self):
        """
        Start shotgun web server, listening to websocket connections.

        :param debug: Boolean Show debug output. Will also Start local web server to test client pages.
        """

        cert_key_path = os.path.join(self._keys_path, "server.key")
        cert_crt_path = os.path.join(self._keys_path, "server.crt")

        self._raise_if_missing_certificate(cert_key_path)
        self._raise_if_missing_certificate(cert_crt_path)

        # SSL server context: load server key and certificate
        self.context_factory = ssl.DefaultOpenSSLContextFactory(cert_key_path,
                                                                cert_crt_path)

        self.factory = WebSocketServerFactory(
            "wss://localhost:%d" % self._port, debug=self._debug, debugCodePaths=self._debug
        )

        self.factory.protocol = ServerProtocol
        self.factory.websocket_server_whitelist = self._whitelist
        self.factory.setProtocolOptions(allowHixie76=True, echoCloseCodeReason=True)
        self.listener = listenWS(self.factory, self.context_factory)

    def _start_reactor(self):
        """
        Starts the reactor in a Python thread.
        """
        def start():
            reactor.run(installSignalHandlers=0)

        t = threading.Thread(target=start)
        t.start()

    def start(self, start_reactor=False):
        """
        Start shotgun web server, listening to websocket connections.

        :param debug: Boolean Show debug output. Will also Start local web server to test client pages.
        :param keys_path: Path to the certificate files (.crt and .key).
        :param start_reactor: Boolean Start threaded reactor
        """
        self._start_server()
        if start_reactor:
            self._start_reactor()

    def stop(self):
        """
        Stops the serverreactor.
        """
        reactor.callFromThread(reactor.stop)
