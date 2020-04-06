# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import struct
import os
import sys
import traceback

from .desktop_message_box import DesktopMessageBox

logger = None


class Settings(object):
    """
    Reads the optionally configured configuration file present in the Desktop
    installer package. This file is in the root of the installed application folder on
    Linux and Windows and in Contents/Resources on MacOSX.

    The configuration file should have the following format:
    [BrowserIntegration]
    port=9000
    debug=1
    certificate_folder=/path/to/the/certificate
    """

    _DEFAULT_PORT = 9000
    _DEFAULT_LOW_LEVEL_DEBUG_VALUE = False

    _BROWSER_INTEGRATION = "BrowserIntegration"
    _PORT_SETTING = "port"
    _LOW_LEVEL_DEBUG_SETTING = "low_level_debug"
    _CERTIFICATE_FOLDER_SETTING = "certificate_folder"
    _ENABLED = "enabled"

    _WHITELIST = "whitelist"

    def __init__(self, user_settings, default_certificate_folder):
        """
        Constructor.

        If the configuration file doesn't not exist, the configuration
        object will return the default values.

        :param location: Path to the configuration file. If ``None``, Toolkit's sgtk.util.UserSettings module
            will be used instead to retrieve the values.
        :param default_certificate_folder: Default location for the certificate file. This value
            is overridable for each app that can use this settings object.
        """
        self._port = (
            user_settings.get_integer_setting(
                self._BROWSER_INTEGRATION, self._PORT_SETTING
            )
            or self._DEFAULT_PORT
        )

        self._low_level_debug = (
            user_settings.get_boolean_setting(
                self._BROWSER_INTEGRATION, self._LOW_LEVEL_DEBUG_SETTING
            )
            or self._DEFAULT_LOW_LEVEL_DEBUG_VALUE
        )

        self._certificate_folder = (
            user_settings.get_setting(
                self._BROWSER_INTEGRATION, self._CERTIFICATE_FOLDER_SETTING
            )
            or default_certificate_folder
        )

        self._integration_enabled = user_settings.get_boolean_setting(
            self._BROWSER_INTEGRATION, self._ENABLED
        )
        self._whitelist = (
            user_settings.get_setting(self._BROWSER_INTEGRATION, self._WHITELIST)
            or "*.shotgunstudio.com"
        )

    @property
    def port(self):
        """
        :returns: The port to listen on for incoming websocket requests.
        """
        return self._port

    @property
    def integration_enabled(self):
        """
        :returns: True if the browser integration is enabled, False otherwise.
        """
        return (
            self._integration_enabled if self._integration_enabled is not None else True
        )

    @property
    def low_level_debug(self):
        """
        :returns: True if the server should run in low level debugging mode. False otherwise.
        """
        return self._low_level_debug

    @property
    def certificate_folder(self):
        """
        :returns: Path to the certificate location.
        """
        return self._certificate_folder

    @property
    def whitelist(self):
        """
        :returns: The connection whitelist.
        """
        return self._whitelist

    def dump(self, logger):
        """
        Dumps all the settings into the logger.
        """
        logger.info("Integration enabled: %s" % self.integration_enabled)
        logger.info("Certificate folder: %s" % self.certificate_folder)
        logger.info("Low level debug: %s" % self.low_level_debug)
        logger.info("Port: %d" % self.port)
        logger.info("Whitelist: %s" % self.whitelist)


def __is_64bit_python():
    """
    :returns: True if 64-bit Python, False otherwise.
    """
    return struct.calcsize("P") == 8


def init_websockets(splash, app_bootstrap, settings, global_logger):
    """
    Initializes the local websocket server.

    :pram splash: Splash widget.
    :param app_bootstrap: The application bootstrap instance.
    :param settings: The application's settings.
    :param logger: Python logger instance. This logger is passed down from the caller
        since the core that can be imported at this point isn't guaranteed to support
        logging.

    :returns: The tk_framework_desktopserver.Server instance and a boolean indicating if the
        Desktop should keep launching.
    """
    global logger
    logger = global_logger

    if not __is_64bit_python():
        # Do not import if Python is not 64-bits
        logger.warning("Interpreter is not 64-bits, can't load desktop server")
        return None, True

    integration_settings = Settings(
        settings,
        os.path.join(
            app_bootstrap.get_shotgun_desktop_cache_location(), "config", "certificates"
        ),
    )

    integration_settings.dump(logger)

    if not integration_settings.integration_enabled:
        # Do not import if server is disabled.
        logger.info("Integration was disabled in configuration file.")
        return None, True

    # Add the desktop server into the PYTHONPATH
    if "SGTK_DESKTOP_SERVER_LOCATION" in os.environ:
        path = os.path.join(os.environ["SGTK_DESKTOP_SERVER_LOCATION"])
        path = os.path.expanduser(os.path.expandvars(path))
    else:
        path = os.path.normpath(
            os.path.join(os.path.split(__file__)[0], "..", "server")
        )
    path = os.path.join(path, "python")
    sys.path.insert(0, path)
    logger.info("Using tk-framework-desktopserver from '%s'", path)

    # First try to import the framework. If it fails, let the user decide if the Desktop should
    # keep launching.
    try:
        splash.show()
        splash.set_message("Initializing browser integration")
        # Import framework
        import tk_framework_desktopserver
    except Exception as e:
        return (
            None,
            __handle_unexpected_exception_during_websocket_init(
                splash, app_bootstrap, e
            ),
        )

    # We need to break these two try's because if we can't import the tk-framework-desktopserver
    # module we won't be able to catch any exception types from that module.
    try:
        # Makes sure that the certificate has been created on disk and registered with the OS (or browser on Linux).
        __ensure_certificate_ready(
            app_bootstrap,
            tk_framework_desktopserver,
            integration_settings.certificate_folder,
        )

        # Launch the server
        server = tk_framework_desktopserver.Server(
            port=integration_settings.port,
            low_level_debug=integration_settings.low_level_debug,
            whitelist=integration_settings.whitelist,
            keys_path=integration_settings.certificate_folder,
        )

        # This might throw a PortBusyError.
        server.start()

        splash.hide()
        return server, True
    except tk_framework_desktopserver.PortBusyError:
        # Gracefully let the user know that the Desktop might already be running.
        logger.exception("Could not start the browser integration:")
        splash.hide()
        return (
            None,
            __query_quit_or_continue_launching(
                "Browser integration failed to start because port %d is already in use. The Shotgun "
                "Desktop may already be running on your machine."
                % integration_settings.port,
                app_bootstrap,
            ),
        )
    except Exception as e:
        return (
            None,
            __handle_unexpected_exception_during_websocket_init(
                splash, app_bootstrap, e
            ),
        )


