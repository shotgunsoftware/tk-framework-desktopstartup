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
import urlparse
import logging


def get_shotgun_app_root():
    """ returns where the shotgun app is installed """
    if sys.platform == "darwin":
        args = [os.path.dirname(__file__)] + [".."] * 5
        shotgun_root = os.path.abspath(os.path.join(*args))
    elif sys.platform == "win32":
        shotgun_root = os.path.abspath(os.path.dirname(sys.prefix))
    elif sys.platform.startswith("linux"):
        shotgun_root = os.path.abspath(os.path.dirname(sys.prefix))
    else:
        raise NotImplementedError("Unsupported platform: %s" % sys.platform)

    return shotgun_root


def get_python_path():
    """ returns the path to the default python interpreter """
    if sys.platform == "darwin":
        python = os.path.join(sys.prefix, "bin", "python")
    elif sys.platform == "win32":
        python = os.path.join(sys.prefix, "python.exe")
    elif sys.platform.startswith("linux"):
        python = os.path.join(sys.prefix, "bin", "python")
    return python


def get_local_site_config_path(connection):
    """
    Computes the local site config path

    :param connection: Connection to the Shotgun site.

    :returns: Path inside the user folder.
    """

    # get operating system specific root
    if sys.platform == "darwin":
        pc_root = os.path.expanduser("~/Library/Application Support/Shotgun")
    elif sys.platform == "win32":
        pc_root = os.path.join(os.environ["APPDATA"], "Shotgun")
    elif sys.platform.startswith("linux"):
        pc_root = os.path.expanduser("~/.shotgun")

    # add on site specific postfix
    site = __get_site_from_connection(connection)
    pc_root = os.path.join(pc_root, site, "site")

    return str(pc_root)


def get_default_site_config_roots(connection, fields):
    """
    Returns all the pipeline configurations that would be a site configuration.

    :param connection: Shotgun instance.
    :param fields: Name of fields that should be retrieved from each pipeline configuration.

    :returns: Array of pipeline configurations dictionaries.
    """

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

    # interesting fields to return

    return connection.find(
        "PipelineConfiguration",
        [{
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
            ]
        }],
        fields=fields,
        order=[
            # Sorting on the project id doesn't actually matter. We want
            # some sorting simply because this will force grouping between
            # configurations with a project and those that don't.
            {'field_name':'project.Project.id','direction':'asc'},
            {'field_name':'id','direction':'desc'}
        ]
    )


def get_default_site_config_root(connection):
    """ return the path to the default configuration for the site """
    # find what path field from the entity we need
    if sys.platform == "darwin":
        plat_key = "mac_path"
    elif sys.platform == "win32":
        plat_key = "windows_path"
    elif sys.platform.startswith("linux"):
        plat_key = "linux_path"
    else:
        raise RuntimeError("unknown platform: %s" % sys.platform)

    pcs = get_default_site_config_roots(
        connection,
        ["id", "code", "windows_path", "mac_path", "linux_path", "project"]
    )

    if len(pcs) == 0:
        pc = None
    else:
        # Pick the last result. See the big comment before the Shotgun query to understand.
        pc = pcs[-1]
        # It is possible to get multiple pipeline configurations due to user error.
        # Log a warning if there was more than one pipeline configuration found.
        if len(pcs) > 1:
            logging.getLogger("tk-desktop.paths").info(
                "More than one pipeline configuration was found (%s), using %d" %
                (", ".join([str(p["id"]) for p in pcs]), pc["id"])
            )

    # see if we found a pipeline configuration
    if pc is not None and pc.get(plat_key, ""):
        # path is already set for us, just return it
        return (str(pc[plat_key]), pc)

    return (get_local_site_config_path(connection), pc)


def __get_site_from_connection(connection):
    """ return the site from the information in the connection """
    # grab just the non-port part of the netloc of the url
    # eg site.shotgunstudio.com
    site = urlparse.urlparse(connection.base_url)[1].split(":")[0]
    return site
