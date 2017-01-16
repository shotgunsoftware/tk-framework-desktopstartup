# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from __future__ import absolute_import

import os
import sys
import time
import subprocess
import struct
import traceback

# initialize logging
import logging
import shotgun_desktop.splash

logger = logging.getLogger("tk-desktop.startup")
logger.info("------------------ Desktop Engine Startup ------------------")


def add_to_python_path(bundled_path, env_var_override, module_name):
    """
    Adds a packaged module into the Python Path unless an environment variable
    overrides the setting.

    :param str bundled_path: Path to the bundled code.
    :param env_var_override: Name of the environment variable that can override that path.
    :param module_name: Friendly name of the module.
    """
    if env_var_override in os.environ:
        path = os.path.join(os.environ[env_var_override])
        path = os.path.expanduser(os.path.expandvars(path))
    else:
        path = os.path.normpath(os.path.join(os.path.split(__file__)[0], bundled_path))
    path = os.path.join(path, "python")
    sys.path.insert(0, path)
    logger.info("Using %s from '%s'", module_name, path)

# Add Toolkit and desktop server to the path.
add_to_python_path(os.path.join("..", "tk-core", ), "SGTK_CORE_LOCATION", "tk-core")
add_to_python_path(os.path.join("..", "server"), "SGTK_DESKTOP_SERVER_LOCATION", "tk-framework-desktopserver")

# now proceed with non builtin imports
from PySide import QtCore, QtGui

import shotgun_desktop.paths
from shotgun_desktop.turn_on_toolkit import TurnOnToolkit
from shotgun_desktop.desktop_message_box import DesktopMessageBox
from shotgun_desktop.upgrade_startup import upgrade_startup
from shotgun_desktop.location import get_location
from shotgun_desktop.settings import Settings
from shotgun_desktop.systray_icon import ShotgunSystemTrayIcon
from distutils.version import LooseVersion

from shotgun_desktop.errors import (ShotgunDesktopError, RequestRestartException, UpgradeEngineError,
                                    ToolkitDisabledError, UpgradeCoreError,
                                    InvalidPipelineConfiguration)


def __is_64bit_python():
    """
    :returns: True if 64-bit Python, False otherwise.
    """
    return struct.calcsize("P") == 8


def __toolkit_supports_authentication_module(sgtk):
    """
    Tests if the given Toolkit API supports the shotgun_authentication module.

    :param sgtk: The Toolkit API handle.

    :returns: True if the shotgun_authentication module is supported, False otherwise.
    """
    # if the authentication module is not supported, this method won't be present on the core.
    return hasattr(sgtk, "set_authenticated_user")


def __desktop_engine_supports_authentication_module(engine):
    """
    Tests if the engine supports the login based authentication. All versions above 2.0.0 supports
    login based authentication.

    :param engine: The desktop engine to test.

    :returns: True if the engine supports the authentication module, False otherwise.
    """
    if engine.version.lower() == 'undefined':
        logger.warning("The version of the tk-desktop engine is undefined.")
        return True
    return LooseVersion(engine.version) >= "v2.0.0"


def __supports_pipeline_configuration_upgrade(pipeline_configuration):
    """
    Tests if the given pipeline configuration supports the None project id.

    :param sgtk: A pipeline configuration.

    :returns: True if the pipeline configuration can have a None project, False otherwise.
    """
    # if the authentication module is not supported, this method won't be present on the core.
    return hasattr(pipeline_configuration, "convert_to_site_config")


def _assert_toolkit_enabled(splash, connection):
    """
    Returns the path to the pipeline configuration for a given site.

    :param splash: Splash dialog
    """
    # get the pipeline configuration for the site we are logged into
    while True:
        pc_schema = connection.schema_entity_read().get("PipelineConfiguration")
        if pc_schema is not None:
            break

        # Toolkit is not turned on show the dialog that explains what to do
        splash.hide()
        dialog = TurnOnToolkit(connection)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        results = dialog.exec_()

        if results == dialog.Rejected:
            # dialog was canceled, raise the exception and let the main exception handler deal
            # with it.
            raise ToolkitDisabledError()

    splash.show()


