# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import os
import glob
from command import Command

from PySide import QtGui, QtCore
from sgtk_file_dialog import SgtkFileDialog


def _create_invoker():
    # If we are already in the main thread, no need for an invoker, invoke directly in this thread.
    if QtCore.QThread.currentThread() == QtGui.QApplication.instance().thread():
        return lambda fn, *args, **kwargs: fn(*args, **kwargs)

    class MainThreadInvoker(QtCore.QObject):
        """
        Class that allows sending message to the main thread. This can be useful
        when a background thread needs to prompt the user via a dialog. The
        method passed into the invoker will be invoked on the main thread and
        the result, either a return value or exception, will be brought back
        to the invoking thread as if it was the thread that actually executed
        the code.
        """
        def __init__(self):
            """
            Constructor.
            """
            QtCore.QObject.__init__(self)
            self._res = None
            self._exception = None
            # Make sure that the invoker is bound to the main thread
            self.moveToThread(QtGui.QApplication.instance().thread())

        def __call__(self, fn, *args, **kwargs):
            """
            Asks the MainTheadInvoker to call a function with the provided parameters in the main
            thread.
            :param fn: Function to call in the main thread.
            :param args: Array of arguments for the method.
            :param kwargs: Dictionary of named arguments for the method.
            :returns: The result from the function.
            """
            self._fn = lambda: fn(*args, **kwargs)
            self._res = None

            QtCore.QMetaObject.invokeMethod(self, "_do_invoke", QtCore.Qt.BlockingQueuedConnection)

            # If an exception has been thrown, rethrow it.
            if self._exception:
                raise self._exception
            return self._res

        @QtCore.Slot()
        def _do_invoke(self):
            """
            Execute function and return result
            """
            try:
                self._res = self._fn()
            except Exception, e:
                self._exception = e

    return MainThreadInvoker()


class ExecuteTankCommandError(Exception):
    pass


