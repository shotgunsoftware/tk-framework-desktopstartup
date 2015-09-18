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
logger.info("Using desktop integration from '%s'" % desktop_server_root)


# now proceed with non builtin imports
from PySide import QtCore, QtGui

import shotgun_desktop.paths
import shotgun_desktop.version
from shotgun_desktop.turn_on_toolkit import TurnOnToolkit
from shotgun_desktop.initialization import initialize, does_pipeline_configuration_require_project
from shotgun_desktop import authenticator
from shotgun_desktop.upgrade_startup import upgrade_startup
from shotgun_desktop.location import get_location
from shotgun_desktop.settings import Settings
from shotgun_desktop.systray_icon import ShotgunSystemTrayIcon
from distutils.version import LooseVersion

from shotgun_desktop.ui import resources_rc
import shutil

from shotgun_desktop.errors import (ShotgunDesktopError, RequestRestartException, UpgradeEngineError,
                                    ToolkitDisabledError, UpdatePermissionsError, UpgradeCoreError,
                                    InvalidPipelineConfiguration, UnexpectedConfigFound)

RESET_SITE_ARG = "--reset-site"


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
    # Executes until user clicks on the systray and chooses Login or Quit.
    return SystrayEventLoop(systray).exec_()


def __do_login(splash, shotgun_authentication, shotgun_authenticator, app_bootstrap):
    """
    Asks for the credentials of the user or automatically logs the user in if the credentials are
    cached on disk.

    :returns: The tuple (ShotgunAuthenticator instance used to login, Shotgun connection to the
        server).
    """

    # If the application was launched holding the alt key, log the user out.
    if (QtGui.QApplication.queryKeyboardModifiers() & QtCore.Qt.AltModifier) == QtCore.Qt.AltModifier:
        logger.info("Alt was pressed, clearing default user and startup descriptor")
        shotgun_authenticator.clear_default_user()
        app_bootstrap.clear_startup_location()
        __restart_app_with_countdown(splash, "Desktop has been reinitialized.")

    logger.debug("Retrieving credentials")
    try:
        user = shotgun_authenticator.get_user()
    except shotgun_authentication.AuthenticationCancelled:
        return None
    else:
        connection = user.create_sg_connection()
    return connection


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

    # If the config folder exists at startup but the user wants to wipe it, do it.
    if config_folder_exists_at_startup and RESET_SITE_ARG in sys.argv:
        logger.info("Resetting site configuration at '%s'" % default_site_config)
        splash.set_message("Resetting site configuration ...")
        shutil.rmtree(default_site_config)
        # It doesn't exist anymore, so we can act as if it never existed in the first place
        config_folder_exists_at_startup = False
        # Remove all occurances of --reset-site so that if we restart the app it doesn't reset it
        # again.
        while RESET_SITE_ARG in sys.argv:
            sys.argv.remove(RESET_SITE_ARG)

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
    QtGui.QMessageBox.critical(None, "Toolkit Error", error_message)
    # If we are logged in, we should log out so the user is not stuck in a loop of always
    # automatically logging in each time the app is launched again
    if shotgun_authenticator:
        shotgun_authenticator.clear_default_user()


def __handle_unexpected_exception(splash, shotgun_authenticator):
    """
    Tears down the application and logs you out.

    :param splash: Splash dialog to hide.
    :param shotgun_authenticator: Used to clear the default user so we logout
        automatically on Desktop failure.

    :raises Exception: Any exception being handled is raised as is so its callstack
        is left as is.
    """
    if splash:
        splash.hide()
    # If we are logged in, we should log out so the user is not stuck in a loop of always
    # automatically logging in each time the app is launched again
    if shotgun_authenticator:
        shotgun_authenticator.clear_default_user()
    # Let the bootstrap catch this error and handle it.
    raise


