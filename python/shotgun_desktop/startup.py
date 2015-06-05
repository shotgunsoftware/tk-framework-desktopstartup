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

# Add shotgun_api3 bundled with tk-core to the path.
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], "..", "tk-core", "python", "tank_vendor"))

# initialize logging
import logging
import shotgun_desktop.splash

logger = logging.getLogger("tk-desktop.startup")
logger.info("------------------ Desktop Engine Startup ------------------")

# now proceed with non builtin imports
from PySide import QtCore, QtGui

import shotgun_desktop.paths
import shotgun_desktop.version
from shotgun_desktop.turn_on_toolkit import TurnOnToolkit
from shotgun_desktop.initialization import initialize, does_pipeline_configuration_require_project
from shotgun_desktop import authenticator
from shotgun_desktop.upgrade_startup import upgrade_startup
from shotgun_desktop.location import get_location

from shotgun_desktop.ui import resources_rc
import shutil

from shotgun_desktop.errors import (ShotgunDesktopError, RequestRestartException,
                                    ToolkitDisabledError, UpdatePermissionsError, UpgradeCoreError,
                                    SitePipelineConfigurationNotFound)


def __supports_authentication_module(sgtk):
    """
    Tests if the given Toolkit API supports the shotgun_authentication module.

    :param sgtk: The Toolkit API handle.

    :returns: True if the shotgun_authentication module is supported, False otherwise.
    """
    # if the authentication module is not supported, this method won't be present on the core.
    return hasattr(sgtk, "set_authenticated_user")


def __import_sgtk_from_path(path, app_bootstrap):
    """
    Imports Toolkit from the given path. If that version of Toolkit supports the shotgun_authentication
    module, the current user will be set. The Toolkit will not support the shotgun_authentication
    module if we've just upgraded the Desktop installer and are running a core upgrade for the first
    time. The first import of the old core will be a pre-0.16 version of the core, therefore it
    won't support the shotgun_authentication module.

    :param path: Path to import Toolkit from.

    :returns: The Toolkit API handle.
    """
    # find where the install should be
    python_path = os.path.join(path, "install", "core", "python")
    logger.info("Prepending sgtk ('%s') to the pythonpath...", python_path)

    # update sys.path with the install
    if python_path not in sys.path:
        sys.path.insert(1, python_path)

    # clear the importer cache since the path could have been created
    # since the last attempt to import toolkit
    sys.path_importer_cache.clear()

    # finally try the import
    import sgtk
    logger.info("SGTK API successfully imported: %s" % sgtk)

    # If the version of Toolkit supports the new authentication mechanism
    if __supports_authentication_module(sgtk):
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
        sys.path.insert(1, python_path)

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


def __do_login(splash, shotgun_authentication, app_bootstrap):
    """
    Asks for the credentials of the user or automatically logs the user in if the credentials are
    cached on disk.

    :returns: The tuple (ShotgunAuthenticator instance used to login, Shotgun connection to the
        server).
    """
    shotgun_authenticator = authenticator.get_configured_shotgun_authenticator(
        shotgun_authentication
    )
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
        return None, None
    else:
        connection = user.create_sg_connection()
    return shotgun_authenticator, connection


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