class ProcessManager(object):
    """
    OS Interface for Shotgun Commands.
    """

    platform_name = "unknown"

    def _get_toolkit_script_name(self):
        return "shotgun"

    def _get_toolkit_fallback_script_name(self):
        return "tank"

    def _get_launcher(self):
        """
        Get Launcher file name from environement.
        This provides an alternative way to launch applications and open files, instead of os-standard open.

        :returns: String Default Launcher filename. None if none was found,
        """
        return os.environ.get("SHOTGUN_PLUGIN_LAUNCHER")

    def _verify_file_open(self, filepath):
        """
        Verify that a file can be opened.

        :param filepath: String file path that should be opened.
        :raises: Exception If filepath cannot be opened.
        """

        if not os.path.exists(filepath):
            raise Exception("Error opening path [%s]. Path not found." % filepath)

    def _get_full_toolkit_path(self, pipeline_config_path):
        """
        Get the full path of the toolkit script.

        :param pipeline_config_path: String Pipeline folder
        :return: String File path of toolkit script (eg: c:/temp/tank)
        """
        exec_script = os.path.join(pipeline_config_path, self._get_toolkit_script_name())

        if not os.path.isfile(exec_script):
            exec_script = os.path.join(pipeline_config_path, self._get_toolkit_fallback_script_name())

        return exec_script

    def _verify_pipeline_configuration(self, pipeline_config_path):
        """
        Verify that the pipeline configuration provided to is valid.

        :param pipeline_config_path: String Pipeline configuration path
        :raises: Exception On invalid toolkit pipeline configuration.
        """
        if not os.path.isdir(pipeline_config_path):
            raise ExecuteTankCommandError("Could not find the Pipeline Configuration on disk: " + pipeline_config_path)

        exec_script = self._get_full_toolkit_path(pipeline_config_path)
        if not os.path.isfile(exec_script):
            raise ExecuteTankCommandError("Could not find the Toolkit command on disk: " + exec_script)

    def _launch_process(self, launcher, filepath, message_error="Error executing command."):
        """
        Standard way of starting a process and handling errors.

        :params launcher: Path of executable
        :params filepath: File to pass as executable argument.
        :params message_error: String to prefix error message in case of an error.
        :returns: Bool If the operation was successful
        """
        args = [launcher, filepath]
        return_code, out, err = Command.call_cmd(args)
        has_error = return_code != 0

        if has_error:
            raise Exception("{message_error}\nCommand: {command}\nReturn code: {return_code}\nOutput: {std_out}\nError: {std_err}"
                            .format(message_error=message_error, command=args, return_code=return_code, std_out=out, std_err=err))

        return True

    def open(self, filepath):
        """
        Opens a file with default os association or launcher found in environments. Not blocking.

        :param filepath: String file path (ex: "c:/file.mov")
        :return: Bool If the operation was successful
        """
        raise NotImplementedError("Open not implemented in base class!")

    def execute_toolkit_command(self, pipeline_config_path, command, args):
        """
        Execute Toolkit Command

        :param pipeline_config_path: String Pipeline configuration path
        :param command: Commands
        :param args: List Script arguments
        :returns: (stdout, stderr, returncode) Returns standard process output
        """
        self._verify_pipeline_configuration(pipeline_config_path)

        if not command.startswith("shotgun"):
            raise ExecuteTankCommandError("ExecuteTankCommand error. Command needs to be a shotgun command [{command}]".format(command=command))

        try:
            #
            # Get toolkit Script Path
            exec_script = self._get_full_toolkit_path(pipeline_config_path)

            # Get toolkit script argument list
            script_args = [command] + args

            #
            # Launch script
            exec_command = [exec_script] + script_args
            return_code, out, err = Command.call_cmd(exec_command)

            return (out, err, return_code)
        except Exception, e:
            raise Exception("Error executing toolkit command: " + e.message)

    def _add_action_output(self, actions, out, err, code):
        """
        Simple shortcut to quickly add process output to a dictionary
        """
        actions['out'] = out
        actions['err'] = err
        actions['retcode'] = code

    def get_project_actions(self, pipeline_config_paths):
        """
        Get all actions for all environments from project path

        Overly complicated way of keeping track of toolkit's get/cache action command.
        Currently creates a dictionary to keep track of all output (error code, stderr/stdout) from toolkit command.

        This code was previously part of the shotgun client and is therefore made to match the exact same behavior
        as a starting point, in order to always output the same error messages.

        It can (and should) be simplified to only output a single error (if any), at the end of all commands,
        without any return code or convoluted stderr/stdout embedded dictionaries.

        :param pipeline_config_paths: [String] Pipeline configuration paths
        """

        project_actions = {}
        for pipeline_config_path in pipeline_config_paths:

            try:
                self._verify_pipeline_configuration(pipeline_config_path)
                env_path = os.path.join(pipeline_config_path, "config", "env")
                env_glob = os.path.join(env_path, "shotgun_*.yml")
                env_files = glob.glob(env_glob)

                project_actions[pipeline_config_path] = {}
                shotgun_get_actions_dict = project_actions[pipeline_config_path]["shotgun_get_actions"] = {}
                shotgun_cache_actions_dict = project_actions[pipeline_config_path]["shotgun_cache_actions"] = {}

                for env_filepath in env_files:
                    env_filename = os.path.basename(env_filepath)
                    entity = os.path.splitext(env_filename.replace("shotgun_", ""))[0]
                    cache_filename = "shotgun_" + self.platform_name + "_" + entity + ".txt"

                    # Need to store where actions have occurred in order to give proper error message to client
                    # This could be made much better in the future by creating the actual final actions from here instead.
                    shotgun_get_actions_dict[env_filename] = {}
                    shotgun_cache_actions_dict[cache_filename] = {}

                    (out, err, code) = self.execute_toolkit_command(pipeline_config_path,
                                                                    "shotgun_get_actions",
                                                                    [cache_filename, env_filename])
                    self._add_action_output(shotgun_get_actions_dict[env_filename], out, err, code)

                    if code == 1:
                        (out, err, code) = self.execute_toolkit_command(pipeline_config_path,
                                                                        "shotgun_cache_actions",
                                                                        [entity, cache_filename])
                        self._add_action_output(shotgun_cache_actions_dict[cache_filename], out, err, code)

                        if code == 0:
                            (out, err, code) = self.execute_toolkit_command(pipeline_config_path,
                                                                            "shotgun_get_actions",
                                                                            [cache_filename, env_filename])
                            self._add_action_output(shotgun_get_actions_dict[env_filename], out, err, code)
            except ExecuteTankCommandError, e:
                # Something is wrong with the pipeline configuration,
                # Clear any temporary result we might have accumulated for that pipeline
                # contiguration.
                project_actions[pipeline_config_path] = {}
                # Report the error that just happened.
                project_actions[pipeline_config_path]["error"] = True
                project_actions[pipeline_config_path]["error_message"] = str(e)
                # Move on to the next pipeline configuration.
                continue
                # We'll keep track of errors in pipeline configurations locally so that
                # errors can be tracked on a per pipeline basis, just like before.

        return project_actions

    def _pick_file_or_directory_in_main_thread(self, multi=False):
        dialog = SgtkFileDialog(multi, None)
        dialog.setResolveSymlinks(False)

        # Get result.
        result = dialog.exec_()

        files = []
        if result:
            selected_files = dialog.selectedFiles()

            for f in selected_files:
                if os.path.isdir(f):
                    f += os.path.sep
                files.append(f)

        return files

    def pick_file_or_directory(self, multi=False):
        """
        Pop-up a file selection window.

        Note: Currently haven't been able to get the proper native dialog to multi select
              both file and directories. Using this work-around for now.

        :param multi: Boolean Allow selecting multiple elements.
        :returns: List of files that were selected with file browser.
        """
        return _create_invoker()(self._pick_file_or_directory_in_main_thread, multi=multi)

    @staticmethod
    def create():
        """
        Create Process Manager according to current context (such as os, etc..)

        :returns: ProcessManager
        """

        if sys.platform == "darwin":
            from process_manager_mac import ProcessManagerMac
            return ProcessManagerMac()
        elif sys.platform == "win32":
            from process_manager_win import ProcessManagerWin
            return ProcessManagerWin()
        elif sys.platform.startswith("linux"):
            from process_manager_linux import ProcessManagerLinux
            return ProcessManagerLinux()
        else:
            raise RuntimeError("Unsupported platform: %s" % sys.platform)
