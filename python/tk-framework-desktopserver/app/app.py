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

import sys
import optparse
import itertools


def _tokenize_args(args):
    """
    Tokenize the strings assigned to each argument to split them by commas so that we
    can use comma separated strings for arguments.

    :param args: Array of strings of each command line argument

    :returns: A flat list of individual strings, without commas.
    """
    return list(itertools.chain(
        *[arg.split(",") for arg in args]
    ))


if __name__ == '__main__':
    """
    Simple application for client/server development and testing.

    Example usage: python app.py --debug

    Server TODO:
        - Test on all Platforms
            - Dependencies:
                [cryptography, cffi, six, pycparser]
                [service-identity, pyasn1, pyasn1-modules, pyopens, sl, characteristic]   --> service_identity for test_client only?

            - General issues with test client
                - pip install service-identity
            - Linux issues
                For cffi:
                    yum install libffi-devel
                    yum install python-devel
                    yum install openssl-devel
                    pip install cffi
                - When do we actually need both files/folder selection?
        - uft-8 unit testing internationalization
            - Internationalization works fine, except for this case: /Users/rivestm/tmp 普通话/ 國語/ 華語.txt, were filename is
              'tmp 普通话/ 國語/ 華語.txt'. The '/' should be encoded by the client differently, and possibly decoded
              differently on the server too.
    """
    sys.path.append("../python")

    from tk_server import Server
    from tk_server import shotgun_api

    from twisted.python import log

    parser = optparse.OptionParser()
    parser.add_option(
        "--debug", action="store_true", default=False,
        help="prints debugging message from the server on the console"
    )
    parser.add_option(
        "--local-server", action="store_true", default=False,
        help="also runs the local server on port 8080 to mock calls from the browser."
    )
    parser.add_option(
        "--fake-errors", action="append", default=[],
        help="list of server calls to fake an error on"
    )
    parser.add_option(
        "--block", action="append", default=[],
        help="list of server calls that will block until ENTER is pressed."
    )

    options, _ = parser.parse_args()

    options.fake_errors = _tokenize_args(options.fake_errors)
    options.block = _tokenize_args(options.block)

    if options.fake_errors:
        print "Faking errors for %s" % ", ".join(options.fake_errors)

    if options.block:
        print "Blocking calls for %s" % ", ".join(options.block)

    # Make a local copy of the handle because we are about to overwrite it.
    ShotgunAPI = shotgun_api.ShotgunAPI

    class ShotgunAPIProxy(object):
        def __init__(self, *args, **kwargs):
            self._shotgun_api = ShotgunAPI(*args, **kwargs)

        def __getattr__(self, name):
            if name in options.fake_errors:
                raise Exception("Fake error for '%s'." % name)
            elif name in options.block:
                raw_input("Blocking %s. Press ENTER to unblock." % name)
                print "Unblocked"
            return getattr(self._shotgun_api, name)

    shotgun_api.ShotgunAPI = ShotgunAPIProxy

    if options.debug:
        log.startLogging(sys.stdout)

    keys_folder = "../resources/keys"

    server = Server()
    server.start(options.debug, keys_folder, True)

    # Enables CTRL-C to kill this process even tough Qt doesn't know how to play nice with Python.
    # As per this stack overflow comment
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    from PySide import QtGui
    app = QtGui.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.exec_()
