# Copyright (c) 2023 Shotgun Software Inc.
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
from unittest.mock import patch

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "python/tk-core/python")
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from shotgun_desktop import paths


class MockUser:
    """Mock a SG User class"""

    def resolve_entity(self, *args, **kwargs):
        pass


class MockConnection:
    """Mock the Shotgun class from python_api."""

    def __init__(self, **kwargs):
        self.base_url = ""

    def find(self, *args, **kwargs):
        pass


def test_no_pipeline_config(*mocks):
    """Ensure that no configuration is returned if there aren't any supplied."""
    with patch.object(MockConnection, "find", return_value=[]):
        _, pc, _ = paths.get_pipeline_configuration_info(MockConnection())
        assert pc is None


@patch("sgtk.get_authenticated_user", return_value=MockUser())
@patch.object(MockUser, "resolve_entity", return_value={"type": "HumanUser", "id": 1})
def test_one_pipeline_configuration(*mocks):
    """
    Just one configuration, no user restriction
    """
    with patch.object(
        MockConnection,
        "find",
        return_value=[
            {
                "type": "PipelineConfiguration",
                "id": 1,
                "code": "pc1",
                "users": [],
            },
        ],
    ):
        _, pc, _ = paths.get_pipeline_configuration_info(MockConnection())
        assert pc == {
            "type": "PipelineConfiguration",
            "id": 1,
            "code": "pc1",
            "users": [],
        }


@patch("sgtk.get_authenticated_user", return_value=MockUser())
@patch.object(MockUser, "resolve_entity", return_value={"type": "HumanUser", "id": 1})
def test_two_pipeline_configurations(*mocks):
    """
    Two configurations, no user restriction
    We select the one with lowest id
    """
    with patch.object(
        MockConnection,
        "find",
        return_value=[
            {
                "type": "PipelineConfiguration",
                "id": 2,
                "code": "pc2",
                "users": [],
            },
            {
                "type": "PipelineConfiguration",
                "id": 1,
                "code": "pc1",
                "users": [],
            },
        ],
    ):
        _, pc, _ = paths.get_pipeline_configuration_info(MockConnection())
        assert pc["id"] == 1 and pc["code"] == "pc1"


@patch("sgtk.get_authenticated_user", return_value=MockUser())
@patch.object(MockUser, "resolve_entity", return_value={"type": "HumanUser", "id": 1})
def test_lowest_id(*mocks):
    """
    Ensure that the configuration with the lowest id and without any user
    restrictions is selected if there are no configurations restricting the user.
    """
    with patch.object(
        MockConnection,
        "find",
        return_value=[
            {
                "type": "PipelineConfiguration",
                "id": 3,
                "code": "pc3",
                "users": [],
            },
            {
                "type": "PipelineConfiguration",
                "id": 2,
                "code": "pc2",
                "users": [],
            },
            {
                "type": "PipelineConfiguration",
                "id": 1,
                "code": "pc1",
                "users": [],
            },
        ],
    ):
        _, pc, _ = paths.get_pipeline_configuration_info(MockConnection())
        assert pc["id"] == 1 and pc["code"] == "pc1"


@patch("sgtk.get_authenticated_user", return_value=MockUser())
@patch.object(MockUser, "resolve_entity", return_value={"type": "HumanUser", "id": 2})
def test_user_restriction(*mocks):
    """
    2 Configs: one is user restricted, one has no restriction
    """
    with patch.object(
        MockConnection,
        "find",
        return_value=[
            {
                "type": "PipelineConfiguration",
                "id": 2,
                "code": "pc2",
                "users": [],
            },
            {
                "type": "PipelineConfiguration",
                "id": 1,
                "code": "pc1",
                "users": [
                    {"id": 1, "type": "HumanUser"},
                    {"id": 2, "type": "HumanUser"},
                    {"id": 3, "type": "HumanUser"},
                ],
            },
        ],
    ):
        _, pc, _ = paths.get_pipeline_configuration_info(MockConnection())
        assert pc["id"] == 1 and pc["code"] == "pc1"


@patch("sgtk.get_authenticated_user", return_value=MockUser())
@patch.object(MockUser, "resolve_entity", return_value={"type": "HumanUser", "id": 1})
def test_user_restriction_all_restricted_different_users(*mocks):
    """
    Ensure that no configuration is returned if all have user restrictions,
    but none match the user.
    """
    with patch.object(
        MockConnection,
        "find",
        return_value=[
            {
                "type": "PipelineConfiguration",
                "id": 1,
                "code": "pc1",
                "users": [{"id": 2, "type": "HumanUser"}],
            },
        ],
    ):
        _, pc, _ = paths.get_pipeline_configuration_info(MockConnection())
        assert pc is None


@patch("sgtk.get_authenticated_user", return_value=MockUser())
@patch.object(MockUser, "resolve_entity", return_value={"type": "HumanUser", "id": 1})
def test_user_restriction_no_match_fallback_unrestricted(*mocks):
    """
    2 Configs: one is user restricted, one has no restriction
    """
    with patch.object(
        MockConnection,
        "find",
        return_value=[
            {
                "type": "PipelineConfiguration",
                "id": 2,
                "code": "pc2",
                "users": [],
            },
            {
                "type": "PipelineConfiguration",
                "id": 1,
                "code": "pc1",
                "users": [{"id": 2, "type": "HumanUser"}],
            },
        ],
    ):
        _, pc, _ = paths.get_pipeline_configuration_info(MockConnection())
        assert pc["id"] == 2 and pc["code"] == "pc2"


@patch("sgtk.get_authenticated_user", return_value=MockUser())
def test_user_restriction_lowest_id(*mocks):
    """
    Ensure that user-restricted configuration with lowest id is selected over
    non-restricted configuration when that user logs in.
    """
    with patch.object(
        MockUser, "resolve_entity", return_value={"type": "HumanUser", "id": 1}
    ), patch.object(
        MockConnection,
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
        _, pc, _ = paths.get_pipeline_configuration_info(MockConnection())
        assert pc["id"] == 2 and pc["code"] == "restricted1"
