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
import logging

import tempfile
import shutil
import re

from tank_vendor import yaml
from tank_vendor.shotgun_authentication import ShotgunAuthenticator
import shotgun_desktop.paths
import shotgun_desktop.startup
from shotgun_desktop.initialization import initialize
import sgtk


class TestShotgun610(TestCase):

    def setUp(self):
        """
        - Makes sure we are logged in to the site for unit testing.
        - Caches template project link
        - caches the site configuration folder
        - clears all site configurations from shotgun
        - clears the unit test output folder (caches, site, logs)
        """
        # Make sure we are logged in to set up the test on the server side.
        self.user = ShotgunAuthenticator().get_user()
        self.sg = self.user.create_sg_connection()
        sgtk.set_authenticated_user(self.user)

        # Find the template project
        self.template_project_link = self.sg.find_one("Project", [["name", "is", "Template Project"]], ["id"])

        self._remove_site_configurations()

        # Path to the folder for this test.
        self.test_folder = os.path.join(tempfile.gettempdir(), "shotgun_desktop_integration_tests", self._testMethodName)
        # Path to the site configuration.
        self.site_config_folder = os.path.join(self.test_folder, "site")
        # Path to the fixtures root.
        self.fixtures_root = os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures"
        )

        # Clear the test folder (previous's run site configuration and logs)
        if os.path.exists(self.test_folder):
            shutil.rmtree(self.test_folder)
        os.makedirs(self.test_folder)

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

    def _upgrade_core(self, version):
        """
        Upgrades the core for the current site to a specific version.

        :param version: Version of the core to upgrade to.
        """
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

    def _get_core_fixture_path(self, version):
        """
        Returns the path to one of the cores used for testing.

        :param version: Version of the core requested.

        :returns: Path to the version of the core requested.
        """
        return os.path.join(self.fixtures_root, "core", version)

    def _setup_site_configuration(self, version=None, pc=None, auto_path=True):
        """
        Sets up a site configuration for the current test

        :param version: Version of the core to use to setup the site.
        :param pc: Pipeline configuration to use with this site configuration.
        """

        if not pc:
            pc = self.sg.create("PipelineConfiguration", {"project": None, "code": "Primary"})

        class MockSplash(object):
            def show(self):
                pass

            def set_message(self, *args):
                pass

            details = None

        if version:
            os.environ["SGTK_CORE_DEBUG_LOCATION"] = self._get_core_fixture_path(version)

        try:
            initialize(MockSplash(), self.sg, self.site_config_folder)
        finally:
            if version:
                del os.environ["SGTK_CORE_DEBUG_LOCATION"]

        # If not in auto path mode, update the pipeline configuration to lock this
        # config.
        if not auto_path:
            self.sg.update("PipelineConfiguration", pc["id"], {
                shotgun_desktop.paths.get_path_field_for_platform(): self.site_config_folder
            })

        # Write the pipeline configuration file
        self._write_config_file(["core", "pipeline_configuration.yml"], {
            "pc_id": pc["id"],
            "pc_name": pc["code"],
            "project_id": None if not pc["project"] else pc["project"]["id"],
            "project_name": "site",
            "published_file_entity_type": "PublishedFile",
            "use_shotgun_path_cache": True
        })

        self._write_config_file(["core", "roots.yml"], {})

    def _write_config_file(self, location_tokens, data):
        """
        Writes a configuration file inside the site configuration
        """
        location = os.path.join(*([self.site_config_folder, "config"] + location_tokens))
        with open(location, "w") as f:
            yaml.dump(data, f)

    def _launch_slave_process(self):
        """
        Launches the MockDesktop script
        """
        mockdesktop_script = os.path.join(
            os.path.split(__file__)[0],
            "mockdesktop.py"
        )

        sub_process = subprocess.Popen(
            [
                sys.executable,
                mockdesktop_script,
                "--test-folder", self.test_folder,
                "--test-name", self._testMethodName
            ],
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE
        )

        return sub_process

    # Parses Exception,ExceptionType,base64-encoded-string or nothing
    # Retursn ExceptionType and the text after the,
    # If \n are present in the output buffer, those will be matched as well.
    EXCEPTION_RE = re.compile(r"Exception:(.*),([a-zA-Z0-9\n]*={1,2}|)")

    def _extract_exception(self, process):
        """
        Extract an exception from the subprocess output.

        :param process: Process handle.

        :returns: Tuple of (exception type, exception message)
        """
        stdout, _ = process.communicate()
        res = self.EXCEPTION_RE.match(stdout)
        if not res:
            return None
        groups = res.groups()
        return groups[0], groups[1].decode("base64")

    def _assert_no_exception(self, process):
        """
        Asserts that no exceptions were thrown by the process.

        :param process: Process handle
        """
        ex = self._extract_exception(process)
        if ex:
            print "Exception was thrown!"
            print "%s: %s" % ex
        self.assertIsNone(ex)

    def _create_pipeline_configuration_for_template_project(self):
        """
        Creates a PipelineConfiguration for the Template Project.
        """
        # Create Pipeline configuration on template project.
        return self.sg.create("PipelineConfiguration", {
            "project": self.template_project_link,
            "code": "Primary"
        })

    def _assert_exception(self, process, exception_type, exception_regexp=None):
        """
        Asserts that no exceptions were thrown by the process.

        :param process: Process handle
        :param ex_type: Expected exception type
        """
        ex = self._extract_exception(process)
        if not ex:
            print "Expecting %s exception, but nothing was found!" % exception_type
            self.assertIsNotNone(ex)
        elif ex[0] != exception_type:
            print "Expecting %s exception, got %s instead!" % (exception_type, ex)
        self.assertEqual(ex[0], exception_type)
        if exception_regexp:
            self.assertRegexpMatches(ex[1], exception_regexp)

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
        pc = self._create_pipeline_configuration_for_template_project()

        # This will setup the site from scratch.
        process = self._launch_slave_process()
        self._assert_no_exception(process)

        tk = sgtk.sgtk_from_path(self.site_config_folder)
        # is_site_configuration is True only for a True site configuration, i.e. project_id is None
        self.assertFalse(tk.pipeline_configuration.is_site_configuration())
        self.assertEqual(tk.pipeline_configuration.get_project_id(), self.template_project_link["id"])
        self.assertEqual(tk.pipeline_configuration.get_shotgun_id(), pc["id"])

        # This should be able to reuse the config.
        process = self._launch_slave_process()
        self._assert_no_exception(process)

    def test_unexpected_config(self):
        """
        Tests startup with a site configured locally but nothing in Shotgun.
        """
        # Let's fake a toolkit install
        self._setup_site_configuration("0.16.4")
        # Clean up all site configurations so this is unexpected.
        self._remove_site_configurations()

        process = self._launch_slave_process()
        # startup should complain about an unexpected config.
        self._assert_exception(process, "UnexpectedConfigFound")

    def test_core_update_reboot(self):
        """
        Tests startup with a site configured locally but nothing in Shotgun.
        """
        self._setup_site_configuration("0.16.4")

        # An auto path setup should be upgradable
        tk = sgtk.sgtk_from_path(self.site_config_folder)
        self.assertTrue(tk.pipeline_configuration.is_auto_path())

        # Launch Desktop
        process = self._launch_slave_process()
        # startup should Restart after upgrading the core.
        self._assert_exception(process, "RequestRestartException")

    def test_non_auto_path_doesnt_upgrade(self):
        """
        Tests a non auto path setup that shouldn't upgrade.
        """
        # Create a site configuration that is non auto updating.
        pc = self._create_pipeline_configuration_for_template_project()
        self._setup_site_configuration("0.16.4", pc, auto_path=False)

        # A non auto path setup should not be upgradable.
        tk = sgtk.sgtk_from_path(self.site_config_folder)
        self.assertFalse(tk.pipeline_configuration.is_auto_path())

        # Launch Desktop
        process = self._launch_slave_process()
        # No request to startup should be made.
        self._assert_no_exception(process)

    def test_too_old_for_no_template(self):
        # Create a site configuration that can't migrate the site configuration.
        pc = self._create_pipeline_configuration_for_template_project()
        self._setup_site_configuration("0.16.4", pc, auto_path=False)
        # Zap the pipeline configuration's project is to cause a migration
        # of site configuration.
        self.sg.update("PipelineConfiguration", pc["id"], {"project": None})

        # Launch Desktop
        process = self._launch_slave_process()
        # startup should Restart after upgrading the core.
        self._assert_exception(process, "UpgradeCoreError", "v0.16.8")

    def test_can_migrate(self):
        # Create a site configuration that can migrate the site configuration.
        pc = self._create_pipeline_configuration_for_template_project()
        self._setup_site_configuration("0.16.12", pc=pc)
        # Zap the pipeline configuration's project is to cause a migration
        # of site configuration.
        self.sg.update("PipelineConfiguration", pc["id"], {"project": None})

        # Launch Desktop
        process = self._launch_slave_process()
        # startup should Restart after upgrading the core.
        self._assert_no_exception(process)

    def test_setup_project_as_an_artist(self):
        pass

    def test_non_matching_pipeline_ids(self):
        pass