def __init_app():
    """
    Initializes UI components.

    :returns: The tupple (QApplication instance, shogun_desktop.splash.Slash instance).
    """
    logger.debug("Creating QApp and splash screen")
    # start up our QApp now
    return QtGui.QApplication(sys.argv), shotgun_desktop.splash.Splash()


class SystrayEventLoop(QtCore.QEventLoop):
    """
    Local event loop for the system tray. The return value of _exec() indicates what the user picked in the
    menu.
    """

    CLOSE_APP, LOGIN = range(0, 2)

    def __init__(self, systray, parent=None):
        """
        Constructor
        """
        QtCore.QEventLoop.__init__(self, parent)
        systray.login.connect(self._login)
        systray.quit.connect(self._quit)

    def _login(self):
        """
        Called when "Login" is selected. Exits the loop.
        """
        self.exit(self.LOGIN)

    def _quit(self):
        """
        Called when "Quit" is selected. Exits the loop.
        """
        self.exit(self.CLOSE_APP)

    def exec_(self):
        """
        Execute the local event loop. If CmdQ was hit in the past, it will be handled just as if the
        user had picked the Quit menu.

        :returns: The exit code for the loop.
        """
        code = QtCore.QEventLoop.exec_(self)
        # Somebody requested the app to close, so pretend the close menu was picked.
        if code == -1:
            return self.CLOSE_APP
        elif code in [self.CLOSE_APP, self.LOGIN]:
            return code
        else:
            raise Exception("Unexpected return code in local event loop: %s" % code)


def __run_with_systray():
    """
    Creates a systray and runs a local event loop to process events for that systray.

    :returns: SystrayEventLoop.LOGIN if the user clicked Login, SystrayEventLoop.CLOSE_APP
        is the user clicked Quit.
    """
    systray = ShotgunSystemTrayIcon()
    systray.show()
    systray.showMessage(
        "Shotgun",
        "Browser integration is running in the background. Click the Shotgun icon to sign in.",
        QtGui.QSystemTrayIcon.Information,
        5000
    )
    # Executes until user clicks on the systray and chooses Login or Quit.
    return SystrayEventLoop(systray).exec_()


def __optional_state_cleanup(splash, shotgun_authenticator, app_bootstrap):
    """
    Cleans the Desktop state if the alt key is pressed. Restarts the Desktop when done.

    :param splash: Splash screen widget.
    :param shotgun_authenticator: Shotgun authenticator used to logout if alt is pressed.
    :params app_bootstrap: The application bootstrap.
    """
    # If the application was launched holding the alt key, log the user out.
    if (QtGui.QApplication.queryKeyboardModifiers() & QtCore.Qt.AltModifier) == QtCore.Qt.AltModifier:
        logger.info("Alt was pressed, clearing default user and startup descriptor")
        shotgun_authenticator.clear_default_user()
        app_bootstrap.clear_startup_location()
        __restart_app_with_countdown(splash, "Desktop has been reinitialized.")


def __do_login(splash, shotgun_authenticator):
    """
    Asks for the credentials of the user or automatically logs the user in if the credentials are
    cached on disk.

    :param splash: Splash screen widget.
    :param shotgun_authenticator: Instance of the Shotgun Authenticator to use for login.

    :returns tank.authentication.ShotgunUser: The logged in user or None
    """
    from sgtk.authentication import AuthenticationCancelled
    logger.debug("Retrieving credentials")
    try:
        user = shotgun_authenticator.get_user()
        # It it possible the user's credentials are expired now. If we don't check for that
        # the user will be prompted to refresh their session by entering the password further
        # down the line when we start looking for a pipeline configuration.

        # In order to avoid this, we'll check to see if the credentials are expired.
        if user.are_credentials_expired():
            # If they are, we will clear them from the session cache...
            shotgun_authenticator.clear_default_user()
            # ... and ask again for a user. Since there is no more current user,
            # the authentication module will prompt for full set of credentials and site
            # information.
            user = shotgun_authenticator.get_user()
    except AuthenticationCancelled:
        return None

    return user


