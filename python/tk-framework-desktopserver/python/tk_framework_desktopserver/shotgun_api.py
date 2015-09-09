# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


class ShotgunAPI():
    """
    Public API For all the commands that can be sent from Shotgun Client.

    Every function of this class is accessible to outside clients.

    Every command receives a data dictionary of the command sent from the client
    """

    _SHOTGUN_INTEGRATION_API_MAJOR = 0
    _SHOTGUN_INTEGRATION_API_MINOR = 1
    _SHOTGUN_INTEGRATION_API_PATCH = 0

    """
    Public API
    Callable methods from client. Every one of these methods can be called from the client.
    """
    public_api = ["echo", "open", "executeToolkitCommand", "executeTankCommand",
                  "pickFileOrDirectory", "pickFilesOrDirectories", "version",
                  "getProjectActions"]

    def __init__(self, host, process_manager):
        """
        API Constructor.
        Keep initialization pretty fast as it is created on every message.

        :param host: Host interface to communicate with. Abstracts the client.
        :param process_manager: Process Manager to use to interact with os processes.
        """
        self.host = host
        self.process_manager = process_manager

    def _handle_toolkit_output(self, out, err, return_code):
        """
        Used as a callback to handle toolkit command output.

        :param out: String Stdout output.
        :param err: String Stderr output.
        :param return_code: Int Process Return code.
        """

        reply = {}
        reply["retcode"] = return_code
        reply["out"] = out
        reply["err"] = err

        self.host.reply(reply)

    def open(self, data):
        """
        Open a file.

        :param data: Message data. ["filepath": String]
        """

        try:
            # Retrieve filepath
            filepath = data.get("filepath")
            result = self.process_manager.open(filepath)

            # Send back information regarding the success of the operation.
            reply = {}
            reply["result"] = result

            self.host.reply(reply)
        except Exception, e:
            self.host.report_error(e.message)

    def echo(self, data):
        """
        Simple message echo. Used for test and as a simple example.

        :param data: Message data. ["message": String]
        """

        # Create reply object
        reply = {}
        reply["message"] = data.get("message")

        self.host.reply(reply)

    def executeToolkitCommand(self, data):
        """
        Executes a toolkit command.

        :param data: Message data {"pipelineConfigPath", "command", "args"}
        """
        pipeline_config_path = data.get("pipelineConfigPath")
        command = data.get("command")
        args = data.get("args")

        # Verify arguments
        if not args:
            args = []

        if not isinstance(args, list):
            message = "ExecuteToolkitCommand 'args' must be a list."
            self.host.report_error(message)

        try:
            (out, err, returncode) = self.process_manager.execute_toolkit_command(pipeline_config_path, command, args)
            self._handle_toolkit_output(out, err, returncode)
        except Exception, e:
            self.host.report_error(e.message)

    def executeTankCommand(self, data):
        """
        Alias for executeToolkitCommand
        """
        return self.executeToolkitCommand(data)

    def getProjectActions(self, data):
        """
        Get all actions from all environments for given project
        :param data: Message data {"pipelineConfigPaths"}
        """
        pipeline_config_paths = data.get("pipelineConfigPaths")
        actions = self.process_manager.get_project_actions(pipeline_config_paths)

        reply = {}
        reply["actions"] = actions

        self.host.reply(reply)

    def pickFileOrDirectory(self, data):
        """
        Pick single file or directory
        :param data: Message data {} (no data expected)
        """

        files = self.process_manager.pick_file_or_directory(False)
        self.host.reply(files)

    def pickFilesOrDirectories(self, data):
        """
        Pick multiple files or directory.
        :param data: Message data {} (no data expected)
        """

        files = self.process_manager.pick_file_or_directory(True)
        self.host.reply(files)

    def version(self, data=None):
        """
        Retrives the API version.
        :param data: Message data {} (no data expected)
        """
        reply = {}
        reply["major"] = self._SHOTGUN_INTEGRATION_API_MAJOR
        reply["minor"] = self._SHOTGUN_INTEGRATION_API_MINOR
        reply["patch"] = self._SHOTGUN_INTEGRATION_API_PATCH

        self.host.reply(reply)
