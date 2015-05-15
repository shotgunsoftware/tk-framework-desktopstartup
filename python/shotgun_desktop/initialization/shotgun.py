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

from shotgun_api3 import Shotgun

from . import constants


def get_server_version(connection):
    """
    Retrieves the server version from the connection.

    :param connection: Connection we want the server version from.

    :returns: Tuple of (major, minor) versions.
    """
    sg_major_ver = connection.server_info["version"][0]
    sg_minor_ver = connection.server_info["version"][1]
    sg_patch_ver = connection.server_info["version"][2]

    return sg_major_ver, sg_minor_ver, sg_patch_ver


def is_script_user_required(connection):
    """
    Returns if a site needs to be configured with a script user or if the new
    human user based authentication for Toolkit will work with it.

    :returns: If the site is not compatible with the new authentication code,
        returns True, False otherwise.
    """
    major, minor, patch = get_server_version(connection)

    # First version to support human based authentication for all operations was
    # 6.0.2.
    if major < 6 or (major == 6 and minor == 0 and patch <= 1):
        return True
    else:
        return False


def is_server_valid(connection):
    """ Validate the shotgun server """
    sg_major_ver, sg_minor_ver, _ = get_server_version(connection)

    if sg_major_ver < 5 or (sg_major_ver == 5 and sg_minor_ver < 1):
        return False
    return True


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
        "email": "toolkitsupport@shotgunsoftware.com",
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


def get_proxy_from_connection(connection):
    """
    Return the proxy string from a connection object
    Returns None if there is no proxy set
    """
    proxy_server = connection.config.proxy_server
    if proxy_server is None:
        return None

    proxy_port = connection.config.proxy_port
    proxy_user = connection.config.proxy_user
    proxy_pass = connection.config.proxy_pass

    if proxy_user is None:
        proxy = "%s:%s" % (proxy_server, proxy_port)
    else:
        proxy = "%s:%s@%s:%s" % (proxy_user, proxy_pass, proxy_server, proxy_port)

    return proxy


def get_app_store_credentials(connection):
    """ Return the validated script for this site to connect to the app store """
    (script, key) = __get_app_store_key(connection)

    # get the proxy string from the connection
    proxy = get_proxy_from_connection(connection)

    # connect to the app store
    try:
        sg_app_store = Shotgun(constants.SGTK_APP_STORE, script, key, http_proxy=proxy)

        # pull down the full script information
        app_store_script = sg_app_store.find_one(
            "ApiUser",
            [["firstname", "is", script]],
            fields=["type", "firstname", "id", "salted_password"])
    except Exception:
        return None

    return app_store_script


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
    return json.loads(html)


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
