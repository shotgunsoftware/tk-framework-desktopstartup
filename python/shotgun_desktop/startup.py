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

# Add shotgun_api3 bundled with tk-core to the path.
shotgun_api3_path = os.path.normpath(os.path.join(os.path.split(__file__)[0], "..", "tk-core", "python", "tank_vendor"))
sys.path.insert(0, shotgun_api3_path)
logger.info("Using shotgun_api3 from '%s'" % shotgun_api3_path)
# Add the Shotgun Desktop Server source to the Python path
if "SGTK_DESKTOP_SERVER_LOCATION" in os.environ:
    desktop_server_root = os.environ["SGTK_DESKTOP_SERVER_LOCATION"]
else:
    desktop_server_root = os.path.normpath(os.path.join(os.path.split(__file__)[0], "..", "server"))
sys.path.insert(0, os.path.join(desktop_server_root, "python"))
logger.info("Using browser integration from '%s'" % desktop_server_root)


# now proceed with non builtin imports
from PySide import QtCore, QtGui

import shotgun_desktop.paths
import shotgun_desktop.version
from shotgun_desktop.turn_on_toolkit import TurnOnToolkit
from shotgun_desktop.desktop_message_box import DesktopMessageBox
from shotgun_desktop.initialization import initialize, does_pipeline_configuration_require_project
from shotgun_desktop import authenticator
from shotgun_desktop.upgrade_startup import upgrade_startup
from shotgun_desktop.location import get_location
from shotgun_desktop.settings import Settings
from shotgun_desktop.systray_icon import ShotgunSystemTrayIcon
from distutils.version import LooseVersion

import shutil

from shotgun_desktop.errors import (ShotgunDesktopError, RequestRestartException, UpgradeEngineError,
                                    ToolkitDisabledError, UpdatePermissionsError, UpgradeCoreError,
                                    InvalidPipelineConfiguration, UnexpectedConfigFound)


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


def __import_sgtk_from_path(path):
    """
    Imports Toolkit from the given path.

    :param path: Path to import Toolkit from.

    :returns: The Toolkit API handle.
    """
    # find where the install should be
    python_path = os.path.join(path, "install", "core", "python")
    logger.info("Prepending sgtk ('%s') to the pythonpath...", python_path)

    # update sys.path with the install
    if python_path not in sys.path:
        sys.path.insert(1, os.path.normpath(python_path))

    # clear the importer cache since the path could have been created
    # since the last attempt to import toolkit
    sys.path_importer_cache.clear()

    # finally try the import
    import sgtk
    logger.info("SGTK API successfully imported: %s" % sgtk)
    return sgtk


def is_toolkit_already_configured(site_configuration_path):
    """
    Checks if there is already a Toolkit configuration at this location.
    """

    # This logic is lifted from tk-core in setup_project_params.py - validate_configuration_location
    if not os.path.exists(site_configuration_path):
        return False

    for folder in ["config", "install"]:
        if os.path.exists(os.path.join(site_configuration_path, folder)):
            return True

    return False


def __initialize_sgtk_authentication(sgtk, app_bootstrap):
    """
    Sets the authenticated user if available. Also registers the authentication module's
    logger with the Desktop's.

    :param sgtk: The Toolkit API handle.
    :param app_bootstrap: The application bootstrap instance.
    """

    # If the version of Toolkit supports the new authentication mechanism
    if __toolkit_supports_authentication_module(sgtk):
        # import authentication
        from tank_vendor import shotgun_authentication
        # Add the module to the log file.
        app_bootstrap.add_logger_to_logfile(shotgun_authentication.get_logger())

        dm = sgtk.util.CoreDefaultsManager()
        sg_auth = shotgun_authentication.ShotgunAuthenticator(dm)

        # get the current user
        user = sg_auth.get_default_user()
        logger.info("Setting current user: %r" % user)
        sgtk.set_authenticated_user(user)


def __get_initialized_sgtk(path, app_bootstrap):
    """
    Imports Toolkit from the given path. If that version of Toolkit supports the
    shotgun_authentication module, the authenticated user will be set.

    :param sgtk: The Toolkit API handle.
    :param app_bootstrap: The application bootstrap instance.

    :returns: The imported sgtk module.
    """
    sgtk = __import_sgtk_from_path(path)
    __initialize_sgtk_authentication(sgtk, app_bootstrap)
    return sgtk


