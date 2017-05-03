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

# Add Toolkit to the path.
add_to_python_path(os.path.join("..", "tk-core", ), "SGTK_CORE_LOCATION", "tk-core")

# now proceed with non builtin imports
from PySide import QtCore, QtGui

import shotgun_desktop.paths
from shotgun_desktop.turn_on_toolkit import TurnOnToolkit
from shotgun_desktop.desktop_message_box import DesktopMessageBox
from shotgun_desktop.upgrade_startup import upgrade_startup
from shotgun_desktop.location import get_startup_descriptor
from shotgun_desktop.settings import Settings
from shotgun_desktop.systray_icon import ShotgunSystemTrayIcon
from distutils.version import LooseVersion

from shotgun_desktop.errors import (ShotgunDesktopError, RequestRestartException, UpgradeEngineError,
                                    ToolkitDisabledError, UpgradeCoreError,
                                    InvalidPipelineConfiguration)


global_debug_flag_at_startup = None


def __restore_global_debug_flag():
    """
    Restores the global debug flag
    """
    global global_debug_flag_at_startup
    import sgtk
    sgtk.LogManager().global_debug = global_debug_flag_at_startup


def __backup_global_debug_flag():
    """
    Backups the global debug flag.
    """
    global global_debug_flag_at_startup
    import sgtk
    global_debug_flag_at_startup = sgtk.LogManager().global_debug


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
    # Before starting QApplication, disable system default QT plugins.
    # The installed QT version on the system might be different then the one we ship with.
    # Incompatible plugins prevent the application from starting.
    # This problem was reproducible on Centos 7 with KDE.
    # We need to remove this env var to make sure every other process starting a
    # QApplication in this same environment will not have problems.
    if os.environ.get("QT_PLUGIN_PATH"):
        del os.environ["QT_PLUGIN_PATH"]
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


def __launch_app(app, splash, user, app_bootstrap, settings):
    """
    Shows the splash screen, optionally downloads and configures Toolkit, imports it, optionally
    updates it and then launches the desktop engine.

    :param app: Application object for event processing.
    :param splash: Splash dialog to update user on what is currently going on
    :param user: Current ShotgunUser.
    :param app_bootstrap: Application bootstrap.
    :param settings: The application's settings.

    :returns: The error code to return to the shell.
    """
    # show the splash screen
    splash.show()

    import sgtk
    sgtk.set_authenticated_user(user)

    # Downloads an upgrade for the startup if available.
    startup_updated = upgrade_startup(
        splash,
        sgtk,
        app_bootstrap
    )
    if startup_updated:
        __restart_app_with_countdown(splash, "Shotgun Desktop updated.")

    splash.set_message("Looking up site configuration.")

    connection = user.create_sg_connection()

    _assert_toolkit_enabled(splash, connection)

    logger.debug("Getting the default site configuration.")
    pc_path, pc, toolkit_classic_required = shotgun_desktop.paths.get_pipeline_configuration_info(connection)

    # We're about to bootstrap, so remove sgtk from our scope so that if we add
    # code that uses it after the bootstrap we have to import the
    # new core.
    del sgtk
    if toolkit_classic_required:
        engine = __start_engine_in_toolkit_classic(app, splash, user, pc, pc_path)
    else:
        engine = __start_engine_in_zero_config(app, app_bootstrap, splash, user)

    return __post_bootstrap_engine(splash, app_bootstrap, engine)


def __bootstrap_progress_callback(splash, app, progress_value, message):
    """
    Called whenever toolkit reports progress.

    :param progress_value: The current progress value as float number.
                           values will be reported in incremental order
                           and always in the range 0.0 to 1.0
    :param message:        Progress message string
    """
    splash.set_message(message)
    logger.debug(message)


