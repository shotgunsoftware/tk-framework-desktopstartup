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


@patch("sgtk.get_authenticated_user", return_value=DummyConnection())
def test_select_restricted_config(*mocks):
    """
    Ensure that user-restricted configuration with lowest id is selected over
    non-restricted configuration when that user logs in.
    """
    with patch.object(
        DummyConnection, "resolve_entity", return_value={"type": "HumanUser", "id": 1}
    ), patch.object(
        DummyConnection,
        "find",
        return_value=[
            {
                "type": "PipelineConfiguration",
                "id": 3,
                "code": "restricted2",
                "users": [{"id": 1, "name": "HumanName", "type": "HumanUser"}],
            },
            {
                "type": "PipelineConfiguration",
                "id": 2,
                "code": "restricted1",
                "users": [{"id": 1, "name": "HumanName", "type": "HumanUser"}],
            },
            {
                "type": "PipelineConfiguration",
                "id": 1,
                "code": "non-restricted",
                "users": [],
            },
        ],
    ):
        _, pc, _ = paths.get_pipeline_configuration_info(DummyConnection())
        expected_pc = {
            "type": "PipelineConfiguration",
            "id": 2,
            "code": "restricted1",
            "users": [{"id": 1, "name": "HumanName", "type": "HumanUser"}],
        }
        assert pc == expected_pc


@patch("sgtk.get_authenticated_user", return_value=DummyConnection())
def test_no_restricted_config(*mocks):
    """
    Ensure that the configuration with the lowest id and without any user
    restrictions is selected if there are no configurations restricting the user.
    """
    with patch.object(
        DummyConnection, "resolve_entity", return_value={"type": "HumanUser", "id": 1}
    ), patch.object(
        DummyConnection,
        "find",
        return_value=[
            {
                "type": "PipelineConfiguration",
                "id": 3,
                "code": "non-restricted2",
                "users": [],
            },
            {
                "type": "PipelineConfiguration",
                "id": 2,
                "code": "non-restricted1",
                "users": [],
            },
            {
                "type": "PipelineConfiguration",
                "id": 1,
                "code": "restricted",
                "users": [{"id": 2, "name": "HumanName", "type": "HumanUser"}],
            },
        ],
    ):
        _, pc, _ = paths.get_pipeline_configuration_info(DummyConnection())
        expected_pc = {
            "type": "PipelineConfiguration",
            "id": 2,
            "code": "non-restricted1",
            "users": [],
        }
        assert pc == expected_pc


def test_no_pipeline_config(*mocks):
    """Ensure that no configuration is returned if there aren't any supplied."""
    with patch.object(DummyConnection, "find", return_value=[]):
        _, pc, _ = paths.get_pipeline_configuration_info(DummyConnection())
        assert not pc


@patch("sgtk.get_authenticated_user", return_value=DummyConnection())
def test_no_config_match(*mocks):
    """
    Ensure that no configuration is returned if all have user restrictions,
    but none match the user.
    """
    with patch.object(
        DummyConnection, "resolve_entity", return_value={"type": "HumanUser", "id": 1}
    ), patch.object(
        DummyConnection,
        "find",
        return_value=[
            {
                "type": "PipelineConfiguration",
                "id": 1,
                "code": "pc1",
                "users": [{"id": 2, "type": "HumanUser"}],
            },
            {
                "type": "PipelineConfiguration",
                "id": 2,
                "code": "pc2",
                "users": [{"id": 2, "type": "HumanUser"}],
            },
        ],
    ):
        _, pc, _ = paths.get_pipeline_configuration_info(DummyConnection())
        assert pc is None
