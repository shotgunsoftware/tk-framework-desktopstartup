# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import subprocess
from unittest2 import TestCase
import os
import sys

import tempfile
import shutil

from tank_vendor.shotgun_authentication import ShotgunAuthenticator


class TestShotgun610(TestCase):

    def setUp(self):
        """
        Makes sure we are logged in to the site for unit testing
        """
        # Make sure we are logged in to set up the test on the server side.
        self.user = ShotgunAuthenticator().get_user()
        self.sg = self.user.create_sg_connection()

        # Find the template project
        self._template_project_link = self.sg.find_one("Project", [["name", "is", "Template Project"]], ["id"])

        # Delete all pipeline configurations that the Desktop might use.
        pcs = self.sg.find("PipelineConfiguration", [{
            "filter_operator": "any",
            "filters": [
                ["project", "is", None],
                {
                    "filter_operator": "all",
                    "filters": [
                        ["project.Project.name", "is", "Template Project"],
                        ["project.Project.layout_project", "is", None]
                    ]
                }
            ]}], ["id"])
        self.sg.batch([
            {"request_type": "delete", "entity_type": "PipelineConfiguration", "entity_id": pc["id"]} for
            pc in pcs
        ])

        # Path to the folder for this test.
        self._test_folder = os.path.join(tempfile.gettempdir(), "shotgun_desktop_integration_tests", self._testMethodName)

        # Clear the test folder (previous's run site configuration and logs)
        if os.path.exists(self._test_folder):
            shutil.rmtree(self._test_folder)
        os.makedirs(self._test_folder)

    def _launch_slave_process(self):
        mockdesktop_script = os.path.join(
            os.path.split(__file__)[0],
            "mockdesktop.py"
        )
        env = {
            "PYTHONPATH": os.path.pathsep.join(sys.path),
        }

        sub_process = subprocess.Popen(
            [
                sys.executable,
                mockdesktop_script,
                "--test-folder", self._test_folder,
                "--test-name", self._testMethodName
            ],
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            env=env
        )

        return sub_process

    def test_from_scratch_no_template(self):
        # This will setup the site from scratch
        process = self._launch_slave_process()
        (stdout, _) = process.communicate()

        process = self._launch_slave_process()
        (stdout, _) = process.communicate()

    def test_from_scratch_with_template(self):
        # Pipeline configuration.
        self.sg.create("PipelineConfiguration", {
            "project": self._template_project_link,
            "code": "Primary"
        })

        # This will setup the site from scratch
        process = self._launch_slave_process()
        (stdout, _) = process.communicate()

        process = self._launch_slave_process()
        (stdout, _) = process.communicate()
