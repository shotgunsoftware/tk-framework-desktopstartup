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
from tank_vendor.six.moves.urllib import parse
import pprint
import sgtk

from sgtk import LogManager

logger = LogManager.get_logger(__name__)


def get_pipeline_configuration_info(connection):
    """
    Finds the site configuration root on disk.

    :param shotgun_api3.Shotgun connection: Shotgun instance for the site we want
        to find a configuration for.

    :returns (str, str, bool): The pipeline configuration root, the pipeline configuration
        entity dictionary and a boolean indicating if Toolkit classic is required. If True,
        Toolkit classic is required.
    """

    # find what path field from the entity we need

    plat_key = sgtk.util.ShotgunPath.get_shotgun_storage_key()

    # interesting fields to return
    fields = [
        "id",
        "code",
        "windows_path",
        "mac_path",
        "linux_path",
        "project",
        "sg_plugin_ids",
        "plugin_ids",
    ]

    # Find the right pipeline configuration. We'll always pick a projectless
    # one over one with the Template Project. To have a deterministic behaviour,
    # we'll also always sort the ids. Common sense would dictate that the
    # sorting needs to be done from low ids to high ids. However, entries with
    # no project get systematically pushed to the end of the list, no matter
    # the ordering. Since we want to pick the projectless configuration first,
    # we'll reverse the sorting order on ids so the last returned result is the
    # lowest projectless configuration (if available). If no projectless
    # pipeline configurations are available, then the ones from the Template
    # project will show up. Once again, because we are sorting configurations
    # based on decreasing ids, the last entry is still the one with the lowest
    # id.

    pcs = connection.find(
        "PipelineConfiguration",
        [
            {
                "filter_operator": "any",
                "filters": [
                    ["project", "is", None],
                    {
                        "filter_operator": "all",
                        "filters": [
                            ["project.Project.name", "is", "Template Project"],
                            ["project.Project.layout_project", "is", None],
                        ],
                    },
                ],
            }
        ],
        fields=fields,
        order=[
            # Sorting on the project id doesn't actually matter. We want
            # some sorting simply because this will force grouping between
            # configurations with a project and those that don't.
            {"field_name": "project.Project.id", "direction": "asc"},
            {"field_name": "id", "direction": "desc"},
        ],
    )

    # We don't filter in the Shotgun query for the plugin ids because not every site these fields yet.
    # So if any pipeline configurations with a plugin id was returned, filter them it out.
    pcs = list(
        filter(lambda pc: not (pc.get("sg_plugin_ids") or pc.get("plugin_ids")), pcs)
    )

    logger.debug(
        "These non-plugin_id based pipeline configurations were found by Desktop:"
    )
    logger.debug(pprint.pformat(pcs))

    if len(pcs) == 0:
        pc = None
    else:
        # Pick the last result. See the big comment before the Shotgun query to understand.
        pc = pcs[-1]
        # It is possible to get multiple pipeline configurations due to user error.
        # Log a warning if there was more than one pipeline configuration found.
        if len(pcs) > 1:
            logger.info(
                "More than one pipeline configuration was found (%s), using %d"
                % (", ".join([str(p["id"]) for p in pcs]), pc["id"])
            )

    logger.debug("This pipeline configuration will be used:")
    logger.debug(pprint.pformat(pc))

    # see if we found a pipeline configuration
    if pc is not None and pc.get(plat_key, ""):
        # path is already set for us, just return it
        return (str(pc[plat_key]), pc, True)

    # get operating system specific root
    if sgtk.util.is_macos():
        pc_root = os.path.expanduser("~/Library/Application Support/Shotgun")
    elif sgtk.util.is_windows():
        pc_root = os.path.join(os.environ["APPDATA"], "Shotgun")
    elif sgtk.util.is_linux():
        pc_root = os.path.expanduser("~/.shotgun")

    # add on site specific postfix
    site = __get_site_from_connection(connection)
    pc_root = os.path.join(pc_root, site, "site")

    return (str(pc_root), pc, False)


def __get_site_from_connection(connection):
    """ return the site from the information in the connection """
    # grab just the non-port part of the netloc of the url
    # eg site.shotgunstudio.com
    site = parse.urlparse(connection.base_url)[1].split(":")[0]
    return site
