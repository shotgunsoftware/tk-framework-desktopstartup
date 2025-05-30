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
import time
import subprocess
import traceback

# initialize logging
import logging

# The value of sys.executable under multiple platforms and multiple versions
# of Desktop is unreliable. Therefore, we're patch the value if the executable
# name is not Shotgun or ShotGrid.
#
# So, we'll use sys.prefix which is properly set and backtrack to the executable.
# When the executable is fixed we should come back here and put a check for the version
# number so we stop updating sys.executable

# Grab the name and the executable
executable_name, ext = os.path.splitext(os.path.basename(sys.executable or ""))

# If the executable is not named Shotgun or ShotGrid, then we need to patch sys.executable.
if executable_name.lower() not in ["shotgun", "shotgrid"]:
    # On macOS, sys.prefix is set to /Applications/Shotgun.app/Contents/Resources/python,
    # so we need to drill down differently for the executable folder than on other platforms
    if sys.platform == "darwin":
        bin_dir = os.path.join(sys.prefix, "..", "..", "MacOS")
    else:
        # On Linux and Windows, the sys.prefix points to Shotgun/Python, so we only
        # need to move up one folder.
        bin_dir = os.path.join(sys.prefix, "..")

    # Set the executable name and make sure to put back in the extension for Windows.
    sys.executable = os.path.normpath(os.path.join(bin_dir, "Shotgun%s" % ext))


def _enumerate_per_line(items):
    """
    Enumerate all items from an array, one line at a time.

    For example,
        - one
        - two
        - three

    :returns: The formatted output.
    """
    return "\n".join("- {}".format(item) for item in items)


def _env_not_set_or_split(var_name):
    """
    Format a PATH-like environment variable for output.

    :param str var_name: Name of the env var.
    :returns: "Not Set" if variable is not set, a bullet list otherwise.
    """
    if var_name not in os.environ:
        return "Not Set"
    else:
        # Add a \n before the first item so each item in the output start from the
        # beginning of the line. Otherwise you'd get
        # varname: - one
        # - two
        # - three.
        return "\n" + _enumerate_per_line(os.environ[var_name].split(os.path.pathsep))


logger = logging.getLogger("tk-desktop.startup")
logger.info("------------------ Desktop Startup Framework Startup ------------------")
logger.info(
    """
Python
======
Executable: {executable}
Version: {major}.{minor}.{micro}
sys.path:
{sys_path}

Environment variables
=====================
PATH: {path}
PYTHONHOME: {python_home}
PYTHONPATH: {python_path}
SGTK_DESKTOP_ORIGINAL_PYTHONHOME: {original_python_home}
SGTK_DESKTOP_ORIGINAL_PYTHONPATH: {original_python_path}
""".format(
        executable=sys.executable,
        major=sys.version_info.major,
        minor=sys.version_info.minor,
        micro=sys.version_info.micro,
        sys_path=_enumerate_per_line(sys.path),
        path=_env_not_set_or_split("PATH"),
        python_home=os.environ.get("PYTHONHOME", "Not Set"),
        python_path=_env_not_set_or_split("PYTHONPATH"),
        original_python_home=os.environ.get(
            "SGTK_DESKTOP_ORIGINAL_PYTHONHOME", "Not Set"
        ),
        original_python_path=_env_not_set_or_split("SGTK_DESKTOP_ORIGINAL_PYTHONPATH"),
    )
)


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


def init_sgtk_logger():
    """
    Initialize the SGTK logger now and not later (main) so we don't miss logs
    coming from sgtk. For instance, before this change, we were missing any
    logs coming from the QtImporter because the logger was not initialized
    already.
    """

    # Do not import sgtk globally to avoid using the wrong sgtk once we
    # bootstrap in the right config.
    import sgtk

    sgtk.LogManager().initialize_base_file_handler("tk-desktop")


# Add Toolkit to the path.
add_to_python_path(
    os.path.join(
        "..",
        "tk-core",
    ),
    "SGTK_CORE_LOCATION",
    "tk-core",
)