def __wait_for_login(
    splash,
    shotgun_authenticator,
    force_login
):
    """
    Runs the login dialog or the tray icon.

    :param splash: Splash screen widget.
    :param shotgun_authenticator: Instance of the Shotgun Authenticator to use for login.
    :params force_login: If True, the prompt will be shown automatically instead of going
        into tray mode.

    :returns tank.authentication.ShotgunUser: The authenticated user or None.
    """
    # The workflow is the following (fl stands for force login, du stands for default user)
    # 1. If you've never used the Desktop before, you will get the tray (!fl and !du)
    # 2. If you've used the desktop before but never logged in, you'll get the tray !fl and !du)
    # 3. If you've just logged out of desktop, you'll get the login screen (fl and !du)
    # 4. If you quit desktop and restart it later you won't see the tray and will auto-login (!fl and du)
    # 5. If you've cancelled the login screen at some point, you'll get the tray. (!fl and !du)
    if force_login is False and shotgun_authenticator.get_default_user() is None:
        if __run_with_systray() == SystrayEventLoop.CLOSE_APP:
            return None

    # Loop until there is a connection or the user wants to quit.
    while True:
        user = __do_login(splash, shotgun_authenticator)
        # If we logged in, return the connection.
        if user:
            return user
        else:
            # Now tell the user the Desktop is running in the tray.
            if __run_with_systray() == SystrayEventLoop.CLOSE_APP:
                return None


def __restart_app_with_countdown(splash, reason):
    """
    Restarts the app after displaying a countdown.

    :param splash: Splash dialog, used to display the countdown.
    :param reason: Reason to display in the dialog for the restart.

    :throws RequestRestartException: This method never returns and throws
    """
    # Provide a countdown so the user knows that the desktop app is being restarted
    # on purpose because of a core update. Otherwise, the user would get a flickering
    # splash screen that from the user point of view looks like the app is redoing work
    # it already did by mistake. This makes the behavior explicit.
    splash.show()
    splash.raise_()
    splash.activateWindow()
    for i in range(3, 0, -1):
        splash.set_message("%s Restarting in %d seconds..." % (reason, i))
        time.sleep(1)
    raise RequestRestartException()


def __extract_command_line_argument(arg_name):
    """
    Checks if an argument was specified from the command line and extracts it. Note that this method
    removes all instances of the argument from argv. Therefore, invoking the method twice with the
    same parameter will always return False the second time.

    :returns: True if the argument was set, False otherwise.
    """
    is_set = arg_name in sys.argv
    while arg_name in sys.argv:
        sys.argv.remove(arg_name)
    return is_set


def __launch_app(app, splash, user, app_bootstrap, server, settings):
    """
    Shows the splash screen, optionally downloads and configures Toolkit, imports it, optionally
    updates it and then launches the desktop engine.

    :param app: Application object for event processing.
    :param splash: Splash dialog to update user on what is currently going on
    :param user: Current ShotgunUser.
    :param app_bootstrap: Application bootstrap.
    :param server: The tk_framework_desktopserver.Server instance.
    :param settings: The application's settings.

    :returns: The error code to return to the shell.
    """
    # show the splash screen
    splash.show()

    import sgtk

    sgtk.set_authenticated_user(user)

    # Downloads an upgrade for the startup if available. The startup upgrade is independent from the
    # auto_path state and has its own logic for auto-updating or not, so move this outside the
    # if auto_path test.
    startup_updated = upgrade_startup(
        splash,
        sgtk,
        app_bootstrap
    )
    if startup_updated:
        __restart_app_with_countdown(splash, "Shotgun Desktop updated.")

    splash.set_message("Looking up site configuration.")
    app.processEvents()

    connection = user.create_sg_connection()

    _assert_toolkit_enabled(splash, connection)

    logger.debug("Getting the default site configuration.")
    pc_path, pc, toolkit_classic_required = shotgun_desktop.paths.get_default_site_config_root(connection)

    if toolkit_classic_required:
        return __toolkit_classic_bootstrap(
            app, splash, user, app_bootstrap, server, settings, pc_path, pc
        )
    else:
        return __zero_config_bootstrap(app, splash, user, app_bootstrap, server, settings)


