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
from . import certificates

import logger


class Server(object):
    _DEFAULT_PORT = 9000
    _DEFAULT_KEYS_PATH = "../resources/keys"
    _DEFAULT_WHITELIST = "*.shotgunstudio.com"

    def __init__(self, keys_path, port=None, low_level_debug=False, whitelist=None):
        """
        Constructor.

        :param keys_path: Path to the keys. If the path is relative, it will be relative to the
            current working directory. Mandatory
        :param port: Port to listen for websocket requests from.
        :param low_level_debug: If True, wss traffic will be written to the console.
        :param whitelist: Comma separated list of sites that can connect to the server.
            For example:
                - *.shotgunstudio.com (default)
                - some-site.shotgunstudio.com
                - localserver.localnetwork.com
                - some-site.shotgunstudio.com,some-other-site.shotgunstudio.com
        """
        self._port = port or self._DEFAULT_PORT
        self._keys_path = keys_path or self._DEFAULT_KEYS_PATH
        self._whitelist = whitelist or self._DEFAULT_WHITELIST
        self._debug = low_level_debug

        if not os.path.exists(keys_path):
            raise MissingCertificateError(keys_path)

        twisted = logger.get_logger("twisted")

        if self._debug:
            # When running the server in low_level_debug mode, the twisted framework will print out
            # data exchanged with the client. Unfortunately, there's no way to filter out that
            # information from since it is being logged at the INFO level just like regular Twisted
            # logs.
            # Warn the user that this is dangerous.
            twisted.warning("-" * 30)
            twisted.warning(
                "YOU ARE LOGGING TWISTED INTERNAL MESSAGES TO THE CONSOLE. MAKE SURE YOU CLOSE THE "
                "CONSOLE AFTER RUNNING THE APPLICATION AS TWISTED CAN LOG SENSITIVE INFORMATION."
            )
            twisted.warning("-" * 30)

        # This will take the Twisted logging and forward it to Python's logging.
        self._observer = log.PythonLoggingObserver(twisted.name)
        self._observer.start()

    def get_logger(self):
        """
        :returns: The python logger root for the framework.
        """
        return logger.get_logger()

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
        cert_crt_path, cert_key_path = certificates.get_certificate_file_names(self._keys_path)

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