def __uuid_import(module, path):
    """
    Imports a module with a given name at a given location with a decorated
    namespace so that it can be reloaded multiple times at different locations.

    :param module: Name of the module we are importing.
    :param path: Path to the folder containing the module we are importing.

    :returns: The imported module.
    """
    import uuid
    import imp
    logger.info("Trying to import module '%s' from path '%s'..." % (module, path))
    spec = imp.find_module(module, [path])
    module = imp.load_module("%s_%s" % (uuid.uuid4().hex, module), *spec)
    logger.info("Successfully imported %s" % module)
    return module


def __import_shotgun_authentication_from_path(app_bootstrap):
    """
    Imports bundled Shotgun authentication module with a decorated name so
    another instance can be loaded later on. If SGTK_CORE_DEBUG_LOCATION
    is set, it will import the Shogun Authentication module bundled with that
    core instead.

    :params app_bootstrap: The application bootstrap.
    """
    logger.info("Initializing Shotgun Authenticator")

    if "SGTK_CORE_DEBUG_LOCATION" in os.environ:
        path = os.environ.get("SGTK_CORE_DEBUG_LOCATION")
        logger.info("Using overridden SGTK_CORE_DEBUG_LOCATION: '%s'" % path)
    else:
        path = os.path.abspath(os.path.join(os.path.split(__file__)[0], "..", "tk-core"))
        logger.info("Using built-in core located here: '%s'" % path)

    # find where the install should be
    # try to load from a non-configured core, that's the default behaviour.
    python_path = os.path.join(path, "python")
    if not os.path.exists(python_path):
        # Non configured core not found at that location. Maybe it's a configured one?
        python_path = os.path.join(path, "install", "core", "python")
    logger.info("Prepending sgtk ('%s') to the pythonpath...", python_path)

    # update sys.path with the install
    if python_path not in sys.path:
        sys.path.insert(1, os.path.normpath(python_path))

    # clear the importer cache since the path could have been created
    # since the last attempt to import toolkit
    sys.path_importer_cache.clear()

    # finally try the import
    sg_auth = __uuid_import("shotgun_authentication", os.path.join(python_path, "tank_vendor"))
    app_bootstrap.add_logger_to_logfile(sg_auth.get_logger())
    return sg_auth


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
        "Browser integration is running in the background. Click the Shotgun icon to login.",
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


def __do_login(splash, shotgun_authentication, shotgun_authenticator, app_bootstrap):
    """
    Asks for the credentials of the user or automatically logs the user in if the credentials are
    cached on disk.

    :param splash: Splash screen widget.
    :param shotgun_authentication: Shotgun authentication module.
    :param shotgun_authenticator: Instance of the Shotgun Authenticator to use for login.
    :params app_bootstrap: The application bootstrap.

    :returns: The tuple (ShotgunAuthenticator instance used to login, Shotgun connection to the
        server).
    """

    logger.debug("Retrieving credentials")
    try:
        user = shotgun_authenticator.get_user()
    except shotgun_authentication.AuthenticationCancelled:
        return None
    else:
        connection = user.create_sg_connection()
    return connection


def __do_login_or_tray(
    splash,
    shotgun_authentication, shotgun_authenticator,
    app_bootstrap, force_login
):
    """
    Runs the login dialog or the tray icon.

    :param splash: Splash screen widget.
    :param shotgun_authentication: Shotgun authentication module.
    :param shotgun_authenticator: Instance of the Shotgun Authenticator to use for login.
    :params app_bootstrap: The application bootstrap.
    :params force_login: If True, the prompt will be shown automatically instead of going
        into tray mode.

    :returns: The connection object if the user logged in, None if the user wants to quit the app.
    """
    connection = None

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
        connection = __do_login(splash, shotgun_authentication, shotgun_authenticator, app_bootstrap)
        # If we logged in, return the connection.
        if connection:
            return connection
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