def __bootstrap_toolkit_into_legacy_config(app, splash, user, pc):
    """
    Create a Toolkit instance by boostraping into the pipeline configuration.

    :param app: Application object for event processing.
    :param splash: Splash dialog to update user on what is currently going on
    :param user: Current ShotgunUser.
    :param app_bootstrap: Application bootstrap.
    :param server: The tk_framework_desktopserver.Server instance.
    :param settings: The application's settings.
    :param pc_path: Pipeline configuration path.
    :param pc: Pipeline configuration entity dictionary.

    :returns sgtk.Sgtk: An Sgtk instance.
    """
    import sgtk
    mgr = sgtk.bootstrap.ToolkitManager(user)

    def progress_callback(progress_value, message):
        """
        Called whenever toolkit reports progress.

        :param progress_value: The current progress value as float number.
                               values will be reported in incremental order
                               and always in the range 0.0 to 1.0
        :param message:        Progress message string
        """
        splash.set_message("[%02d]: %s" % (int(progress_value * 100), message))
        logger.debug(message)
        app.processEvents()

    mgr.do_shotgun_config_lookup = True
    mgr.progress_callback = progress_callback
    mgr.pipeline_configuration = pc["id"]
    return mgr.bootstrap_toolkit(None)


def __toolkit_classic_bootstrap(app, splash, user, app_bootstrap, server, settings, pc_path, pc):
    """
    Launches the Shotgun Desktop using Toolkit Classic

    :param app: Application object for event processing.
    :param splash: Splash dialog to update user on what is currently going on
    :param user: Current ShotgunUser.
    :param app_bootstrap: Application bootstrap.
    :param server: The tk_framework_desktopserver.Server instance.
    :param settings: The application's settings.
    :param pc_path: Pipeline configuration path.
    :param pc: Pipeline configuration entity dictionary.

    :returns: The error code to return to the shell.
    """
    # Creates a Toolkit instance pointing a Toolkit classic pipeline configuration. Note that this
    # also scopes the import of Toolkit so that we can reimport it later down the line to start
    # the engine.
    tk = __bootstrap_toolkit_into_legacy_config(app, splash, user, pc)

    # If the pipeline configuration found in Shotgun doesn't match what we have locally, we have a
    # problem.
    if pc["id"] != tk.pipeline_configuration.get_shotgun_id():
        raise InvalidPipelineConfiguration(pc, tk.pipeline_configuration)

    # If the pipeline configuration we got from Shotgun is not assigned to a project, we might have
    # some patching to be done to local site configuration.
    if pc["project"] is None:

        # make sure that the version of core we are using supports the new-style site configuration
        if not __supports_pipeline_configuration_upgrade(tk.pipeline_configuration):
            raise UpgradeCoreError(
                "Running a site configuration without the Template Project requires core v0.16.8 "
                "or higher.",
                pc_path
            )

        # If the configuration on disk is not the site configuration, update it to the site config.
        if not tk.pipeline_configuration.is_site_configuration():
            tk.pipeline_configuration.convert_to_site_config()

    # initialize the tk-desktop engine for an empty context
    splash.set_message("Resolving context...")
    app.processEvents()
    ctx = tk.context_empty()

    splash.set_message("Launching Engine...")
    app.processEvents()

    # Now start the engine. This import will import the new Toolkit we've bootstrapped into.
    import sgtk
    engine = sgtk.platform.start_engine("tk-desktop", tk, ctx)

    if not __desktop_engine_supports_authentication_module(engine):
        raise UpgradeEngineError(
            "This version of the Shotgun Desktop only supports tk-desktop engine 2.0.0 and higher.",
            pc_path
        )

    return __post_bootstrap_engine(sgtk, splash, app_bootstrap, server, engine)


def __zero_config_bootstrap(app, splash, user, app_bootstrap, server, settings):
    """
    Launch into the engine using the new zero config based bootstrap.

    :param app: Application object for event processing.
    :param splash: Splash dialog to update user on what is currently going on
    :param user: Current ShotgunUser.
    :param app_bootstrap: Application bootstrap.
    :param server: The tk_framework_desktopserver.Server instance.
    :param settings: The application's settings.

    :returns: The error code to return to the shell.
    """
    # The startup is up to date, now it's time to bootstrap Toolkit.
    import sgtk
    mgr = sgtk.bootstrap.ToolkitManager(user)

    def progress_callback(progress_value, message):
        """
        Called whenever toolkit reports progress.

        :param progress_value: The current progress value as float number.
                               values will be reported in incremental order
                               and always in the range 0.0 to 1.0
        :param message:        Progress message string
        """
        splash.set_message("%s: %s" % (progress_value, message))
        app.processEvents()

    mgr.base_configuration = os.environ.get(
        "SHOTGUN_CONFIG_FALLBACK_DESCRIPTOR",
        "sgtk:descriptor:app_store?name=tk-config-basic"
    )
    mgr.progress_callback = progress_callback
    mgr.plugin_id = "basic.desktop"

    engine = mgr.bootstrap_engine("tk-desktop")

    return __post_bootstrap_engine(sgtk, splash, app_bootstrap, server, engine)


