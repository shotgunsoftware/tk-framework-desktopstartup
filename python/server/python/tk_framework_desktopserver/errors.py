# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
All custom exceptions that the browser integration can emit are here.
"""


class BrowserIntegrationError(Exception):
    """
    Base class for all browser integration errors.
    """
    pass


class MissingCertificateError(BrowserIntegrationError):
    """
    Base class for all browser integration errors.
    """
    pass


    """
    """
    pass


class PortBusyError(BrowserIntegrationError):
    """
    Exception raised when the TCP port is busy.
    """
    pass


class CertificateRegistrationFailed(BrowserIntegrationError):
    """
    Exception raised when something goes wrong while registering or
    unregistering a certificate.
    """
    pass
