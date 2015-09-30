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
import threading
import logging

from server_protocol import ServerProtocol

from twisted.internet import reactor, ssl, error
from twisted.python import log

from autobahn.twisted.websocket import WebSocketServerFactory, listenWS

from .errors import MissingCertificateError, PortBusyError


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

        self._logger_root = logging.getLogger("tk-framework-desktopserver")

        if self._debug:
            # This will take the Twisted logging and forward it to Python's logging.
            self._observer = log.PythonLoggingObserver("tk-framework-desktopserver.twisted")
            self._observer.start()

    def get_logger(self):
        """
        :returns: The python logger root for the framework.
        """
        return self._logger_root

    def _raise_if_missing_certificate(self, certificate_path):
        """
        Raises an exception is a certificate file is missing.

        :param certificate_path: Path to the certificate file.

        :raises Exception: Thrown if the certificate file is missing.
        """
        if not os.path.exists(certificate_path):
            raise MissingCertificateError("Missing certificate file: %s" % certificate_path)

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
        try:
            self.listener = listenWS(self.factory, self.context_factory)
        except error.CannotListenError, e:
            raise PortBusyError(str(e))

    def _start_reactor(self):
        """
        Starts the reactor in a Python thread.
        """
        def start():
            reactor.run(installSignalHandlers=0)

        self._reactor_thread = threading.Thread(target=start)
        self._reactor_thread.start()

    def start(self):
        """
        Start shotgun web server, listening to websocket connections.
        """
        self._start_server()
        self._start_reactor()

    def is_running(self):
        """
        :returns: True if the server is up and running, False otherwise.
        """
        return self._reactor_thread.isAlive()

    def tear_down(self):
        """
        Tears down Twisted.
        """
        reactor.callFromThread(reactor.stop)
        self._reactor_thread.join()
