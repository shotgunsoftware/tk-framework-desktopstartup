# Copyright (c) 2015 Shotgun Software Inc.
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

# Name of the keychain per platform. Note that Linux doesn't have any entries because there is no prompting
# done when adding and removing to the Chrome/Firefox 'keychain'.
__keychain_name = {
    "win32": "Windows certificate store",
    "darwin": "keychain"
}

# Explains what the user will be required to do after typing enter.
__keychain_prompting = {
    "win32": "Windows will now prompt you to accept an update to your certificate store.",
    "darwin": (
        "You will be prompted to enter your username and password by MacOS's keychain "
        "manager in order to proceed with the update."
    )
}


def __warn_for_prompt(removal):
    """
    Warn the user he will be prompted.
    """
    # On Linux there's no need to prompt. It's all silent.
    if sys.platform.startswith("linux"):
        return
    if removal:
        raw_input(
            "This script needs to remove a security certificate from your %s.\n"
            "%s\nPress ENTER to continue." % (__keychain_name[sys.platform], __keychain_prompting[sys.platform])
        )
    else:
        raw_input(
            "This script needs to install a security certificate into your %s before "
            "it can turn on the browser integration.\n"
            "%s\nPress ENTER to continue." % (__keychain_name[sys.platform], __keychain_prompting[sys.platform])
        )


def __remove_certificate(certificate_folder, logger):
    """
    Ensures that the certificates are created and registered. If something is amiss, then the
    configuration is fixed.

    :param certificate_folder: Folder where the certificates are stored.
    """

    cert_handler = get_certificate_handler(certificate_folder)

    # Removes the certificate from the OS/browser certificate database.
    if cert_handler.is_registered():
        logger.debug("Removing certificate from database.")
        __warn_for_prompt(removal=True)
        cert_handler.unregister()
        logger.info("The certificate is now unegistered.")
    else:
        logger.info("No certificate was registered.")

    # Removes the actual certificate files on disk.
    if cert_handler.exists():
        logger.debug("Certificate was found on disk at %s." % certificate_folder)
        cert_handler.remove_files()
        logger.info("The certificate was removed at %s." % certificate_folder)
    else:
        logger.info("No certificate was found on disk at %s." % certificate_folder)


def __create_certificate(certificate_folder, logger):
    """
    Ensures that the certificates are created and registered. If something is amiss, then the
    configuration is fixed.

    :param certificate_folder: Folder where the certificates are stored.
    """

    cert_handler = get_certificate_handler(certificate_folder)

    # We only warn once.
    warned = False
    # Make sure the certificates exist.
    if not cert_handler.exists():
        logger.debug("Certificate doesn't exist on disk.")
        # Start by unregistering certificates from the keychains, this can happen if the user
        # wiped his certificates folder.
        if cert_handler.is_registered():
            # Warn once.
            __warn_for_prompt(removal=False)
            logger.debug("Unregistering dangling certificate from database...")
            warned = True
            cert_handler.unregister()
            logger.debug("Done.")
        # Create the certificate files
        logger.debug("About to create the certificates...")
        cert_handler.create()
        logger.info("Certificate created at %s." % certificate_folder)
    else:
        logger.info("Certificate already exist on disk at %s." % certificate_folder)

    # Check if the certificates are registered with the keychain.
    if not cert_handler.is_registered():
        logger.debug("Certificate is not currently registered in the keychain.")
        # Only if we've never been warned before.
        if not warned:
            __warn_for_prompt(removal=False)
        cert_handler.register()
        logger.info("Certificate is now registered .")
    else:
        logger.info("Certificate is already registered.")


def __parse_options():
    """
    Parses the command line for options.

    :returns An OptionParser with attributes debug, remove and configuration.
    """
    parser = optparse.OptionParser()
    parser.add_option(
        "--debug", action="store_true", default=False,
        help="prints debugging message from the certificate generation"
    )
    parser.add_option(
        "--remove", action="store_true", default=False,
        help="removes the certificate from disk and from the certificate database"
    )
    parser.add_option(
        "-c", "--configuration", action="store", default=None,
        help="location of the configuration file")

    options, _ = parser.parse_args()

    return options


def main():
    """
    Main.
    """
    # Configure the app.
    options = __parse_options()
    # Create the logger
    app_logger = logger.get_logger(options.debug)

    app_settings = settings.get_settings(options.configuration)

    try:
        if options.remove:
            __remove_certificate(app_settings.certificate_folder, app_logger)
        else:
            __create_certificate(app_settings.certificate_folder, app_logger)
    except BrowserIntegrationError, e:
        if options.debug:
            app_logger.exception("There was an error handling the certificate.")
        else:
            app_logger.error(e)


if __name__ == '__main__':
    # Add the modules files to PYTHOHPATH
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../python"))
    from tk_framework_desktopserver import get_certificate_handler, BrowserIntegrationError
    import settings
    import logger
    main()