def __post_bootstrap_engine(sgtk, splash, app_bootstrap, server, engine):

    # engine will take over logging
    app_bootstrap.tear_down_logging()

    # reset PYTHONPATH and PYTHONHOME if they were overridden by the application
    if "SGTK_DESKTOP_ORIGINAL_PYTHONPATH" in os.environ:
        os.environ["PYTHONPATH"] = os.environ["SGTK_DESKTOP_ORIGINAL_PYTHONPATH"]
    if "SGTK_DESKTOP_ORIGINAL_PYTHONHOME" in os.environ:
        os.environ["PYTHONHOME"] = os.environ["SGTK_DESKTOP_ORIGINAL_PYTHONHOME"]

    # and run the engine
    logger.debug("Running tk-desktop")
    startup_version = get_location(sgtk, app_bootstrap).get("version") or "Undefined"

    # Connect to the about to quit signal so that we can shut down the server automatically when the
    # desktop tries to quit the app.
    if server:
        QtGui.qApp.aboutToQuit.connect(lambda: server.tear_down())

    return engine.run(
        splash,
        version=app_bootstrap.get_version(),
        startup_version=startup_version,
        server=server
    )


def __handle_exception(splash, shotgun_authenticator, error_message):
    """
    Tears down the application, logs you out and displays an error message.

    :param splash: Splash dialog to hide.
    :param shotgun_authenticator: Used to clear the default user so we logout
        automatically on Desktop failure.
    :param error_message: Error string that will be displayed in a message box.
    """
    if splash:
        splash.hide()
    logger.exception("Fatal error, user will be logged out.")
    DesktopMessageBox.critical("Shotgun Desktop Error", error_message)
    # If we are logged in, we should log out so the user is not stuck in a loop of always
    # automatically logging in each time the app is launched again
    if shotgun_authenticator:
        shotgun_authenticator.clear_default_user()


def __handle_unexpected_exception(splash, shotgun_authenticator, error_message, app_bootstrap):
    """
    Tears down the application, logs you out and displays an error message.

    :param splash: Splash dialog to hide.
    :param shotgun_authenticator: Used to clear the default user so we logout
        automatically on Desktop failure.
    :param error_message: Error string that will be displayed in a message box.
    :params app_bootstrap: The application bootstrap.
    """
    if splash:
        splash.hide()

    exc_type, exc_value, exc_traceback = sys.exc_info()

    logger.exception("Fatal error, user will be logged out.")
    DesktopMessageBox.critical(
        "Shotgun Desktop Error",
        "Something went wrong in the Shotgun Desktop! If you drop us an email at "
        "support@shotgunsoftware.com, we'll help you diagnose the issue.\n"
        "For more information, see the log file at %s.\n"
        "Error: %s" % (app_bootstrap.get_logfile_location(), str(error_message)),
        detailed_text="".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    )
    # If we are logged in, we should log out so the user is not stuck in a loop of always
    # automatically logging in each time the app is launched again
    if shotgun_authenticator:
        shotgun_authenticator.clear_default_user()


def __get_certificate_prompt(keychain_name, action):
    """
    Generates the text to use when alerting the user that we need to register the certificate.

    :param keychain_name: Name of the keychain-like entity for a particular OS.
    :param action: Description of what the user will need to do when the OS prompts the user.

    :returns: String containing an error message formatted
    """
    return ("The Shotgun Desktop needs to update the security certificate list from your %s before "
            "it can turn on the browser integration.\n"
            "%s" % (keychain_name, action))


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
                "manager in order to proceed with the updates."
            )
        )
    elif sys.platform == "win32":
        DesktopMessageBox.information(
            "Shotgun browser integration",
            __get_certificate_prompt(
                "Windows certificate store",
                "Windows will now prompt you to accept one or more updates to your certificate store."
            )
        )
    # On Linux there's no need to prompt. It's all silent.