init_sgtk_logger()

# now proceed with non builtin imports
from .qt import QtCore, QtGui

import shotgun_desktop.paths
import shotgun_desktop.splash
from shotgun_desktop.desktop_message_box import DesktopMessageBox
from shotgun_desktop.upgrade_startup import upgrade_startup
from shotgun_desktop.location import get_startup_descriptor

from shotgun_desktop.errors import (
    ShotgunDesktopError,
    RequestRestartException,
    UpgradeEngine200Error,
    EngineNotCompatibleWithDesktop16,
    UpgradeCoreError,
    UpgradeCorePython3Error,
    InvalidPipelineConfiguration,
)

from tank.util.version import (
    is_version_older_or_equal,
    is_version_newer_or_equal,
)


global_debug_flag_at_startup = None


def __restore_global_debug_flag():
    """
    Restores the global debug flag
    """
    global global_debug_flag_at_startup
    import sgtk

    # If there is no LogManager for the new core, there's no need to restore any flag.
    if hasattr(sgtk, "LogManager"):
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
    if engine.version.lower() == "undefined":
        logger.warning(
            "The version of the tk-desktop engine is undefined. "
            "Assuming engine it supports sgtk.authentication module."
        )
        return True
    return is_version_newer_or_equal(engine.version, "v2.0.0")


def __desktop_engine_supports_websocket(engine):
    """
    Tests if the engine implements the browser integration. All versions above 2.1.0 supports
    login based authentication.

    :param engine: The desktop engine to test.

    :returns: True if the engine supports the authentication module, False otherwise.
    """
    if engine.version.lower() == "undefined":
        logger.warning(
            "The version of the tk-desktop engine is undefined. "
            "Assuming it has built-in browser integration support."
        )
        return True
    return is_version_newer_or_equal(engine.version, "v2.1.0")


def __supports_pipeline_configuration_upgrade(pipeline_configuration):
    """
    Tests if the given pipeline configuration supports the None project id.

    :param sgtk: A pipeline configuration.

    :returns: True if the pipeline configuration can have a None project, False otherwise.
    """
    # if the authentication module is not supported, this method won't be present on the core.
    return hasattr(pipeline_configuration, "convert_to_site_config")


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


