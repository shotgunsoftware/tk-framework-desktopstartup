# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from __future__ import with_statement
import os
import sys
import subprocess
import logging
from .errors import CertificateRegistrationFailed

from OpenSSL import crypto


class _CertificateHandler(object):
    """
    Handles creation and registration of the websocket certificate.
    """

    def __init__(self, certificate_folder):
        """
        Constructor.
        """
        self._logger = logging.getLogger("tk-framework-desktopserver.certificate")
        self._cert_path = os.path.join(certificate_folder, "server.crt")
        self._key_path = os.path.join(certificate_folder, "server.key")

    def exists(self):
        """
        :returns: True if the certificate exists on disk, False otherwose.
        """
        return os.path.exists(self._cert_path) and os.path.exists(self._key_path)

    def create(self):
        """
        Creates a self-signed certificate.
        """

        # This code is heavily inspired from:
        # https://skippylovesmalorie.wordpress.com/2010/02/12/how-to-generate-a-self-signed-certificate-using-pyopenssl/

        # Clean the certificate destination
        self._clean_folder_for_file(self._cert_path)
        self._clean_folder_for_file(self._key_path)

        # create a key pair
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "California"
        cert.get_subject().L = "San Rafael"
        cert.get_subject().O = "Autodesk"
        cert.get_subject().OU = "Shotgun Software"
        cert.get_subject().CN = "localhost"
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        # 10 years should be enough for everyone
        cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha256')

        # Write the certificate and key back to disk.
        self._write_file(self._cert_path, crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        self._write_file(self._key_path, crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

    def register(self):
        """
        Registers the file passed in in the certificate store. Any errors are logged.

        :returns: True on success, False otherwise.
        """
        raise NotImplemented("'_CertificateInterface.register' not implemented!")

    def _check_call(self, ctx, cmd):
        """
        Runs a process and logs it's output if the return code was not 0.

        :param ctx: string identifying the goal of the command. Will complete this sentence:
            "There was a problem %s" %% ctx
        :param cmd: Command to run.

        :returns: True if the process returns 0, False otherwise.
        """
        try:
            # Sometimes the is_registered_cmd will output Shotgun Software and sometimes it will
            # only output the pretty name Shotgun Desktop Integration, so searching for Shotgun is 
            # good enough.
            subprocess.check_call(cmd, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError, e:
            self._logger.exception("There was a problem %s" % ctx)
            self._logger.info("Output:\n%s" % e.output)
            raise CertificateRegistrationFailed("There was a problem %s" % ctx)

    def is_registered(self):
        """
        Checks if a certificate is registered in the certificate store. Any errors are logged.

        :returns: True if the certificate is registered, False otherwise.
        """
        try:
            # Sometimes the is_registered_cmd will output Shotgun Software and sometimes it will
            # only output the pretty name Shotgun Desktop Integration, so searching for Shotgun is
            # good enough.
            return "Shotgun" in subprocess.check_output(self._get_is_registered_cmd(), stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError, e:
            self._logger.exception("There was a problem validating if a certificate was installed.")
            self._logger.info("Output:\n%s" % e.output)
            raise CertificateRegistrationFailed("There was a problem validating if a certificate was installed.")

    def unregister(self):
        """
        Unregisters a certificate from the store. Any errors are logged.

        :returns: True if the certificate was unregistered, False otherwise.
        """
        raise NotImplemented("'_CertificateInterface.unregister' not implemented!")

    def _get_is_registered_cmd(self):
        """
        Returns the command to execute to determine if a certificate is registered. Invoked by 
        is_registered.

        :retuns: The command string to execute.
        """
        raise NotImplemented("'_CertificateInterface._get_is_registered_cmd' not implemented!")

    def _write_file(self, path, content):
        """
        Writes text to a file.

        :param path: Path to the file.
        :param content: Text to write to disl.
        """
        old_umask = os.umask(0077)
        try:
            with open(path, "wt") as f:
                f.write(content)
        finally:
            os.umask(old_umask)

    def _clean_folder_for_file(self, filepath):
        """
        Makes sure the folder exists for a given file and that the file doesn't exist.

        :param filepath: Path to the file we want to make sure the parent directory
                         exists.
        """

        folder = os.path.dirname(filepath)
        if not os.path.exists(folder):
            old_umask = os.umask(0077)
            try:
                os.makedirs(folder, 0700)
            finally:
                os.umask(old_umask)
        if os.path.exists(filepath):
            os.remove(filepath)


class _LinuxCertificateHandler(_CertificateHandler):
    """
    Handles creation and registration of the websocket certificate on Linux.
    """

    _PKI_DB_PATH = "\"sql:$HOME/.pki/nssdb\""
    _CERTIFICATE_PRETTY_NAME = "\"Shotgun Desktop Integration\""

    def _get_is_registered_cmd(self):
        """
        :returns: Command string to list the certificates in the ~/.pki certificate store.
        """
        # Adds the certificate for Chrome.
        # FIXME: For Firefox, each profile stores it's own certificates. Maybe we should always
        # return False here and let the register method iterate over all the know locations. For
        # more about Firefox profiles, read: http://kb.mozillazine.org/Profiles.ini_file
        # Also, we could use
        # http://k0s.org/mozilla/hg/ProfileManager/file/145e111903d2/profilemanager to parse the
        # profiles.ini file, but I'm not a lawyer and I'm not sure if the Mozilla Public License is
        # something we can use.
        return "certutil -L -d %s" % self._PKI_DB_PATH

    def register(self):
        """
        Registers a certificate in the ~/.pki certificate store. Any errors are logged.

        :returns: True on success, False on failure.
        """
        return self._check_call(
            "registering certificate",
            "certutil -A -d %s -i \"%s\" -n %s -t \"TC,C,c\"" % (
                self._PKI_DB_PATH, self._cert_path, self._CERTIFICATE_PRETTY_NAME
            )
        )

    def unregister(self):
        """
        Unregisters a certificate from the ~/.pki certificate store. Any errors are logged.

        :returns: True on success, False on failure.
        """
        return self._check_call(
            "unregistering certificate",
            "certutil -D -d %s -n %s" % (self._PKI_DB_PATH, self._CERTIFICATE_PRETTY_NAME)
        )


class _WindowsCertificateHandler(_CertificateHandler):
    """
    Handles creation and registration of the websocket certificate on Windows.
    """

    def _get_is_registered_cmd(self):
        """
        :returns: Command string to list the certificates in the Windows root certificate store.
        """
        # Don't provide the certificate name after the store name, if the certificate is not listed
        # the process will return an error code. We'll let is_register parse the output instead.
        return "certutil -user -store root"

    def register(self):
        """
        Registers a certificate in the Windows root certificate store. Any errors are logged.

        :returns: True on success, False on failure.
        """
        return self._check_call(
            "registering certificate",
            ("certutil", "-user", "-addstore", "root", self._cert_path.replace("/", "\\"))
        )

    def unregister(self):
        """
        Unregisters a certificate from the Windows root certificate store. Any errors are logged.

        :returns: True on success, False on failure.
        """
        # FIXME: Unregistering by the certificate name is wonky, since other certificates might
        # have the same name. Maybe we should write the sha to disk and delete using that as
        # a query (certutil -user -delstore root sha1).
        return self._check_call(
            "unregistering certificate",
            ("certutil", "-user", "-delstore", "root", "localhost")
        )


class _MacCertificateHandler(_CertificateHandler):
    """
    Handles creation and registration of the websocket certificate on MacOS.
    """

    def register(self):
        """
        :returns: Command string to list the certificates in the keychain.
        """
        # FIXME: The SecurityAgent from Apple which prompts for the password to allow an update to the
        # trust settings can sometime freeze. Read more at:
        # https://discussions.apple.com/thread/6300609
        # In order to unfreeze it, do "sudo kill SecurityAgent". Best way to avoid a second freeze
        # is to reboot. Note that doing that trusting the certificate via the UI exposes the same
        # issue.
        return self._check_call(
            "registering certificate",
            "security add-trusted-cert -k ~/Library/Keychains/login.keychain -r trustRoot  \"%s\"" %
            self._cert_path
        )

    def _get_is_registered_cmd(self):
        """
        Registers a certificate in the keychain. Any errors are logged

        :returns: True on success, False on failure.
        """
        # This could list more than one certificate, but since we're grepping for Shotgun it's going
        # to be fine.
        return "security find-certificate -a -e localhost"

    def unregister(self):
        """
        Unregisters a certificate from the keychain. Any errors are logged.

        :returns: True on success, False on failure.
        """
        # FIXME: Unregistering by the certificate name is wonky, since other certificates might
        # have the same name. Maybe we should write the sha to disk and delete using that as
        # a query (security delete-certificate -Z sha1 -t).
        if self.is_registered():
            return self._check_call(
                "removing trusted certificate",
                "security delete-certificate -c localhost -t"
            )
        else:
            return True


def get_certificate_handler(certificate_folder):
    """
    :param certificate_folder: Folder where the certificate is stored.
    :returns: The platform specific certificate handler to get, create or delete the websocket
        certificate.
    """
    if sys.platform.startswith("linux"):
        return _LinuxCertificateHandler(certificate_folder)
    elif sys.platform == "darwin":
        return _MacCertificateHandler(certificate_folder)
    elif sys.platform == "win32":
        return _WindowsCertificateHandler(certificate_folder)
    else:
        raise RuntimeError("Platform '%s' not supported!" % sys.platform)