def __ensure_certificate_ready(app_bootstrap, tk_framework_desktopserver, certificate_folder):
    """
    Ensures that the certificates are created and registered. If something is amiss, then the
    configuration is fixed.

    :params app_bootstrap: The application bootstrap.
    :param tk_framework_desktopserver: The desktopserver framework.
    :param certificate_folder: Folder where the certificates are stored.

    :returns: True is the certificate is ready, False otherwise.
    """
    cert_handler = tk_framework_desktopserver.get_certificate_handler(certificate_folder)

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
        "%s\n"
        "Do you want to continue launching the Shotgun Desktop?" % msg,
        DesktopMessageBox.Yes,
        DesktopMessageBox.Yes | DesktopMessageBox.No,
        "If you drop us an email at support@shotgunsoftware.com, we'll help you diagnose "
        "the issue.\n\n"
        "For more information, see the log file at %s.\n\n"
        "%s" % (app_bootstrap.get_logfile_location(), traceback.format_exc())
    )
    warning_box.button(DesktopMessageBox.Yes).setText("Continue")
    warning_box.button(DesktopMessageBox.No).setText("Quit")

    return warning_box.exec_() == DesktopMessageBox.Yes


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
        app_bootstrap
    )


def __init_websockets(splash, app_bootstrap, settings):
    """
    Initializes the local websocket server.

    :pram splash: Splash widget.
    :param app_bootstrap: The application bootstrap instance.
    :param settings: The application's settings.

    :returns: The tk_framework_desktopserver.Server instance and a boolean indicating if the
        Desktop should keep launching.
    """
    if not __is_64bit_python():
        # Do not import if Python is not 64-bits
        logger.warning("Interpreter is not 64-bits, can't load desktop server")
        return None, True

    if not settings.integration_enabled:
        # Do not import if server is disabled.
        logger.info("Integration was disabled in config.ini.")
        return None, True

    # First try to import the framework. If it fails, let the user decide if the Desktop should
    # keep launching.
    try:
        splash.show()
        splash.set_message("Initializing browser integration")
        # Import framework
        import tk_framework_desktopserver
        app_bootstrap.add_logger_to_logfile(tk_framework_desktopserver.get_logger())
    except Exception, e:
        return None, __handle_unexpected_exception_during_websocket_init(splash, app_bootstrap, e)

    # Read the browser integration settings in the same file as the desktop integration settings.
    integration_settings = tk_framework_desktopserver.Settings(
        settings.location,
        os.path.join(
            app_bootstrap.get_shotgun_desktop_cache_location(),
            "config",
            "certificates"
        )
    )

    integration_settings.dump(logger)

    # We need to break these two try's because if we can't import the tk-framework-desktopserver
    # module we won't be able to catch any exception types from that module.
    try:
        # Makes sure that the certificate has been created on disk and registered with the OS (or browser on Linux).
        __ensure_certificate_ready(app_bootstrap, tk_framework_desktopserver, integration_settings.certificate_folder)

        # Launch the server
        server = tk_framework_desktopserver.Server(
            port=integration_settings.port,
            low_level_debug=integration_settings.low_level_debug,
            whitelist=integration_settings.whitelist,
            keys_path=integration_settings.certificate_folder
        )

        # This might throw a PortBusyError.
        server.start()

        splash.hide()
        return server, True
    except tk_framework_desktopserver.PortBusyError:
        # Gracefully let the user know that the Desktop might already be running.
        logger.exception("Could not start the browser integration:")
        splash.hide()
        return None, __query_quit_or_continue_launching(
            "Browser integration failed to start because port %d is already in use. The Shotgun "
            "Desktop may already be running on your machine." % integration_settings.port,
            app_bootstrap
        )
    except Exception, e:
        return None, __handle_unexpected_exception_during_websocket_init(splash, app_bootstrap, e)