def __optional_state_cleanup(splash, shotgun_authenticator, app_bootstrap):
    """
    Cleans the Desktop state if the alt key is pressed. Restarts the Desktop when done.

    :param splash: Splash screen widget.
    :param shotgun_authenticator: Shotgun authenticator used to logout if alt is pressed.
    :params app_bootstrap: The application bootstrap.
    """
    # If the application was launched holding the alt key, log the user out.
    if (
        QtGui.QApplication.queryKeyboardModifiers() & QtCore.Qt.AltModifier
    ) == QtCore.Qt.AltModifier:
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
    startup_updated = upgrade_startup(splash, sgtk, app_bootstrap)
    if startup_updated:
        # We need to restore the global debug logging setting prior to
        # restarting the app so that forced debug logging is not remembered
        # as the startup state.  Once Desktop relaunches it will resume forced
        # debug logging until core swap, when the original launch setting is
        # restored.
        __restore_global_debug_flag()
        __restart_app_with_countdown(splash, "Flow Production Tracking updated.")

    splash.set_message("Looking up site configuration.")

    connection = user.create_sg_connection()

    splash.show()

    logger.debug("Getting the default site configuration.")
    (
        pc_path,
        pc,
        toolkit_classic_required,
    ) = shotgun_desktop.paths.get_pipeline_configuration_info(connection)

    # We need to toggle the global debug logging setting back prior to swapping
    # core. Cores older than v0.18.117 do not manage the TK_DEBUG environment
    # variable when global debug is toggled, so we can end up in a situation
    # where the new core in desktopstartup toggles it on, setting the env var,
    # and then when the toggle off occurs we end up with the older core in the
    # site config NOT purging the TK_DEBUG env var. The result is that any
    # subprocesses spawned then end up with debug logging on when the user
    # didn't ask for it. This impacts engine command execution from both Desktop
    # and via browser integration. It is the biggest issue with browser
    # integration, however, as the debug logs are reported back to the web
    # app from the desktopserver RPC API, and the user is presented with a
    # dialog full of debug log messages.
    __restore_global_debug_flag()

    # We're about to bootstrap, so remove sgtk from our scope so that if we add
    # code that uses it after the bootstrap we have to import the
    # new core.
    del sgtk
    try:
        if toolkit_classic_required:
            engine = __start_engine_in_toolkit_classic(app, splash, user, pc, pc_path)
        else:
            engine = __start_engine_in_zero_config(app, app_bootstrap, splash, user)
    except SyntaxError:
        # Try to see if this SyntaxError might be due to non-Python 3 compatible
        # code.

        # If we're not in Python 3, we can reraise right away.
        if sys.version_info[0] != 3:
            raise

        # Reach the end of the stack.
        exc_type, exc_value, current_stack_frame = sys.exc_info()
        deepest = None
        while deepest is None:
            if current_stack_frame.tb_next is None:
                deepest = current_stack_frame
                break
            else:
                current_stack_frame = current_stack_frame.tb_next

        # If the syntax error was from somewhere in the tk-desktop engine,
        # then it's likely the engine is too old. This will yield false-positives
        # in development when making syntax errors, but is robust enough
        # for released code.
        if (
            "python/tk_desktop/".replace("/", os.path.sep)
            in deepest.tb_frame.f_code.co_filename
        ):
            raise EngineNotCompatibleWithDesktop16(app_bootstrap.get_version())
        raise
    except Exception as e:
        # We may end up here when running with an older version of core pre 0.19.
        # If we are running a pre 0.19 version of core and we are using Python 3
        # Then we will likely hit an error: ModuleNotFoundError: No module named 'Cookie'
        if "No module named 'Cookie'" in e.args:
            raise UpgradeCorePython3Error()
        raise

    return __post_bootstrap_engine(splash, app_bootstrap, engine, settings)


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
    mgr.progress_callback = (
        lambda progress_value, message: __bootstrap_progress_callback(
            splash, app, progress_value, message
        )
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
            if not __supports_pipeline_configuration_upgrade(
                ctx.sgtk.pipeline_configuration
            ):
                raise UpgradeCoreError(
                    "Running a site configuration without the Template Project requires core v0.16.8 "
                    "or higher.",
                    pc_path,
                )

            # If the configuration on disk is not the site configuration, update it to the site config.
            if not ctx.sgtk.pipeline_configuration.is_site_configuration():
                ctx.sgtk.pipeline_configuration.convert_to_site_config()

        splash.set_message("Launching Engine...")

    # We need to validate a few things before the engine starts.
    mgr.pre_engine_start_callback = pre_engine_start_callback

    engine = mgr.bootstrap_engine("tk-desktop")

    if not __desktop_engine_supports_authentication_module(engine):
        raise UpgradeEngine200Error(
            "This version of the PTR desktop app only supports tk-desktop engine 2.0.0 and higher.",
            pc_path,
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
        "sgtk:descriptor:app_store?name=tk-config-basic",
    )
    mgr.progress_callback = (
        lambda progress_value, message: __bootstrap_progress_callback(
            splash, app, progress_value, message
        )
    )
    mgr.plugin_id = "basic.desktop"

    # Add the bundle cache if there is one available
    bundle_cache_path = app_bootstrap.get_bundle_cache_location()
    if bundle_cache_path:
        mgr.bundle_cache_fallback_paths.append(bundle_cache_path)

    mgr.pre_engine_start_callback = lambda ctx: __restore_global_debug_flag()

    return mgr.bootstrap_engine("tk-desktop")


def __post_bootstrap_engine(splash, app_bootstrap, engine, settings):
    """
    Called after bootstrapping the engine. Mainly use to transition logging to the
    engine and launch the main event loop.

    :param splash: Splash screen widget.
    :param app_bootstrap: Application bootstrap logic.
    :param engine: Toolkit engine that was bootstrapped.
    :param settings: The application's settings.

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

    # Uses the old API as we may have bootstrap into an old core.
    startup_version = startup_desc.get_version()

    # If the site config is running an older version of the desktop engine, it
    # doesn't include browser integration, so we'll launch it ourselves.
    server = None

    try:
        return _run_engine(
            engine, splash, startup_version, app_bootstrap, startup_desc, settings
        )
    except TypeError as e:
        # When running in Python 3 mode and launching into tk-desktop 2.5.0, the engine
        # does support PySide2, but the engine doesn't yet support Python 3 fully and the gui
        # can't initialize, so a TypeError will be launched by qRegisterResourceData.
        # So catch it, and let the user know that this error is due to missing Python3
        # support for the engine.
        if sys.version_info[0] != 3:
            raise
        if (
            "PySide2.QtCore.qRegisterResourceData' called with wrong argument types"
            in str(e)
        ):
            raise EngineNotCompatibleWithDesktop16(app_bootstrap.get_version())
        raise


def __ensure_engine_compatible_with_qt_version(engine, app_version):
    """
    Make sure the tk-desktop engine is compatible with the PySide version we distribute
    with Desktop.

    When using tk-desktop versions before v2.5.0, PySide2 builds of desktop can't launch
    DCCs because a QAction's signal emit an unexpected boolean that crashes older tk-desktop
    builds.
    """
    # If we can't find the version, we assume it's good.
    if engine.version.lower() == "undefined":
        logger.warning(
            "The version of the tk-desktop engine is undefined. "
            "Assuming the engine is compatible with the builtin Qt."
        )
        return

    # tk-desktop 2.5.0 introduced Python 3 and PySide2 support while being backward
    # compatible with PySide, so it can't be a problem.
    if is_version_newer_or_equal(engine.version, "v2.5.0"):
        return

    # Versions of desktop older than v2.5.0 have issues with desktop 1.6.1+, so raise an error.
    if is_version_newer_or_equal(app_version, "v1.6.1"):
        raise EngineNotCompatibleWithDesktop16(app_version)


def _is_pipeline_config_disabled(error_message):
    """
    Check if the 'PipelineConfiguration' entities has been
    disabled from the user site.

    :param error_message: The error string that will be displayed in a message box.
    :returns: True if the error message matches with the expected pipeline config
          disabled message.
    """
    # expected error message when 'PipelineConfiguration' entities has been
    # disabled from the user site.
    pipeline_config_disabled_message = (
        "API read() invalid/missing string entity 'type':\n"
        '{"type"=>"PipelineConfiguration"'
    )
    return pipeline_config_disabled_message in str(error_message)


def _run_engine(engine, splash, startup_version, app_bootstrap, startup_desc, settings):
    __ensure_engine_compatible_with_qt_version(engine, app_bootstrap.get_version())

    return engine.run(
        splash,
        version=app_bootstrap.get_version(),
        startup_version=startup_version,
        startup_descriptor=startup_desc,
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
    DesktopMessageBox.critical("Flow Production Tracking Error", error_message)
    # If we are logged in, we should log out so the user is not stuck in a loop of always
    # automatically logging in each time the app is launched again
    if shotgun_authenticator:
        shotgun_authenticator.clear_default_user()


def __handle_unexpected_exception(
    splash, shotgun_authenticator, error_message, app_bootstrap
):
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

    import sgtk

    exc_type, exc_value, exc_traceback = sys.exc_info()

    if hasattr(sgtk, "LogManager"):
        log_location = sgtk.LogManager().base_file_handler.baseFilename
    else:
        log_location = app_bootstrap.get_logfile_location()

    logger.exception("Fatal error, user will be logged out.")

    if _is_pipeline_config_disabled(error_message):
        formatted_error_message = (
            "PipelineConfiguration entities are disabled for your site. "
            "Head to your <a href={link}>Site Preferences</a>, enable them and try again.\n"
            "Error: {error}\n"
            "For more information, see the log file at {log}.".format(
                link=(
                    "{shotgrid_base_url}/preferences".format(
                        shotgrid_base_url=shotgun_authenticator.get_default_host()
                    )
                ),
                error=str(error_message),
                log=log_location,
            )
        )

    else:
        formatted_error_message = (
            "Something went wrong in the PTR desktop app! If you <a href={link}>contact us</a> "
            "we'll help you diagnose the issue.\n"
            "Error: {error}\n"
            "For more information, see the log file at {log}.".format(
                link=sgtk.support_url,
                error=str(error_message),
                log=log_location,
            )
        )

    DesktopMessageBox.critical(
        "Flow Production Tracking Error",
        formatted_error_message,
        detailed_text="".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        ),
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
        Retrieves the bundle cache that is distributed with the PTR desktop app.

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

    # Core will take over logging
    app_bootstrap.tear_down_logging()

    logger = sgtk.LogManager.get_logger(__name__)
    logger.debug("Running main from %s" % __file__)

    # Create some ui related objects
    app, splash = __init_app()

    splash.set_version(
        f"{app_bootstrap.get_version()} - Python {sys.version_info[0]}.{sys.version_info[1]}"
    )

    # We might crash before even initializing the authenticator, so instantiate
    # it right away.
    shotgun_authenticator = None
    # PTR desktop app startup has always been logging every debug string to disk since the new authentication from 0.16
    # was released and the startup has been difficult to work with and debug, so keep that logic in place during the
    # startup sequence. It will be restored during the ToolkitManager's pre_engine_start_callback.
    __backup_global_debug_flag()
    sgtk.LogManager().global_debug = True

    from sgtk import authentication
    from sgtk.descriptor import InvalidAppStoreCredentialsError
    from sgtk.authentication import (
        set_shotgun_authenticator_support_web_login,
        ShotgunSamlUser,
    )

    try:
        # Reading user settings from disk.
        settings = sgtk.util.UserSettings()

        # It is very important to decouple logging in from creating the shotgun authenticator.
        # If there is an error during auto login, for example proxy settings changed and you
        # can't connect anymore, we need to be able to log the user out.
        shotgun_authenticator = sgtk.authentication.ShotgunAuthenticator()
        if os.environ.get("SGTK_DESKTOP_SUPPORT_WEB_LOGIN_TRUE"):
            logger.info(
                "Indicating to the Desktop that web login is supported and to be used."
            )
            set_shotgun_authenticator_support_web_login(True)
        __optional_state_cleanup(splash, shotgun_authenticator, app_bootstrap)

        user = __do_login(splash, shotgun_authenticator)

        if not user:
            logger.info("Login canceled. Quitting.")
            return 0

        # In the case where the site is using SSO, the user needs to renew
        # its claims regularily. So we kick off a separate newewal thread.
        if isinstance(user, ShotgunSamlUser):
            logger.debug("Starting SSO claims renewal")
            user.start_claims_renewal()
        else:
            logger.debug("Not using SSO")

        # Now that we are logged, we can proceed with launching the
        # application.
        exit_code = __launch_app(app, splash, user, app_bootstrap, settings)
        return exit_code
    except RequestRestartException:
        subprocess.Popen(sys.argv, close_fds=True)
        return 0
    except authentication.AuthenticationCancelled:
        # The user cancelled an authentication request while the app was running, log him out.
        splash.hide()
        shotgun_authenticator.clear_default_user()
        return 0
    except InvalidAppStoreCredentialsError as e:
        __handle_exception(splash, shotgun_authenticator, str(e))
        return -1
    except ShotgunDesktopError as e:
        __handle_exception(splash, shotgun_authenticator, str(e))
        return -1
    except Exception as e:
        __handle_unexpected_exception(splash, shotgun_authenticator, e, app_bootstrap)
        return -1