def __warn_for_prompt():
    """
    Warn the user he will be prompted.
    """
    if sys.platform == "darwin":
        QtGui.QMessageBox.information(
            None,
            "Shotgun Desktop Integration",
            "The Shotgun Desktop Integration needs to update your keychain.\n\n"
            "You will be prompted to enter your keychain credentials by Keychain Access in order "
            "to update they keychain.",
            QtGui.QMessageBox.Ok
        ) == QtGui.QMessageBox.Ok
    elif sys.platform == "win32":
        QtGui.QMessageBox.information(
            None,
            "Shotgun Desktop Integration",
            "The Shotgun Desktop Integration needs to update your Windows certificate list.\n\n"
            "Windows will now prompt you to update the certificate list.",
            QtGui.QMessageBox.Ok
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

    try:
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
    except:
        logger.error("There was a problem registering the certificates. Skipping this step.")
        return False


def __init_websockets(tk_framework_desktopserver, splash, app_bootstrap, settings):
    """
    Initializes the local websocket server.

    :param tk_framework_desktopserver: tk_framework_desktopserver module handle.
    :pram splash: Splash widget.
    :param app_bootstrap: The application bootstrap instance.
    :param settings: The application's settings.

    :returns: The tk_framework_desktopserver.Server instance.
    """
    key_path = os.path.join(
        app_bootstrap.get_shotgun_desktop_cache_location(),
        "config",
        "certificates"
    )

    if not __ensure_certificate_ready(app_bootstrap, tk_framework_desktopserver, key_path):
        return None

    server = tk_framework_desktopserver.Server(
        port=settings.integration_port,
        debug=settings.integration_debug,
        whitelist=settings.integration_whitelist,
        keys_path=key_path
    )
    server.start()

    return server


def __import_tk_framework_desktopserver(app_bootstrap, splash, settings):
    """
    Imports the tk-framework-desktopserver module.

    :param app_bootstrap: Application bootstrap.
    :param splash: Splash widget.
    :param settings: Desktop application settings

    :returns: Handle to the tk-framework-desktopserver module.
    """
    # Do not import if Python is not 64-bits
    if not __is_64bit_python():
        logger.warning("Interpreter is not 64-bits, can't load desktop server")
        return None

    # Do not import if server is disabled.
    if not settings.integration_enabled:
        logger.info("Integration was disabled in config.ini.")
        return None

    # Show progress
    splash.show()
    splash.set_message("Initializing Desktop Integration server")

    # try to import
    tk_framework_desktopserver = None
    try:
        import tk_framework_desktopserver
        app_bootstrap.add_logger_to_logfile(tk_framework_desktopserver.get_logger())
    except:
        __handle_unexpected_exception(splash, None)
    return tk_framework_desktopserver


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

    # We might crash before even initializing the authenticator, so instantiate
    # it right away.
    shotgun_authenticator = None

    # We have to import this in a separate try catch block because we'll be using
    # shotgun_authentication in the following catch statements.
    try:
        # get the shotgun authentication module.
        shotgun_authentication = __import_shotgun_authentication_from_path(app_bootstrap)
    except:
        __handle_unexpected_exception(splash, shotgun_authenticator)
        return -1

    # We have gui, websocket library and the authentication module, now do the rest.
    server = None
    try:
        # For now let the Desktop keep running even if the server cannot start
        try:
            tk_framework_desktopserver = __import_tk_framework_desktopserver(app_bootstrap, splash, settings)
            if tk_framework_desktopserver:
                server = __init_websockets(tk_framework_desktopserver, splash, app_bootstrap, settings)
                app_bootstrap.add_logger_to_logfile(server.get_logger())
        except Exception, e:
            msg = "Could not start the desktop server: %s" % str(e)
            logger.error(msg)
            splash.set_message(msg)
            splash.show()
            app.processEvents()
            time.sleep(3)

        splash.hide()

        # It is very important to decouple logging in from creating the shotgun authenticator.
        # If there is an error during auto login, for example proxy settings changed and you
        # can't connect anymore, we need to be able to log the user out.
        shotgun_authenticator = authenticator.get_configured_shotgun_authenticator(
            shotgun_authentication, settings
        )
        # If the user has never logged in, start the Desktop in minimalist mode.
        if not shotgun_authenticator.get_default_host():
            if __run_with_systray() == SystrayEventLoop.CLOSE_APP:
                return 0

        # Authenticate
        connection = __do_login(splash, shotgun_authentication, shotgun_authenticator, app_bootstrap)
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
    except ShotgunDesktopError, ex:
        # Those are expected errors and the error message will be printed as is.
        __handle_exception(splash, shotgun_authenticator, str(ex))
        return -1
    except:
        __handle_unexpected_exception(splash, shotgun_authenticator)
        return -1
    finally:
        # We can end up in the finally either because the app closed correctly, in which case
        # the aboutToQuit signal will have been send and the server shut down or there was an
        # exception and we need to tear down correctly.
        if server and server.is_running():
            server.tear_down()
