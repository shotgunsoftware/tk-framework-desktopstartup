# Copyright (c) 2023 Shotgun Software Inc.
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

from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python/tk-core/python"))
from python.shotgun_desktop import paths

# sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
# import sgtk


class Dummy:
    def __init__(self, **kwargs):
        self.base_url = ""

    def find(self, *args, **kwargs):
        pass

    def resolve_entity(self, *args, **kwargs):
        pass


@patch.object(Dummy,"find",
        return_value=[{'type': 'PipelineConfiguration', 'id': 2, 'code': 'restricted', 'project': None, 'plugin_ids': None, 'users': [{'id': 88, 'name': 'HumanName', 'type': 'HumanUser'}]},
                      {'type': 'PipelineConfiguration', 'id': 1, 'code': 'non-restricted', 'project': None, 'plugin_ids': None, 'users': []}])
@patch("sgtk.get_authenticated_user",
       return_value=Dummy())
@patch.object(Dummy,"resolve_entity",
        return_value={'type': 'HumanUser', 'id': 88})
def test_select_restricted_config(*mocks):
    _, pc, _ = paths.get_pipeline_configuration_info(Dummy())
    expected_pc = {'type': 'PipelineConfiguration', 'id': 2, 'code': 'restricted', 'project': None, 'plugin_ids': None, 'users': [{'id': 88, 'name': 'HumanName', 'type': 'HumanUser'}]}
    assert pc == expected_pc


@patch.object(Dummy,"find",
        return_value=[{'type': 'PipelineConfiguration', 'id': 2, 'code': 'Secondary', 'project': None, 'plugin_ids': None, 'users': []}, 
                      {'type': 'PipelineConfiguration', 'id': 1, 'code': 'Primary', 'project': None, 'plugin_ids': None, 'users': []}])
@patch("sgtk.get_authenticated_user",
       return_value=Dummy())
@patch.object(Dummy,"resolve_entity",
        return_value={'type': 'HumanUser', 'id': 88})
def test_no_restricted_config(*mocks):
    _, pc, _ = paths.get_pipeline_configuration_info(Dummy())
    expected_pc = {'type': 'PipelineConfiguration', 'id': 1, 'code': 'Primary', 'project': None, 'plugin_ids': None, 'users': []}
    assert pc == expected_pc


@patch.object(Dummy,"find",
        return_value=[])
def test_no_pipeline_config(*mocks):
    _, pc, _ = paths.get_pipeline_configuration_info(Dummy())
    assert not pc
