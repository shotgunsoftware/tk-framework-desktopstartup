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
import re

from tank_vendor.shotgun_authentication import ShotgunAuthenticator
import shotgun_desktop.paths
import shotgun_desktop.startup
import sgtk


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

        self._remove_site_configurations()

        # Path to the folder for this test.
        self._test_folder = os.path.join(tempfile.gettempdir(), "shotgun_desktop_integration_tests", self._testMethodName)

        # Clear the test folder (previous's run site configuration and logs)
        if os.path.exists(self._test_folder):
            shutil.rmtree(self._test_folder)
        os.makedirs(self._test_folder)

        test_project_name = "ShotgunDesktopIntegrationTests"

        self._project_link = self.sg.find_one("Project", [["name", "is", test_project_name]])
        if not self._project_link:
            self._project_link = self.sg.create("Project", {"name": test_project_name})

        self.site_config_folder = os.path.join(self._test_folder, "site")

        self._fixtures_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures"
        )

    def _remove_site_configurations(self):
        """
        Removes all site configurations for the current site.
        """
        # Retrieve any pipeline configurations that could be associated to a site configuration.
        pcs = shotgun_desktop.paths.get_default_site_config_roots(self.sg, ["id"])
        # Delete them.
        self.sg.batch([
            {"request_type": "delete", "entity_type": "PipelineConfiguration", "entity_id": pc["id"]} for
            pc in pcs
        ])

    def _get_core_fixture_path(self, version):
        return os.path.join(self._fixtures_path, "core", version)

    def _launch_slave_process(self, core_version=None):
        """
        Launches the MockDesktop script
        """
        mockdesktop_script = os.path.join(
            os.path.split(__file__)[0],
            "mockdesktop.py"
        )
        env = {
            "PYTHONPATH": os.path.pathsep.join(sys.path),
        }

        if core_version:
            env["SGTK_CORE_DEBUG_LOCATION"] = self._get_core_fixture_path(core_version)

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

    # Parses Exception,ExceptionType,base64-encoded-string or nothing
    # Retursn ExceptionType and the text after the,
    # If \n are present in the output buffer, those will be matched as well.
    EXCEPTION_RE = re.compile(r"Exception:(.*),([a-zA-Z0-9\n]*={1,2}|)")

    def _extract_exception(self, process):
        stdout, _ = process.communicate()
        res = self.EXCEPTION_RE.match(stdout)
        if not res:
            return None
        groups = res.groups()
        return groups[0], groups[1].decode("base64")

    def _assert_no_exception(self, process):
        ex = self._extract_exception(process)
        if ex:
            print "Exception was thrown!"
            print "%s: %s" % ex
        self.assertIsNone(ex)

    def _assert_exception(self, process, ex_type):
        ex = self._extract_exception(process)
        if not ex:
            print "Expecting %s exception, but nothing was found!" % ex_type
            self.assertIsNotNone(ex)
        elif ex[0] != ex_type:
            print "Expecting %s exception, got %s instead!" % (ex_type, ex)
        self.assertEqual(ex[0], ex_type)

    def test_create_with_no_template(self):
        """
        Tests startup without any pipeline configuration already established. A pipeline
        configuration with no project should be created.
        """
        # This will setup the site from scratch
        process = self._launch_slave_process()
        self._assert_no_exception(process)

        tk = sgtk.sgtk_from_path(self.site_config_folder)
        self.assertTrue(tk.pipeline_configuration.is_site_configuration())

        process = self._launch_slave_process()
        self._assert_no_exception(process)

    def test_reuse_with_no_template(self):
        """
        Tests startup without a pipeline configuration already established in Shotgun. A pipeline
        configuration with no project should be created.
        """
        pc = self.sg.create("PipelineConfiguration", {
            "code": "Primary"
        })
        # This will setup the site from scratch
        process = self._launch_slave_process()
        self._assert_no_exception(process)

        tk = sgtk.sgtk_from_path(self.site_config_folder)

        # Make sure we have the site config and the right pipeline configuration.
        self.assertTrue(tk.pipeline_configuration.is_site_configuration())
        self.assertEqual(tk.pipeline_configuration.get_shotgun_id(), pc["id"])

        process = self._launch_slave_process()
        self._assert_no_exception(process)

    def test_reuse_with_template(self):
        """
        Tests startup with a pipeline configuration already configured with the template project.
        """
        # Create Pipeline configuration on template project.
        pc = self.sg.create("PipelineConfiguration", {
            "project": self._template_project_link,
            "code": "Primary"
        })

        # This will setup the site from scratch.
        process = self._launch_slave_process()
        self._assert_no_exception(process)

        tk = sgtk.sgtk_from_path(self.site_config_folder)
        # is_site_configuration is True only for a True site configuration, i.e. project_id is None
        self.assertFalse(tk.pipeline_configuration.is_site_configuration())
        self.assertEqual(tk.pipeline_configuration.get_project_id(), self._template_project_link["id"])
        self.assertEqual(tk.pipeline_configuration.get_shotgun_id(), pc["id"])

        # This should be able to reuse the config.
        process = self._launch_slave_process()
        self._assert_no_exception(process)

    def test_unexpected_config(self):
        """
        Tests startup with a site configured locally but nothing in Shotgun.
        """
        # Let's fake a toolkit install
        os.makedirs(os.path.join(self._test_folder, "site", "config"))
        process = self._launch_slave_process()
        # startup should complain about an unexpected config.
        self._assert_exception(process, "UnexpectedConfigFound")

    def _upgrade_core(self, version):
        core_to_upgrade = os.path.join(self.site_config_folder, "install")
        core_upgrader = os.path.join(self._get_core_fixture_path(version), "_core_upgrader.py")
        with open(os.devnull, "w") as f:
            subprocess.check_call(
                [
                    sys.executable,
                    core_upgrader,
                    "migrate",
                    core_to_upgrade
                ],
                stdout=f,
                stderr=f
            )

    def test_engine_update_reboot(self):
        """
        Tests startup with a site configured locally but nothing in Shotgun.
        """
        # Install Toolkit
        process = self._launch_slave_process()
        self._assert_no_exception(process)
        # Downgrade the core so that the next time we launch we are getting upgraded
        self._upgrade_core("0.16.4")
        # Start again
        process = self._launch_slave_process()
        # startup should Restart after upgrading the core.
        self._assert_exception(process, "RequestRestartException")