def __handle_unexpected_exception_during_websocket_init(splash, app_bootstrap, ex):
    """
    Handles unexpected exception during websocket initialization. If hides the splashscreen
    and asks the user if we wants to keep launching the Desktop.

    :param splash: Splashscreen widget.
    :param app_bootstrap: The application bootstrap instance.
    :param ex: The unexpected exception.

    :returns: True if the user wants to continue, False otherwise.
    """
    logger.exception("Could not start the browser integration:")
    splash.hide()
    return __query_quit_or_continue_launching(
        "Browser integration failed to start. It will not be available if "
        "you continue.\n"
        "Error: %s" % str(ex),
        app_bootstrap,
    )


def __query_quit_or_continue_launching(msg, app_bootstrap):
    """
    Asks the user if he wants to keep launching the Desktop or not.

    :param msg: Message to display to the user.
    :param app_bootstrap: The application bootstrap instance.

    :returns: True if the user wants to continue, False otherwise.
    """
    warning_box = DesktopMessageBox(
        DesktopMessageBox.Warning,
        "Browser Integration error",
        "%s\n" "Do you want to continue launching the Shotgun Desktop?" % msg,
        DesktopMessageBox.Yes,
        DesktopMessageBox.Yes | DesktopMessageBox.No,
        "If you drop us an email at support@shotgunsoftware.com, we'll help you diagnose "
        "the issue.\n\n"
        "For more information, see the log file at %s.\n\n"
        "%s" % (app_bootstrap.get_logfile_location(), traceback.format_exc()),
    )
    warning_box.button(DesktopMessageBox.Yes).setText("Continue")
    warning_box.button(DesktopMessageBox.No).setText("Quit")

    return warning_box.exec_() == DesktopMessageBox.Yes


def __ensure_certificate_ready(
    app_bootstrap, tk_framework_desktopserver, certificate_folder
):
    """
    Ensures that the certificates are created and registered. If something is amiss, then the
    configuration is fixed.

    :params app_bootstrap: The application bootstrap.
    :param tk_framework_desktopserver: The desktopserver framework.
    :param certificate_folder: Folder where the certificates are stored.

    :returns: True is the certificate is ready, False otherwise.
    """
    cert_handler = tk_framework_desktopserver.get_certificate_handler(
        certificate_folder
    )

    # We only warn once.
    warned = False
    # Make sure the certificates exist.
    if not cert_handler.exists():
        logger.info("Certificate doesn't exist.")
        # Start by unregistering certificates from the keychains, this can happen if the user
        # wiped his shotgun/desktop/config/certificates folder.
        if cert_handler.is_registered():
            logger.info("Unregistering lingering certificate.")
            # Warn once.
            __warn_for_prompt()
            warned = True
            cert_handler.unregister()
            logger.info("Unregistered.")
        # Create the certificate files
        cert_handler.create()
        logger.info("Certificate created.")
    else:
        logger.info("Certificate already exist.")

    # Check if the certificates are registered with the keychain.
    if not cert_handler.is_registered():
        logger.info("Certificate not registered.")

        # Only if we've never been warned before.
        if not warned:
            __warn_for_prompt()
        cert_handler.register()
        logger.info("Certificate registered.")
    else:
        logger.info("Certificates already registered.")
    return True


def __get_certificate_prompt(keychain_name, action):
    """
    Generates the text to use when alerting the user that we need to register the certificate.

    :param keychain_name: Name of the keychain-like entity for a particular OS.
    :param action: Description of what the user will need to do when the OS prompts the user.

    :returns: String containing an error message formatted
    """
    return (
        "The Shotgun Desktop needs to update the security certificate list from your %s before "
        "it can turn on the browser integration.\n"
        "%s" % (keychain_name, action)
    )


def __warn_for_prompt():
    """
    Warn the user he will be prompted.
    """
    if sys.platform == "darwin":
        DesktopMessageBox.information(
            "Shotgun browser integration",
            __get_certificate_prompt(
                "keychain",
                "You will be prompted to enter your username and password by MacOS's keychain "
                "manager in order to proceed with the updates.",
            ),
        )
    elif sys.platform == "win32":
        DesktopMessageBox.information(
            "Shotgun browser integration",
            __get_certificate_prompt(
                "Windows certificate store",
                "Windows will now prompt you to accept one or more updates to your certificate store.",
            ),
        )
    # On Linux there's no need to prompt. It's all silent.