def __launch_app(app, splash, connection, app_bootstrap, server):
    """
    Shows the splash screen, optionally downloads and configures Toolkit, imports it, optionally
    updates it and then launches the desktop engine.

    :param app: Application object for event processing.
    :param splash: Splash dialog to update user on what is currently going on
    :param connection: Connection to the Shotgun server.
    :param server: The tk_framework_desktopserver.Server instance.

    :returns: The error code to return to the shell.
    """
    # show the splash screen
    splash.show()
    splash.set_message("Looking up site configuration.")
    app.processEvents()

    _assert_toolkit_enabled(splash, connection)

    logger.debug("Getting the default site config")
    default_site_config, pc = shotgun_desktop.paths.get_default_site_config_root(connection)

    # try and import toolkit
    toolkit_imported = False
    config_folder_exists_at_startup = os.path.exists(default_site_config)

    reset_site = __extract_command_line_argument("--reset-site")

    # If the config folder exists at startup but the user wants to wipe it, do it.
    if config_folder_exists_at_startup and reset_site:
        logger.info("Resetting site configuration at '%s'" % default_site_config)
        splash.set_message("Resetting site configuration ...")
        shutil.rmtree(default_site_config)
        # It doesn't exist anymore, so we can act as if it never existed in the first place
        config_folder_exists_at_startup = False
        # Remove all occurances of --reset-site so that if we restart the app it doesn't reset it
        # again.

    # If there is no pipeline configuration but we found something on disk nonetheless.
    if not pc and is_toolkit_already_configured(default_site_config):
        raise UnexpectedConfigFound(default_site_config)

    try:
        # In we found a pipeline configuration and the path for the config exists, try to import
        # Toolkit.
        if config_folder_exists_at_startup:
            logger.info("Trying site config from '%s'" % default_site_config)
            sgtk = __import_sgtk_from_path(default_site_config)
            toolkit_imported = True
    except Exception:
        logger.exception("There was an error importing Toolkit:")
        pass
    else:
        # Toolkit was imported, we need to initialize it now.
        if toolkit_imported:
            __initialize_sgtk_authentication(sgtk, app_bootstrap)

    if not toolkit_imported:
        # sgtk not available. initialize core
        logger.info("Import sgtk from site config failed. ")
        try:
            app.processEvents()
            splash.set_message("Initializing Toolkit")
            logger.info("Initializing Toolkit")
            core_path = initialize(splash, connection)
        except Exception, error:
            logger.exception(error)
            if "ApiUser can not be accessed" in error.message:
                # Login does not have permission to see Scripts, throw an informative
                # error how to work around this for now.
                raise UpdatePermissionsError()
            else:
                raise

        try:
            # try again after the initialization is done
            logger.debug("Importing sgtk after initialization")

            sgtk = __get_initialized_sgtk(core_path, app_bootstrap)

            if sgtk is None:
                # Generate a generic error message, which will suggest to contact support.
                raise Exception("Could not access API post initialization.")

            splash.set_message("Setting up default site configuration...")

            # Install the default site config
            sg = sgtk.util.shotgun.create_sg_connection()

            # Site config has a none project id.
            project_id = None
            # If no pipeline configuration had been found.
            if not pc:
                # This site config has never been set by anyone, so we're the first.
                # If pipeline configurations are still project entities, we'll have to use the
                # TemplateProject as the project which will host the pipeline configuration.
                if does_pipeline_configuration_require_project(connection):
                    template_project = sg.find_one(
                        "Project",
                        [["name", "is", "Template Project"], ["layout_project", "is", None]])
                    # Can't find template project, so we're effectively done here, we need a project
                    # to create a pipeline configuration.
                    if template_project is None:
                        # Generate a generic error message, which will suggest to contact support.
                        raise Exception("Error finding the Template project on your site.")

                    logger.info("Creating the site config using the template project.")

                    # We'll need to use the template project's id to setup the site config in this case.
                    project_id = template_project["id"]
                else:
                    logger.info("Creating the site config without using a project.")
            else:
                # If a project is set in the pipeline configuration, it's an old style site config tied
                # to the template project, so we have to use it.
                if pc.get("project") is not None:
                    logger.info("Reusing the site config with a project.")
                    project_id = pc["project"]["id"]
                else:
                    logger.info("Reusing the site config without a project.")

            # Create the directory
            if not os.path.exists(default_site_config):
                os.makedirs(default_site_config)

            # Setup the command to create the config
            if sys.platform == "darwin":
                path_param = "config_path_mac"
            elif sys.platform == "win32":
                path_param = "config_path_win"
            elif sys.platform.startswith("linux"):
                path_param = "config_path_linux"

            # allow the config uri to be overridden for testing
            config_uri = os.environ.get("SGTK_SITE_CONFIG_DEBUG_LOCATION", "tk-config-site")

            params = {
                "auto_path": True,
                "config_uri": config_uri,
                "project_folder_name": "site",
                "project_id": project_id,
                path_param: default_site_config,
            }
            setup_project = sgtk.get_command("setup_project")
            setup_project.set_logger(logger)

            try:
                setup_project.execute(params)
            except Exception, error:
                logger.exception(error)
                if "CRUD ERROR" in error.message:
                    raise UpdatePermissionsError()
                else:
                    raise

            # and now try to load up sgtk through the config again
            sgtk = __get_initialized_sgtk(default_site_config, app_bootstrap)
            tk = sgtk.sgtk_from_path(default_site_config)

            # now localize the core to the config
            splash.set_message("Localizing core...")
            localize = tk.get_command("localize")
            localize.set_logger(logger)
            localize.execute({})

            # Get back the pipeline configuration, this is expected to be initialized further down.
            _, pc = shotgun_desktop.paths.get_default_site_config_root(connection)
        except Exception:
            # Something went wrong. Wipe the default site config if we can and
            # rethrow
            if not config_folder_exists_at_startup:
                logger.error(
                    "Something went wrong during Toolkit's activation, wiping configuration."
                )
                if os.path.exists(default_site_config):
                    shutil.rmtree(default_site_config)
            raise
    else:
        tk = sgtk.sgtk_from_path(default_site_config)

    # If the pipeline configuration found in Shotgun doesn't match what we have locally, we have a
    # problem.
    if pc["id"] != tk.pipeline_configuration.get_shotgun_id():
        raise InvalidPipelineConfiguration(pc, tk.pipeline_configuration)

    is_auto_path = tk.pipeline_configuration.is_auto_path()

    # Downloads an upgrade for the startup if available. The startup upgrade is independent from the
    # auto_path state and has its own logic for auto-updating or not, so move this outside the
    # if auto_path test.
    startup_updated = upgrade_startup(
        splash,
        sgtk,
        app_bootstrap
    )

    core_updated = False
    if is_auto_path:
        splash.set_message("Getting core and engine updates...")
        logger.info("Getting updates...")
        app.processEvents()

        core_update = tk.get_command("core")
        core_update.set_logger(logger)
        result = core_update.execute({})

        # If core was updated.
        if result["status"] == "updated":
            core_updated = True
        else:
            if result["status"] == "update_blocked":
                # Core update should not be blocked. Warn, because it is not a fatal error.
                logger.warning("Core update was blocked. Reason: %s" % result["reason"])
            elif result["status"] != "up_to_date":
                # Core update should not fail. Warn, because it is not a fatal error.
                logger.warning("Unexpected Core upgrade result: %s" % str(result))
    else:
        logger.info("Pipeline configuration not in auto path mode, skipping core and engine "
                    "updates...")

    # Detect which kind of updates happened and restart the app if necessary
    if core_updated and startup_updated:
        return __restart_app_with_countdown(splash, "Shotgun Desktop and core updated.")
    elif core_updated:
        return __restart_app_with_countdown(splash, "Core updated.")
    elif startup_updated:
        return __restart_app_with_countdown(splash, "Shotgun Desktop updated.")

    # This is important that this happens AFTER the core upgrade so that if there is a bug in the
    # migration code we can release a new core that fixes it.
    # If the pipeline configuration we got from Shotgun is not assigned to a project, we might have
    # some patching to be done to local site configuration.
    if pc["project"] is None:

        # make sure that the version of core we are using supports the new-style site configuration
        if not __supports_pipeline_configuration_upgrade(tk.pipeline_configuration):
            raise UpgradeCoreError(
                "Running a site configuration without the Template Project requires core v0.16.8 "
                "or higher.",
                default_site_config
            )

        # If the configuration on disk is not the site configuration, update it to the site config.
        if not tk.pipeline_configuration.is_site_configuration():
            tk.pipeline_configuration.convert_to_site_config()

    if is_auto_path:
        updates = tk.get_command("updates")
        updates.set_logger(logger)
        updates.execute({})

    if not __toolkit_supports_authentication_module(sgtk):
        raise UpgradeCoreError(
            "This version of the Shotgun Desktop only supports core 0.16.4 and higher.",
            default_site_config
        )
    # initialize the tk-desktop engine for an empty context
    splash.set_message("Starting desktop engine.")
    app.processEvents()

    ctx = tk.context_empty()
    engine = sgtk.platform.start_engine("tk-desktop", tk, ctx)

    if not __desktop_engine_supports_authentication_module(engine):
        raise UpgradeEngineError(
            "This version of the Shotgun Desktop only supports tk-desktop engine 2.0.0 and higher.",
            default_site_config
        )

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
    logger.exception("Fatal error, user will be logged out.")
    DesktopMessageBox.critical(
        "Shotgun Desktop Error",
        "Something went wrong in the Shotgun Desktop! If you drop us an email at "
        "support@shotgunsoftware.com, we'll help you diagnose the issue.\n"
        "For more information, see the log file at %s.\n"
        "Error: %s" % (app_bootstrap.get_logfile_location(), str(error_message)),
        detailed_text="".join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
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
    return ("The Shotgun Desktop needs to install a security certificate into your %s before "
            "it can turn on the browser integration.\n"
            "%s." % (keychain_name, action))


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
                "manager in order to proceed with the update."
            )
        )
    elif sys.platform == "win32":
        DesktopMessageBox.information(
            "Shotgun browser integration",
            __get_certificate_prompt(
                "Windows certificate store",
                "Windows will now prompt you to accept an update to your certificate store."
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

    # We need to break these two try's because if we can't import the tk-framework-desktopserver
    # module we won't be able to catch any exception types from that module.
    try:
        key_path = os.path.join(
            app_bootstrap.get_shotgun_desktop_cache_location(),
            "config",
            "certificates"
        )

        # Makes sure that the certificate has been created on disk and registered with the OS (or browser on Linux).
        __ensure_certificate_ready(app_bootstrap, tk_framework_desktopserver, key_path)

        # Launch the server
        server = tk_framework_desktopserver.Server(
            port=settings.integration_port,
            debug=settings.integration_debug,
            whitelist=settings.integration_whitelist,
            keys_path=key_path
        )

        # This might throw a PortBusy error.
        server.start()

        splash.hide()
        return server, True
    except tk_framework_desktopserver.PortBusy:
        # Gracefully let the user know that the Desktop might already be running.
        logger.exception("Could not start the browser integration:")
        splash.hide()
        return None, __query_quit_or_continue_launching(
            "Browser integration failed to start because port %d is already in use. The Shotgun "
            "Desktop may already be running on your machine." % settings.integration_port,
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
        location. See https://github.com/shotgunsoftware/tk-desktop-internal/blob/a31e9339b7e438cd111fb8f4a2b0436e77c98a17/Common/Shotgun/python/bootstrap.py#L133
        for more info.

    :returns: Error code for the process.
    """
    logger.debug("Running main from %s" % __file__)
    app_bootstrap = _BootstrapProxy(kwargs["app_bootstrap"])

    settings = Settings(app_bootstrap)

    # Create some ui related objects
    app, splash = __init_app()

    show_login = __extract_command_line_argument("--show-login")

    # We might crash before even initializing the authenticator, so instantiate
    # it right away.
    shotgun_authenticator = None

    # We have to import this in a separate try catch block because we'll be using
    # shotgun_authentication in the following catch statements.
    try:
        # get the shotgun authentication module.
        shotgun_authentication = __import_shotgun_authentication_from_path(app_bootstrap)
    except Exception, e:
        __handle_unexpected_exception(splash, shotgun_authenticator, e, app_bootstrap)
        return -1

    # We have gui, websocket library and the authentication module, now do the rest.
    server = None
    try:
        server, keep_running = __init_websockets(splash, app_bootstrap, settings)
        if keep_running is False:
            return 0

        if server:
            app_bootstrap.add_logger_to_logfile(server.get_logger())

        # It is very important to decouple logging in from creating the shotgun authenticator.
        # If there is an error during auto login, for example proxy settings changed and you
        # can't connect anymore, we need to be able to log the user out.
        shotgun_authenticator = authenticator.get_configured_shotgun_authenticator(
            shotgun_authentication, settings
        )

        __optional_state_cleanup(splash, shotgun_authenticator, app_bootstrap)

        # If the server is up and running, we want the workflow where we can either not login
        # and keep the websocket running in the background or choose to login
        if server:
            connection = __do_login_or_tray(
                splash,
                shotgun_authentication,
                shotgun_authenticator,
                app_bootstrap,
                show_login
            )
        else:
            # The server is not running, so simply offer to login.
            connection = __do_login(
                splash,
                shotgun_authentication,
                shotgun_authenticator,
                app_bootstrap
            )

        # If we didn't authenticate a user
        if not connection:
            # We're done for the day.
            logger.info("Login canceled. Quitting.")
            return 0
        else:
            # Now that we are logged, we can proceed with launching the
            # application.
            return __launch_app(
                app,
                splash,
                connection,
                app_bootstrap,
                server
            )
    except RequestRestartException:
        subprocess.Popen(sys.argv, close_fds=True)
        return 0
    except shotgun_authentication.AuthenticationCancelled:
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