def __start_engine_in_toolkit_classic(app, splash, user, pc, pc_path):
    """
    Create a Toolkit instance by boostraping into the pipeline configuration.

    :param app: Application object for event processing.
    :param splash: Splash dialog to update user on what is currently going on
    :param user: Current ShotgunUser.
    :param pc: Pipeline configuration entity dictionary.
    :param pc_path: Path to the pipeline configuration.

    :returns: Toolkit engine that was started.
    """
    import sgtk
    mgr = sgtk.bootstrap.ToolkitManager(user)
    # Tell the manager to resolve the config in Shotgun so it can resolve the location on disk.
    mgr.do_shotgun_config_lookup = True
    mgr.progress_callback = lambda progress_value, message: __bootstrap_progress_callback(
        splash, app, progress_value, message
    )
    mgr.pipeline_configuration = pc["id"]

    def pre_engine_start_callback(ctx):
        """
        Called before the engine starts during bootstrap. This is used to
        ensure that the pipeline configuration on disk is the expected one
        and has the right stat.

        :param ctx: Toolkit context we are bootstrapping into.
        :type ctx: :class:`sgtk.Context`
        """
        # If the pipeline configuration found in Shotgun doesn't match what we have locally, we have a
        # problem.
        if pc["id"] != ctx.sgtk.pipeline_configuration.get_shotgun_id():
            raise InvalidPipelineConfiguration(pc, ctx.sgtk.pipeline_configuration)

        # If the pipeline configuration we got from Shotgun is not assigned to a project, we might have
        # some patching to be done to local site configuration.
        if pc["project"] is None:

            # make sure that the version of core we are using supports the new-style site configuration
            if not __supports_pipeline_configuration_upgrade(ctx.sgtk.pipeline_configuration):
                raise UpgradeCoreError(
                    "Running a site configuration without the Template Project requires core v0.16.8 "
                    "or higher.",
                    pc_path
                )

            # If the configuration on disk is not the site configuration, update it to the site config.
            if not ctx.sgtk.pipeline_configuration.is_site_configuration():
                ctx.sgtk.pipeline_configuration.convert_to_site_config()

        splash.set_message("Launching Engine...")

        __restore_global_debug_flag()

    # We need to validate a few things before the engine starts.
    mgr.pre_engine_start_callback = pre_engine_start_callback

    engine = mgr.bootstrap_engine("tk-desktop")

    if not __desktop_engine_supports_authentication_module(engine):
        raise UpgradeEngineError(
            "This version of the Shotgun Desktop only supports tk-desktop engine 2.0.0 and higher.",
            pc_path
        )

    return engine


def __start_engine_in_zero_config(app, app_bootstrap, splash, user):
    """
    Launch into the engine using the new zero config based bootstrap.

    :param app: Application object for event processing.
    :param app_bootstrap: Application bootstrap.
    :param splash: Splash dialog to update user on what is currently going on
    :param user: Current ShotgunUser.

    :returns: Toolkit engine that was started.
    """
    # The startup is up to date, now it's time to bootstrap Toolkit.
    import sgtk
    mgr = sgtk.bootstrap.ToolkitManager(user)

    # Allows to take over the site config to use with Desktop without impacting the projects
    # configurations.
    mgr.base_configuration = os.environ.get(
        "SHOTGUN_DESKTOP_CONFIG_FALLBACK_DESCRIPTOR",
        "sgtk:descriptor:app_store?name=tk-config-basic"
    )
    mgr.progress_callback = lambda progress_value, message: __bootstrap_progress_callback(
        splash, app, progress_value, message
    )
    mgr.plugin_id = "basic.desktop"

    # Add the bundle cache if there is one available
    bundle_cache_path = app_bootstrap.get_bundle_cache_location()
    if bundle_cache_path:
        mgr.bundle_cache_fallback_paths.append(bundle_cache_path)

    mgr.pre_engine_start_callback = lambda ctx: __restore_global_debug_flag()

    return mgr.bootstrap_engine("tk-desktop")


