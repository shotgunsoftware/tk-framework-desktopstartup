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

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "python/tk-core/python")
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from shotgun_desktop import paths


class DummyConnection:
    """Simulate the Shotgun class from python_api."""

    def __init__(self, **kwargs):
        self.base_url = ""

    def find(self, *args, **kwargs):
        pass

    def resolve_entity(self, *args, **kwargs):
        pass


@patch.object(
    DummyConnection,
    "find",
    return_value=[
        {
            "type": "PipelineConfiguration",
            "id": 3,
            "code": "restricted2",
            "project": None,
            "plugin_ids": None,
            "users": [{"id": 88, "name": "HumanName", "type": "HumanUser"}],
        },
        {
            "type": "PipelineConfiguration",
            "id": 2,
            "code": "restricted1",
            "project": None,
            "plugin_ids": None,
            "users": [{"id": 88, "name": "HumanName", "type": "HumanUser"}],
        },
        {
            "type": "PipelineConfiguration",
            "id": 1,
            "code": "non-restricted",
            "project": None,
            "plugin_ids": None,
            "users": [],
        },
    ],
)
@patch("sgtk.get_authenticated_user", return_value=DummyConnection())
@patch.object(
    DummyConnection, "resolve_entity", return_value={"type": "HumanUser", "id": 88}
)
def test_select_restricted_config(*mocks):
    """
    Ensure that user-restricted configuration with lowest id is selected over
    non-restricted configuration when that user logs in.
    """
    _, pc, _ = paths.get_pipeline_configuration_info(DummyConnection())
    expected_pc = {
        "type": "PipelineConfiguration",
        "id": 2,
        "code": "restricted1",
        "project": None,
        "plugin_ids": None,
        "users": [{"id": 88, "name": "HumanName", "type": "HumanUser"}],
    }
    assert pc == expected_pc


@patch.object(
    DummyConnection,
    "find",
    return_value=[
        {
            "type": "PipelineConfiguration",
            "id": 3,
            "code": "non-restricted2",
            "project": None,
            "plugin_ids": None,
            "users": [],
        },
        {
            "type": "PipelineConfiguration",
            "id": 2,
            "code": "non-restricted1",
            "project": None,
            "plugin_ids": None,
            "users": [],
        },
        {
            "type": "PipelineConfiguration",
            "id": 1,
            "code": "restricted",
            "project": None,
            "plugin_ids": None,
            "users": [{"id": 80, "name": "HumanName", "type": "HumanUser"}],
        },
    ],
)
@patch("sgtk.get_authenticated_user", return_value=DummyConnection())
@patch.object(
    DummyConnection, "resolve_entity", return_value={"type": "HumanUser", "id": 88}
)
def test_no_restricted_config(*mocks):
    """
    Ensure that the configuration with the lowest id and without any user
    restrictions is selected if there are no configurations restricting the user.
    """
    _, pc, _ = paths.get_pipeline_configuration_info(DummyConnection())
    expected_pc = {
        "type": "PipelineConfiguration",
        "id": 2,
        "code": "non-restricted1",
        "project": None,
        "plugin_ids": None,
        "users": [],
    }
    assert pc == expected_pc


@patch.object(DummyConnection, "find", return_value=[])
def test_no_pipeline_config(*mocks):
    """Ensure that no configuration is returned if there aren't any supplied."""
    _, pc, _ = paths.get_pipeline_configuration_info(DummyConnection())
    assert not pc