class _BootstrapProxy(object):
    """
    Wraps the application bootstrap code to add functionality that should have been present
    on it.
    """

    def __init__(self, app_bootstrap):
        """
        Constructor

        :param app_bootstrap: Application bootstrap instance.
        """
        self._app_bootstrap = app_bootstrap

    def __getattr__(self, name):
        """
        Retrieves an attribute on the proxied instance.

        :param name: Name of the attribute.

        :returns: The attribute instance.
        """
        # Python hasn't found the requested attribute on this class, so let's look for it on the
        # proxied class.
        return getattr(self._app_bootstrap, name)

    def get_app_root(self):
        """
        Retrieves the application root.

        :returns: Path to the root of the installation directory.
        """
        # If the bootstrap now has the method, forward the call to it.
        if hasattr(self._app_bootstrap, "get_app_root"):
            return self._app_bootstrap.get_app_root()
        # Otherwise retrieve the bootstrap.py module from tk-desktop-internal (which can't be imported manually since it
        # isn't in the Python path.
        bootstrap_module = sys.modules[self._app_bootstrap.__module__]
        # Pick the SHOTGUN_APP_ROOT:
        # https://github.com/shotgunsoftware/tk-desktop-internal/blob/a31e9339b7e438cd111fb8f4a2b0436e77c98a17/Common/Shotgun/python/bootstrap.py#L80
        return bootstrap_module.SHOTGUN_APP_ROOT


def main(**kwargs):
    """
    Main

    :params app_bootstrap: AppBootstrap instance, used to get information from
        the installed application as well as updating the startup description
        location. See
        https://github.com/shotgunsoftware/tk-desktop-internal/blob/a31e9339b7e438cd111fb8f4a2b0436e77c98a17/Common/Shotgun/python/bootstrap.py#L133
        for more info.

    :returns: Error code for the process.
    """
    logger.debug("Running main from %s" % __file__)
    app_bootstrap = _BootstrapProxy(kwargs["app_bootstrap"])

    # Create some ui related objects
    app, splash = __init_app()

    show_login = __extract_command_line_argument("--show-login")

    # We might crash before even initializing the authenticator, so instantiate
    # it right away.
    shotgun_authenticator = None

    # Do not import sgtk globally to avoid using the wrong sgtk once we bootstrap in
    # the right config.
    import sgtk
    sgtk.LogManager().global_debug = True
    app_bootstrap.add_logger_to_logfile(
        sgtk.LogManager().root_logger
    )

    # We have gui, websocket library and the authentication module, now do the rest.
    server = None
    from sgtk import authentication
    try:
        # Reading user settings from disk.
        settings = Settings()
        settings.dump(logger)

        server, keep_running = __init_websockets(splash, app_bootstrap, settings)
        if keep_running is False:
            return 0

        if server:
            app_bootstrap.add_logger_to_logfile(server.get_logger())

        # It is very important to decouple logging in from creating the shotgun authenticator.
        # If there is an error during auto login, for example proxy settings changed and you
        # can't connect anymore, we need to be able to log the user out.
        shotgun_authenticator = sgtk.authentication.ShotgunAuthenticator()

        __optional_state_cleanup(splash, shotgun_authenticator, app_bootstrap)

        # If the server is up and running, we want the workflow where we can either not login
        # and keep the websocket running in the background or choose to login
        if server:
            user = __wait_for_login(
                splash,
                shotgun_authenticator,
                show_login
            )
        else:
            # The server is not running, so simply offer to login.
            user = __do_login(
                splash,
                shotgun_authenticator
            )

        if not user:
            logger.info("Login canceled. Quitting.")
            return 0

        # Now that we are logged, we can proceed with launching the
        # application.
        exit_code = __launch_app(
            app,
            splash,
            user,
            app_bootstrap,
            server,
            settings
        )
        return exit_code
    except RequestRestartException:
        subprocess.Popen(sys.argv, close_fds=True)
        return 0
    except authentication.AuthenticationCancelled:
        # The user cancelled an authentication request while the app was running, log him out.
        splash.hide()
        shotgun_authenticator.clear_default_user()
        return 0
    except ShotgunDesktopError, e:
        __handle_exception(splash, shotgun_authenticator, str(e))
        return -1
    except Exception, e:
        __handle_unexpected_exception(splash, shotgun_authenticator, e, app_bootstrap)
        return -1
    finally:
        # We can end up in the finally either because the app closed correctly, in which case
        # the aboutToQuit signal will have been send and the server shut down or there was an
        # exception and we need to tear down correctly.
        if server and server.is_running():
            server.tear_down()