def __post_bootstrap_engine(splash, app_bootstrap, engine):
    """
    Called after bootstrapping the engine. Mainly use to transition logging to the
    engine and launch the main event loop.

    :param splash: Splash screen widget.
    :param app_bootstrap: Application bootstrap logic.
    :param engine: Toolkit engine that was bootstrapped.

    :returns: Application exit code.
    """
    import sgtk

    # reset PYTHONPATH and PYTHONHOME if they were overridden by the application
    if "SGTK_DESKTOP_ORIGINAL_PYTHONPATH" in os.environ:
        os.environ["PYTHONPATH"] = os.environ["SGTK_DESKTOP_ORIGINAL_PYTHONPATH"]
    if "SGTK_DESKTOP_ORIGINAL_PYTHONHOME" in os.environ:
        os.environ["PYTHONHOME"] = os.environ["SGTK_DESKTOP_ORIGINAL_PYTHONHOME"]

    # and run the engine
    logger.debug("Running tk-desktop")
    startup_desc = get_startup_descriptor(sgtk, engine.shotgun, app_bootstrap)

    startup_version = startup_desc.version

    return engine.run(
        splash,
        version=app_bootstrap.get_version(),
        startup_version=startup_version,
        startup_descriptor=startup_desc
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
        "Error: %s\n"
        "For more information, see the log file at %s." % (
            str(error_message), app_bootstrap.get_logfile_location()
        ),
        detailed_text="".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    )
    # If we are logged in, we should log out so the user is not stuck in a loop of always
    # automatically logging in each time the app is launched again
    if shotgun_authenticator:
        shotgun_authenticator.clear_default_user()


class _BootstrapProxy(object):
    """
    Wraps the application bootstrap code to add functionality that is present only in more recent builds of the
    Desktop, which the startup code is not necessarily running off of.
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

    def get_bundle_cache_location(self):
        """
        Retrieves the bundle cache that is distributed with the Shotgun Desktop.

        We're implementing this method on the proxy because Desktop versions 1.3.6 and earlier didn't
        have a bundle cache.

        :returns: Path to the bundle cache or None if no bundle cache is present.
        """
        if hasattr(self._app_bootstrap, "get_bundle_cache_location"):
            return self._app_bootstrap.get_bundle_cache_location()
        else:
            return os.environ.get("SHOTGUN_DESKTOP_BUNDLE_CACHE_LOCATION") or None


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

    app_bootstrap = _BootstrapProxy(kwargs["app_bootstrap"])

    # Do not import sgtk globally to avoid using the wrong sgtk once we bootstrap in
    # the right config.
    import sgtk

    global logger

    # Older versions of the desktop on Windows logged at %APPDATA%\Shotgun\tk-desktop.log. Notify the user that
    # this logging location is deprecated and the logs are now at %APPDATA%\Shotgun\Logs\tk-desktop.log
    if sys.platform == "win32" and LooseVersion(app_bootstrap.get_version()) <= "v1.3.6":
        logger.info(
            "Logging at this location will now stop and resume at {0}\\tk-desktop.log".format(
                sgtk.LogManager().log_folder
            )
        )
        logger.info(
            "If you see any more logs past this line, you need to upgrade your site configuration to "
            "the latest core and apps using 'tank core' and 'tank updates'."
        )

    # Core will take over logging
    app_bootstrap.tear_down_logging()

    sgtk.LogManager().initialize_base_file_handler("tk-desktop")

    logger = sgtk.LogManager.get_logger(__name__)
    logger.debug("Running main from %s" % __file__)

    # Create some ui related objects
    app, splash = __init_app()

    # We might crash before even initializing the authenticator, so instantiate
    # it right away.
    shotgun_authenticator = None
    # Shotgun Desktop startup has always been logging every debug string to disk since the new authentication from 0.16
    # was released and the startup has been difficult to work with and debug, so keep that logic in place during the
    # startup sequence. It will be restored during the ToolkitManager's pre_engine_start_callback.
    __backup_global_debug_flag()
    sgtk.LogManager().global_debug = True

    from sgtk import authentication
    from sgtk.descriptor import InvalidAppStoreCredentialsError

    try:
        # Reading user settings from disk.
        settings = Settings()
        settings.dump(logger)

        # It is very important to decouple logging in from creating the shotgun authenticator.
        # If there is an error during auto login, for example proxy settings changed and you
        # can't connect anymore, we need to be able to log the user out.
        shotgun_authenticator = sgtk.authentication.ShotgunAuthenticator()

        __optional_state_cleanup(splash, shotgun_authenticator, app_bootstrap)

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
    except InvalidAppStoreCredentialsError, e:
        __handle_exception(splash, shotgun_authenticator, str(e))
        return -1
    except ShotgunDesktopError, e:
        __handle_exception(splash, shotgun_authenticator, str(e))
        return -1
    except Exception, e:
        __handle_unexpected_exception(splash, shotgun_authenticator, e, app_bootstrap)
        return -1