def __launch_app(app, splash, connection, app_bootstrap):
    """
    Shows the splash screen, optionally downloads and configures Toolkit, imports it, optionally
    updates it and then launches the desktop engine.

    :param app: Application object for event processing.
    :param splash: Splash dialog to update user on what is currently going on
    :param connection: Connection to the Shotgun server.

    :returns: The error code to return to the shell.
    """
    # show the splash screen
    splash.show()
    splash.raise_()
    splash.activateWindow()
    splash.set_message("Looking up site configuration.")
    app.processEvents()

    _assert_toolkit_enabled(splash, connection)

    logger.debug("Getting the default site config")
    default_site_config, pc = shotgun_desktop.paths.get_default_site_config_root(connection)

    # try and import toolkit
    toolkit_imported = False
    try:
        if os.path.exists(default_site_config):
            if "--reset-site" not in sys.argv:
                logger.info("Trying site config from '%s'" % default_site_config)
                sgtk = __import_sgtk_from_path(default_site_config, app_bootstrap)
                toolkit_imported = True
            else:
                logger.info("Resetting site configuration at '%s'" % default_site_config)
                splash.set_message("Resetting site configuration ...")
                shutil.rmtree(default_site_config)
    except Exception:
        pass

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

        # try again after the initialization is done
        logger.debug("Importing sgtk after initialization")

        sgtk = __import_sgtk_from_path(core_path, app_bootstrap)

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
        sgtk = __import_sgtk_from_path(default_site_config, app_bootstrap)
        tk = sgtk.sgtk_from_path(default_site_config)

        # now localize the core to the config
        splash.set_message("Localizing core...")
        localize = tk.get_command("localize")
        localize.set_logger(logger)
        localize.execute({})

    tk = sgtk.sgtk_from_path(default_site_config)
    try:
        is_auto_path = tk.pipeline_configuration.is_auto_path()
    except sgtk.TankError, error:
        logger.exception(error)
        raise SitePipelineConfigurationNotFound(default_site_config)

    if is_auto_path:
        splash.set_message("Getting updates...")
        logger.info("Getting updates...")
        app.processEvents()

        # Downloads an upgrade, if available.
        startup_updated = upgrade_startup(
            splash,
            sgtk,
            app_bootstrap
        )

        core_update = tk.get_command("core")
        core_update.set_logger(logger)
        result = core_update.execute({})

        # If core was updated.
        if result["status"] == "updated":
            core_updated = True
        else:
            core_updated = False
            if result["status"] == "update_blocked":
                # Core update should not be blocked. Warn, because it is not a fatal error.
                logger.warning("Core update was blocked. Reason: %s" % result["reason"])
            elif result["status"] != "up_to_date":
                # Core update should not fail. Warn, because it is not a fatal error.
                logger.warning("Unexpected Core upgrade result: %s" % str(result))

        if core_updated and startup_updated:
            return __restart_app_with_countdown(splash, "Desktop and Core updated.")
        elif core_updated:
            return __restart_app_with_countdown(splash, "Core updated.")
        elif startup_updated:
            return __restart_app_with_countdown(splash, "Desktop updated.")

        updates = tk.get_command("updates")
        updates.set_logger(logger)
        updates.execute({})
    else:
        logger.info("Fixed core, skipping updates...")

    # initialize the tk-desktop engine for an empty context
    splash.set_message("Starting desktop engine.")
    app.processEvents()

    ctx = tk.context_empty()
    engine = sgtk.platform.start_engine("tk-desktop", tk, ctx)

    # engine will take over logging
    app_bootstrap.tear_down_logging()

    # reset PYTHONPATH and PYTHONHOME if they were overridden by the application
    if "SGTK_DESKTOP_ORIGINAL_PYTHONPATH" in os.environ:
        os.environ["PYTHONPATH"] = os.environ["SGTK_DESKTOP_ORIGINAL_PYTHONPATH"]
    if "SGTK_DESKTOP_ORIGINAL_PYTHONHOME" in os.environ:
        os.environ["PYTHONHOME"] = os.environ["SGTK_DESKTOP_ORIGINAL_PYTHONHOME"]

    if not __supports_authentication_module(sgtk):
        raise UpgradeCoreError(default_site_config)

    # and run the engine
    logger.debug("Running tk-desktop")
    startup_version = get_location(sgtk, app_bootstrap).get("version") or "Undefined"
    return engine.run(splash, version=app_bootstrap.get_version(), startup_version=startup_version)


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


def main(**kwargs):
    """
    Main

    :params app_bootstrap: AppBootstrap instance, used to get information from
        the installed application as well as updating the startup description
        location.

    :returns: Error code for the process.
    """
    logger.debug("Running main from %s" % __file__)
    # Create some ui related objects
    app, splash = __init_app()

    # We might crash before even initializing the authenticator, so instantiate
    # it right away.
    shotgun_authenticator = None
    # We have to import this in a separate try catch block because we'll be using
    # shotgun_authentication in the following catch statements.

    app_bootstrap = kwargs["app_bootstrap"]

    try:
        # get the shotgun authentication module.
        shotgun_authentication = __import_shotgun_authentication_from_path(app_bootstrap)
    except:
        __handle_unexpected_exception(splash, shotgun_authenticator)

    # We have gui and the authentication module, now do the rest.
    try:
        # Authenticate
        shotgun_authenticator, connection = __do_login(splash, shotgun_authentication, app_bootstrap)
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
                app_bootstrap
            )
    except RequestRestartException:
        subprocess.Popen(sys.argv)
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
