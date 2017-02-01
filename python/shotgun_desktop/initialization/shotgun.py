# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import json
import urllib
import urllib2
import httplib

from shotgun_api3 import Shotgun, AuthenticationFault
from shotgun_api3.lib import httplib2

from . import constants
from distutils.version import LooseVersion
from ..logger import get_logger
from ..errors import InvalidAppStoreCredentialsError, TankAppStoreConnectionError

logger = get_logger("initialization.shotgun")


def get_server_version(connection):
    """
    Retrieves the server version from the connection.

    :param connection: Connection we want the server version from.

    :returns: Tuple of (major, minor) versions.
    """
    sg_major_ver = connection.server_info["version"][0]
    sg_minor_ver = connection.server_info["version"][1]
    sg_patch_ver = connection.server_info["version"][2]

    return LooseVersion("%d.%d.%d" % (sg_major_ver, sg_minor_ver, sg_patch_ver))


def is_script_user_required(connection):
    """
    Returns if a site needs to be configured with a script user or if the new
    human user based authentication for Toolkit will work with it.

    :param connection: Connection to the server to test against.

    :returns: If the site is not compatible with the new authentication code,
        returns True, False otherwise.
    """
    # First version to support human based authentication for all operations was
    # 6.0.2.
    return get_server_version(connection) < LooseVersion("6.0.2")


def does_pipeline_configuration_require_project(connection):
    """
    Returns if pipeline configurations are project entities or not.

    :param connection: Connection to the server to test against.

    :returns: True if pipeline configurations are project entities, False
        otherwise.
    """
    # Pipepline configurations were made non project entities in 6.0.2
    return get_server_version(connection) < LooseVersion("6.0.2")


def get_or_create_script(connection):
    """
    Find the Toolkit script in Shotgun or create it if it does not exist.

    This method is present for legacy reason. When running pre-6.0 sites, we
    have to configure the core to use script users due for script user based
    authentication. However, in a post 5.0 world, clients will now by default
    use human user authentication and therefore won't need a script user to
    created.

    :param connection: Connection to the server to get or create a script user
                       from.

    :returns: A dictionary with keys firstname and salted_password.
    """
    script = connection.find_one(
        "ApiUser", [["firstname", "is", "Toolkit"]],
        fields=["firstname", "salted_password"])

    if script is not None:
        # script already exists
        return script

    # find the admin api rule set
    permission_rule_set = connection.find_one(
        "PermissionRuleSet",
        [["entity_type", "is", "ApiUser"], ["code", "is", "api_admin"]])

    # prepare the data to create the script
    data = {
        "description": "Shotgun Toolkit API Access",
        "email": "support@shotgunsoftware.com",
        "firstname": "Toolkit",
        "lastname": "1.0",
        "generate_event_log_entries": True,
    }

    if permission_rule_set is not None:
        # if we found our permission rule set, be explicit about using it
        # otherwise rely on the default role having enough permissions
        data["permission_rule_set"] = permission_rule_set

    # create the script
    script = connection.create("ApiUser", data)

    # and find it to get the api key
    script = connection.find_one(
        "ApiUser", [["id", "is", script["id"]]],
        fields=["firstname", "salted_password"])

    return script


def get_app_store_credentials(connection, proxy):
    """ Return the validated script for this site to connect to the app store """
    (script, key) = __get_app_store_key(connection)

    # connect to the app store
    try:
        sg_app_store = Shotgun(constants.SGTK_APP_STORE, script, key, http_proxy=proxy, connect=False)

        # pull down the full script information
        app_store_script = sg_app_store.find_one(
            "ApiUser",
            [["firstname", "is", script]],
            fields=["type", "firstname", "id", "salted_password"])
    except AuthenticationFault:
        raise InvalidAppStoreCredentialsError(
            "The Toolkit App Store credentials found in Shotgun are invalid."
        )

    return app_store_script


def get_app_store_http_proxy(connection, app_store_http_proxy):
    """
    Computes the proxy server to use for the app store. If the app_store_http_proxy setting is set in config.ini,
    that value will be used for the App Store proxy. If it is not set, the one from the site will be used.

    :param connection: Shotgun connection to the Shotgun site.
    :param app_store_http_proxy: Proxy setting found in config.ini

    :returns: The app store
    """
    # If app store proxy is None, we use the proxy setting from the site
    if app_store_http_proxy is None:
        return connection.config.raw_http_proxy
    # If the proxy is empty, it means we are forcing it to None, regardless
    # of the http proxy setting.
    elif app_store_http_proxy == "":
        return None
    # We have something, so use that.
    else:
        return app_store_http_proxy


def __get_app_store_key_internal(connection, post_data):
    """
    Return the script for this site to connect to the app store using a given
    set of credentials.

    :param connection: Connection to Shotgun.
    :param post_data: Credentials to send to the sgtk_install_script route.

    :returns: Dictionary with keys script_name and script_key.
    """
    # handle proxy setup by pulling the proxy details from the main shotgun connection
    if connection.config.proxy_handler:
        opener = urllib2.build_opener(connection.config.proxy_handler)
        urllib2.install_opener(opener)

    # now connect to our site and use a special url to retrieve the app store script key
    # note: need to use POST as of 5.1.13
    response = urllib2.urlopen(
        "%s/api3/sgtk_install_script" % connection.base_url,
        urllib.urlencode(post_data))

    html = response.read()
    data = json.loads(html)

    if not data["script_name"] or not data["script_key"]:
        raise InvalidAppStoreCredentialsError(
            "Toolkit App Store credentials could not be retrieved from Shotgun."
        )

    return data


def __get_app_store_key(connection):
    """
    Return the script for this site to connect to the app store. Uses the right
    authentication mechanism based on the version of the website.

    :param connection: Connection to Shotgun.

    :returns: Dictionary with keys script_name and script_key.
    """
    if is_script_user_required(connection):
        # We'll have to resort to the pre-6.0 way of getting the app store key,
        # using script user credentials. This gets us backward compatible
        # with old sites.

        # Find a script.
        script_user = get_or_create_script(connection)
        data = __get_app_store_key_internal(connection, {
            "script_name": script_user["firstname"],
            "script_key": script_user["salted_password"],
        })
    else:
        # The site supports session tokens to authenticate when retrieving
        # the app store keys, so use taht.
        data = __get_app_store_key_internal(connection, {
            "session_token": connection.get_session_token()
        })

    return (data["script_name"], data["script_key"])
